# Kubernetes manifests (local/dev)

These files mirror the services in `docker-compose.yml`:
- `api-gateway` (HTTP :8000)
- `worker` (no ports)
- `balance-service` (gRPC :50051)

They expect your existing `.env` values to be loaded into the cluster as a Secret.

## 1) Create namespace + env secret

```sh
kubectl apply -f k8s/namespace.yaml
kubectl -n fintech create secret generic fintech-env --from-env-file=.env
```

If you update `.env`, recreate the secret:

```sh
kubectl -n fintech delete secret fintech-env
kubectl -n fintech create secret generic fintech-env --from-env-file=.env
```

## 2) Build images for your cluster

These manifests use local image names:
- `fintech/api-gateway:local`
- `fintech/worker:local`
- `fintech/balance-service:local`

Build them:

```sh
docker build -t fintech/api-gateway:local services/api-gateway
docker build -t fintech/worker:local services/worker
docker build -t fintech/balance-service:local services/balance-service
```

If you use kind, load images into the cluster:

```sh
kind load docker-image fintech/api-gateway:local fintech/worker:local fintech/balance-service:local
```

## 3) Deploy

```sh
kubectl apply -f k8s/api-gateway.yaml
kubectl apply -f k8s/worker.yaml
kubectl apply -f k8s/balance-service.yaml
```

## 4) Access api-gateway

### Option A: External LoadBalancer (EKS)

`k8s/api-gateway.yaml` exposes `api-gateway` as a `Service` of type `LoadBalancer`.
On EKS, Kubernetes will provision an external LB automatically.

Get the external address:

```sh
kubectl -n fintech get svc api-gateway
```

Then use the `EXTERNAL-IP` / hostname:

```sh
curl http://<external-host>/healthz
curl "http://<external-host>/v2/balance/metrics?client_id=client_123"
```

### Option B: Local clusters (kind/minikube)

If you are running locally, `LoadBalancer` may require extra plumbing:

- minikube: run `minikube tunnel` and then `kubectl -n fintech get svc api-gateway`
- kind: use an Ingress controller or port-forward

Port-forward (always works):

```sh
kubectl -n fintech port-forward svc/api-gateway 8000:80
```

Then:

```sh
curl http://localhost:8000/healthz
curl "http://localhost:8000/v2/balance/metrics?client_id=client_123"
```
