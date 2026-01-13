resource "aws_cloudwatch_event_rule" "balance_reconcile_every_minute" {
  name                = "local-balance-reconcile-every-minute"
  description         = "Triggers a balance reconciliation event every minute (local testing)"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "balance_reconcile_to_sqs" {
  rule = aws_cloudwatch_event_rule.balance_reconcile_every_minute.name
  arn  = module.events_queue.queue_arn

  # Keep the message schema consistent with the HTTP publish endpoint.
  input = jsonencode({
    message_type = "balance.reconcile"
    payload = {
      trigger = "eventbridge"
      reason  = "scheduled"
    }
  })
}

data "aws_iam_policy_document" "allow_eventbridge_send_to_events_queue" {
  statement {
    sid    = "AllowEventBridgeSendMessage"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions   = ["sqs:SendMessage"]
    resources = [module.events_queue.queue_arn]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.balance_reconcile_every_minute.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "events_queue_allow_eventbridge" {
  queue_url = module.events_queue.queue_url
  policy    = data.aws_iam_policy_document.allow_eventbridge_send_to_events_queue.json
}
