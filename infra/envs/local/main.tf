module "events_queue" {
  source = "../../modules/sqs"

  name = var.events_queue_name
}
