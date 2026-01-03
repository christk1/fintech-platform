.PHONY: infra-local up down reset

infra-local:
	cd infra/envs/local && terraform init && terraform apply -auto-approve

up:
	docker compose up --build

down:
	docker compose down

reset:
	cd infra/envs/local && terraform destroy -auto-approve || true
	docker compose down -v --remove-orphans
