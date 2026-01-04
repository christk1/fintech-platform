variable "name" {
  type        = string
  description = "ALB name"
}

variable "vpc_id" {
  type        = string
  description = "VPC id"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Public subnet ids for the ALB"
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups attached to the ALB"
}

variable "target_port" {
  type        = number
  description = "Target group port"
  default     = 8000
}
