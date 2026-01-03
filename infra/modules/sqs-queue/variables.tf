variable "name" {
  type        = string
  description = "Queue name"
}

variable "visibility_timeout_seconds" {
  type        = number
  description = "Visibility timeout"
  default     = 30
}

variable "message_retention_seconds" {
  type        = number
  description = "Message retention"
  default     = 345600 # 4 days
}
