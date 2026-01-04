variable "identifier" {
  type        = string
  description = "DB instance identifier"
}

variable "db_name" {
  type        = string
  description = "Initial database name"
  default     = "fintech"
}

variable "username" {
  type        = string
  description = "Master username"
}

variable "password" {
  type        = string
  description = "Master password"
  sensitive   = true
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for the DB subnet group"
}

variable "vpc_security_group_ids" {
  type        = list(string)
  description = "Security groups attached to the DB instance"
}

variable "instance_class" {
  type        = string
  description = "RDS instance class"
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  type        = number
  description = "Allocated storage (GiB)"
  default     = 20
}

variable "engine_version" {
  type        = string
  description = "Postgres engine version"
  default     = "16"
}
