variable "name" {
  type        = string
  description = "ElastiCache cluster name"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for the cache subnet group"
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups attached to the cache cluster"
}

variable "node_type" {
  type        = string
  description = "ElastiCache node type"
  default     = "cache.t3.micro"
}

variable "num_cache_nodes" {
  type        = number
  description = "Number of cache nodes"
  default     = 1
}

variable "engine_version" {
  type        = string
  description = "Redis engine version"
  default     = "7.0"
}
