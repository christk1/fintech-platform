provider "aws" {
  region                      = var.aws_region
  access_key                  = var.aws_access_key_id
  secret_key                  = var.aws_secret_access_key

  # LocalStack S3 needs path-style URLs (avoid bucketname.localhost DNS)
  s3_use_path_style           = true

  # LocalStack requirements
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  endpoints {
    cloudfront = var.localstack_endpoint
    ecs = var.localstack_endpoint
    elbv2 = var.localstack_endpoint
    elasticache = var.localstack_endpoint
    rds = var.localstack_endpoint
    sqs = var.localstack_endpoint
    sts = var.localstack_endpoint
    iam = var.localstack_endpoint
    ec2 = var.localstack_endpoint
    s3  = var.localstack_endpoint
  }
}
