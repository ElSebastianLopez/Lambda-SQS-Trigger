terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  
  endpoints {
    sqs    = "http://localhost:4566"
    lambda = "http://localhost:4566"
    iam    = "http://localhost:4566"
    logs   = "http://localhost:4566"
  }
}

# Variables para simular múltiples ambientes
variable "environments" {
  default = ["dev", "qa", "uat"]
}

variable "queue_types" {
  default = ["masivo-kit", "masivo-cotizacion", "masivo-emision", "masivo-suscripcion-cotizacion"]
}

# IAM Role para Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Crear todas las colas SQS (3 ambientes x 4 tipos = 12 colas)
resource "aws_sqs_queue" "all_queues" {
  for_each = {
    for item in flatten([
      for env in var.environments : [
        for queue in var.queue_types : {
          key   = "${env}-${queue}"
          env   = env
          queue = queue
          name  = "${env}-andina-core-${queue}"
        }
      ]
    ]) : item.key => item
  }
  
  name                       = each.value.name
  visibility_timeout_seconds = 60
  message_retention_seconds  = 3600  # 1 hora para testing
}

# Lambda Archive
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda_function.zip"
}

# Una Lambda por ambiente
resource "aws_lambda_function" "processor" {
  for_each = toset(var.environments)
  
  function_name    = "${each.key}-lambda-processor"
  handler          = "handler.handler"
  runtime          = "python3.11"
  role            = aws_iam_role.lambda_exec.arn
  filename        = data.archive_file.lambda_zip.output_path
  source_code_hash = filebase64sha256(data.archive_file.lambda_zip.output_path)
  timeout         = 60
  
  environment {
    variables = {
      ENVIRONMENT = each.key
    }
  }
}

# Event Source Mappings (cada lambda escucha sus 4 colas)
resource "aws_lambda_event_source_mapping" "triggers" {
  for_each = {
    for item in flatten([
      for env in var.environments : [
        for queue in var.queue_types : {
          key        = "${env}-${queue}"
          env        = env
          queue      = queue
          queue_name = "${env}-andina-core-${queue}"
        }
      ]
    ]) : item.key => item
  }
  
  event_source_arn = aws_sqs_queue.all_queues[each.key].arn
  function_name    = aws_lambda_function.processor[each.value.env].arn
  batch_size       = 1
  enabled          = true
}

# Outputs útiles
output "queue_urls" {
  value = {
    for k, v in aws_sqs_queue.all_queues : k => v.url
  }
}

output "test_commands" {
  value = {
    dev = "aws sqs send-message --queue-url ${aws_sqs_queue.all_queues["dev-masivo-suscripcion-cotizacion"].url} --message-body '{\"id\": 12345}' --endpoint-url http://localhost:4566"
    qa  = "aws sqs send-message --queue-url ${aws_sqs_queue.all_queues["qa-masivo-suscripcion-cotizacion"].url} --message-body '{\"id\": 12345}' --endpoint-url http://localhost:4566"
    uat = "aws sqs send-message --queue-url ${aws_sqs_queue.all_queues["uat-masivo-suscripcion-cotizacion"].url} --message-body '{\"id\": 12345}' --endpoint-url http://localhost:4566"
  }
}