.PHONY: init plan apply destroy validate fmt clean

init:
	terraform init

plan:
	terraform plan

apply:
	terraform apply

destroy:
	terraform destroy

validate:
	terraform validate

fmt:
	terraform fmt -recursive

clean:
	rm -rf .terraform .terraform.lock.hcl terraform.tfstate* *.tfvars

# Создание директорий для данных
prepare:
	mkdir -p ../data/{postgres,redis,prometheus,grafana,crawler,processor}
	chmod -R 755 ../data

# Просмотр outputs
outputs:
	terraform output

# Просмотр логов
logs:
	docker logs reestry-crawler -f

logs-processor:
	docker logs reestry-processor -f

logs-postgres:
	docker logs reestry-postgres -f

logs-redis:
	docker logs reestry-redis -f

logs-prometheus:
	docker logs reestry-prometheus -f

logs-grafana:
	docker logs reestry-grafana -f

# Проверка статуса
status:
	docker ps --filter "name=reestry-"

