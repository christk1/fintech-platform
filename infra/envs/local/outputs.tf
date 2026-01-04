output "events_queue_url" {
  value       = module.events_queue.queue_url
  description = "Queue URL for local events"
}
 
output "ecs_cluster_arn" {
  value = module.ecs.cluster_arn
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "alb_arn" {
  value = module.alb.alb_arn
}

output "rds_endpoint" {
  value = module.rds.endpoint
}

output "rds_address" {
  value = module.rds.address
}

output "redis_endpoint" {
  value = module.redis.endpoint
}

output "redis_port" {
  value = module.redis.port
}

output "cloudfront_domain_name" {
  value = module.cloudfront.domain_name
}
