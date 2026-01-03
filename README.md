# fintech-platform (monorepo scaffold)

## Structure
- `services/` contains independent microservices (no shared business logic)
- `infra/` contains Terraform only (fully separated)

## Local development (LocalStack + Terraform)

### 1) Start LocalStack
- `docker compose up -d localstack`

### 2) Create SQS via Terraform (required)
Terraform `local` env targets LocalStack and creates SQS queues.

- `cd infra/envs/local`
- `terraform init`
- `terraform apply -auto-approve`

Useful output:
- `terraform output -raw events_queue_url`

### 3) Start services
- `cd ../../..`
- `docker compose up --build`

Gateway:
- http://localhost:8000/healthz

Publish a message:
- `curl -s -X POST http://localhost:8000/v1/messages -H 'content-type: application/json' -d '{"message_type":"ping","payload":{}}'`

## Notes
- Applications read AWS endpoints from `AWS_ENDPOINT_URL` (LocalStack: `http://localstack:4566`).
- Applications do not create AWS resources; Terraform does.
