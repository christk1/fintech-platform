variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_access_key_id" {
  type    = string
  default = "test"
}

variable "aws_secret_access_key" {
  type    = string
  default = "test"
}

variable "localstack_endpoint" {
  type        = string
  description = "LocalStack edge endpoint"
  default     = "http://localhost:4566"
}

variable "events_queue_name" {
  type        = string
  description = "SQS queue name used by the local environment"
  default     = "fintech-local-events"
}
