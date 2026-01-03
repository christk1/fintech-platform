Terraform is fully separated from application code.

Environments:
- `infra/envs/local` targets LocalStack (mandatory for local dev)
- `infra/envs/staging` placeholder
- `infra/envs/prod` placeholder

Modules:
- `infra/modules/sqs-queue`
