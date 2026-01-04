.PHONY: infra-local infra-local-clean sync-env up down reset

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
