output "bucket_name" {
  value       = aws_s3_bucket.origin.bucket
  description = "Origin bucket name"
}

output "distribution_id" {
  value       = aws_cloudfront_distribution.this.id
  description = "CloudFront distribution id"
}

output "domain_name" {
  value       = aws_cloudfront_distribution.this.domain_name
  description = "CloudFront distribution domain"
}
