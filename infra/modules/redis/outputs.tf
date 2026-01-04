output "cluster_id" {
  value       = aws_elasticache_cluster.this.cluster_id
  description = "ElastiCache cluster id"
}

output "endpoint" {
  value       = aws_elasticache_cluster.this.cache_nodes[0].address
  description = "Redis endpoint host"
}

output "port" {
  value       = aws_elasticache_cluster.this.cache_nodes[0].port
  description = "Redis endpoint port"
}
