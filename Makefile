.PHONY: infra-local infra-local-clean sync-env up down reset migrate gen-grpc

infra-local:
	cd infra/envs/local && terraform init && terraform apply -auto-approve

infra-local-clean:
	@# Use this after switching LocalStack instances (e.g. `localstack start` vs compose) to avoid stale IDs/ARNs.
	rm -rf infra/envs/local/.terraform \
		infra/envs/local/terraform.tfstate \
		infra/envs/local/terraform.tfstate.backup
	$(MAKE) infra-local

sync-env:
	python3 scripts/sync_env_from_tf.py --tf-dir infra/envs/local --env-file .env

up:
	$(MAKE) infra-local
	$(MAKE) sync-env
	docker compose up --build

down:
	docker compose down

reset:
	cd infra/envs/local && terraform destroy -auto-approve || true
	docker compose down -v --remove-orphans

migrate:
	@# Runs DB migrations (owned by api-gateway) using DATABASE_URL from .env
	@set -a; [ -f .env ] && . ./.env; set +a; \
	DATABASE_URL="$$(printf '%s' "$$DATABASE_URL" | sed 's/host.docker.internal/localhost/g')"; \
	cd services/api-gateway && DATABASE_URL="$$DATABASE_URL" ../../.venv/bin/python -m alembic -c alembic.ini upgrade head

gen-grpc:
	./.venv/bin/python scripts/gen_balance_grpc_py.py
