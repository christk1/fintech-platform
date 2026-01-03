module "events_queue" {
  source = "../../modules/sqs-queue"

  name = var.events_queue_name
}
