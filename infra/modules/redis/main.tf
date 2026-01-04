resource "aws_elasticache_subnet_group" "this" {
	name       = "${var.name}-subnets"
	subnet_ids = var.subnet_ids
}

resource "aws_elasticache_cluster" "this" {
	cluster_id           = var.name
	engine               = "redis"
	engine_version       = var.engine_version
	node_type            = var.node_type
	num_cache_nodes      = var.num_cache_nodes
	port                 = 6379
	subnet_group_name    = aws_elasticache_subnet_group.this.name
	security_group_ids   = var.security_group_ids
}
