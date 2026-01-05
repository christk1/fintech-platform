package main

import (
	"context"
	"errors"
	"hash/fnv"
	"log"
	"math/rand/v2"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	balancev1 "github.com/christk1/fintech-platform/services/balance-service/proto"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type balanceServer struct {
	balancev1.UnimplementedBalanceServiceServer
}

func (s *balanceServer) Ping(
	ctx context.Context,
	req *balancev1.PingRequest,
) (*balancev1.PingResponse, error) {
	_ = ctx
	_ = req
	return &balancev1.PingResponse{Status: "ok"}, nil
}

func (s *balanceServer) GetMetrics(
	ctx context.Context,
	req *balancev1.MetricsRequest,
) (*balancev1.MetricsResponse, error) {
	clientID := strings.TrimSpace(req.GetClientId())
	if clientID == "" {
		return nil, status.Error(codes.InvalidArgument, "client_id is required")
	}

	allProviders := defaultProvidersFromEnv()
	assigned := providersForClient(clientID, allProviders)

	// If caller provided explicit provider_ids, only allow those within the client's assigned set.
	providerIDs := req.GetProviderIds()
	if len(providerIDs) == 0 {
		providerIDs = assigned
	} else {
		allowed := make(map[string]struct{}, len(assigned))
		for _, p := range assigned {
			allowed[p] = struct{}{}
		}
		filtered := make([]string, 0, len(providerIDs))
		for _, p := range providerIDs {
			p = strings.TrimSpace(p)
			if p == "" {
				continue
			}
			if _, ok := allowed[p]; ok {
				filtered = append(filtered, p)
			}
		}
		providerIDs = filtered
	}

	workers := getenvInt("FANOUT_WORKERS", 8)
	if workers <= 0 {
		return nil, status.Error(codes.InvalidArgument, "FANOUT_WORKERS must be > 0")
	}

	jobs := make(chan string)
	results := make(chan *balancev1.ProviderMetric)
	workerErrors := make(chan error, 1)

	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	var wg sync.WaitGroup
	for range workers {
		wg.Go(func() {
			for providerID := range jobs {
				metric, err := fetchDummyMetric(ctx, providerID)
				if err != nil {
					select {
					case workerErrors <- err:
					default:
					}
					cancel()
					return
				}
				select {
				case results <- metric:
				case <-ctx.Done():
					return
				}
			}
		})
	}

	// Feed jobs and close the queue exactly once.
	go func() {
		defer close(jobs)
		for _, providerID := range providerIDs {
			select {
			case jobs <- providerID:
			case <-ctx.Done():
				return
			}
		}
	}()

	// Close results when all workers exit.
	go func() {
		wg.Wait()
		close(results)
	}()

	var metrics []*balancev1.ProviderMetric
	for {
		select {
		case err := <-workerErrors:
			if err != nil {
				return nil, status.Error(codes.Unavailable, "provider fanout failed")
			}
		case metric, ok := <-results:
			if !ok {
				return &balancev1.MetricsResponse{Metrics: metrics}, nil
			}
			metrics = append(metrics, metric)
		case <-ctx.Done():
			// Prefer surfacing any worker error if one occurred.
			select {
			case err := <-workerErrors:
				if err != nil {
					return nil, status.Error(codes.Unavailable, "provider fanout failed")
				}
			default:
			}

			if errors.Is(ctx.Err(), context.DeadlineExceeded) {
				return nil, status.Error(codes.DeadlineExceeded, "request deadline exceeded")
			}
			return nil, status.Error(codes.Canceled, "request canceled")
		}
	}
}

func main() {
	host := getenv("HOST", "0.0.0.0")
	port := getenv("PORT", "50051")
	addr := net.JoinHostPort(host, port)

	lis, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("listen %s: %v", addr, err)
	}

	srv := grpc.NewServer()
	balancev1.RegisterBalanceServiceServer(srv, &balanceServer{})

	log.Printf("balance-service gRPC listening on %s", addr)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getenvInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(v)
	if err != nil {
		return fallback
	}
	return parsed
}

func defaultProvidersFromEnv() []string {
	raw := os.Getenv("DUMMY_PROVIDERS")
	if raw == "" {
		return []string{"bank_alpha", "bank_bravo", "psp_charlie", "psp_delta", "bank_echo"}
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	if len(out) == 0 {
		return []string{"bank_alpha", "bank_bravo", "psp_charlie", "psp_delta", "bank_echo"}
	}
	return out
}

func providersForClient(clientID string, all []string) []string {
	banks := make([]string, 0, len(all))
	psps := make([]string, 0, len(all))
	for _, p := range all {
		lp := strings.ToLower(p)
		if strings.HasPrefix(lp, "psp") {
			psps = append(psps, p)
			continue
		}
		banks = append(banks, p)
	}

	seed := fnv64("client:" + clientID)
	rng := rand.New(rand.NewPCG(seed, seed^0x9e3779b97f4a7c15))
	rng.Shuffle(len(banks), func(i, j int) { banks[i], banks[j] = banks[j], banks[i] })
	rng.Shuffle(len(psps), func(i, j int) { psps[i], psps[j] = psps[j], psps[i] })

	banksPerClient := getenvInt("BANKS_PER_CLIENT", 2)
	pspsPerClient := getenvInt("PSPS_PER_CLIENT", 1)
	if banksPerClient < 0 {
		banksPerClient = 0
	}
	if pspsPerClient < 0 {
		pspsPerClient = 0
	}

	if banksPerClient > len(banks) {
		banksPerClient = len(banks)
	}
	if pspsPerClient > len(psps) {
		pspsPerClient = len(psps)
	}

	assigned := make([]string, 0, banksPerClient+pspsPerClient)
	assigned = append(assigned, banks[:banksPerClient]...)
	assigned = append(assigned, psps[:pspsPerClient]...)
	return assigned
}

func fetchDummyMetric(ctx context.Context, providerID string) (*balancev1.ProviderMetric, error) {
	// Simulate IO latency per provider.
	seed := fnv64(providerID)
	rng := rand.New(rand.NewPCG(seed, seed^0x9e3779b97f4a7c15))

	latency := time.Duration(50+rng.IntN(150)) * time.Millisecond
	t := time.NewTimer(latency)
	select {
	case <-t.C:
	case <-ctx.Done():
		if !t.Stop() {
			<-t.C
		}
		return nil, ctx.Err()
	}

	providerType := "bank"
	if strings.HasPrefix(strings.ToLower(providerID), "psp") {
		providerType = "psp"
	}

	available := int64(10_00 + rng.IntN(250_000_00))
	ledger := available + int64(rng.IntN(50_00))
	if ledger < 0 {
		ledger = available
	}

	return &balancev1.ProviderMetric{
		ProviderId:     providerID,
		ProviderName:   strings.ReplaceAll(providerID, "_", " "),
		ProviderType:   providerType,
		Currency:       "EUR",
		AvailableCents: available,
		LedgerCents:    ledger,
		AsOfUnixMs:     time.Now().UnixMilli(),
	}, nil
}

func fnv64(s string) uint64 {
	h := fnv.New64a()
	_, _ = h.Write([]byte(s))
	return h.Sum64()
}
