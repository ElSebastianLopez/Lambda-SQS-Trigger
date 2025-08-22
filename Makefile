.PHONY: help up deploy test logs clean

help:
	@echo "Comandos:"
	@echo "  make deploy   - Desplegar todo"
	@echo "  make test     - Enviar mensaje de prueba"
	@echo "  make logs     - Ver logs"
	@echo "  make clean    - Limpiar todo"



deploy: up
	cd lambda && pip install requests -t . --quiet
	terraform init -upgrade
	terraform apply -auto-approve

test:
	python test_sqs.py dev

logs:
	aws logs tail /aws/lambda/dev-lambda-processor --follow --endpoint-url http://localhost:4566

clean:
	terraform destroy -auto-approve || true
	docker stop localstack || true
	docker rm localstack || true
	rm -rf .terraform terraform.tfstate* lambda_function.zip