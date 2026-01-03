output "events_queue_url" {
  value       = module.events_queue.queue_url
  description = "Queue URL for local events"
}
