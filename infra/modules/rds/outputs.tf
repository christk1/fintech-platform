output "address" {
  value       = aws_db_instance.this.address
  description = "DB hostname/address"
}

output "port" {
  value       = aws_db_instance.this.port
  description = "DB port"
}

output "endpoint" {
  value       = aws_db_instance.this.endpoint
  description = "DB endpoint host:port"
}

output "identifier" {
  value       = aws_db_instance.this.identifier
  description = "DB instance identifier"
}
