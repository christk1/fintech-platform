package main

import (
	"context"
	"log"
	"net"
	"os"

	balancev1 "github.com/christk1/fintech-platform/services/balance-service/proto"
	"google.golang.org/grpc"
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
