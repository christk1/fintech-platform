provider "aws" {
  region                      = var.aws_region
  access_key                  = var.aws_access_key_id
  secret_key                  = var.aws_secret_access_key

  # LocalStack requirements
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  endpoints {
    sqs = var.localstack_endpoint
    sts = var.localstack_endpoint
    iam = var.localstack_endpoint
    ec2 = var.localstack_endpoint
    s3  = var.localstack_endpoint
  }
}
