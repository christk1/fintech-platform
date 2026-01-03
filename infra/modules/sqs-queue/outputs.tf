output "queue_url" {
  value       = aws_sqs_queue.this.url
  description = "SQS Queue URL"
}

output "queue_arn" {
  value       = aws_sqs_queue.this.arn
  description = "SQS Queue ARN"
}
