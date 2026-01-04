resource "aws_db_subnet_group" "this" {
	name       = "${var.identifier}-subnets"
	subnet_ids = var.subnet_ids
}

resource "aws_db_instance" "this" {
	identifier             = var.identifier
	allocated_storage      = var.allocated_storage
	engine                 = "postgres"
	engine_version         = var.engine_version
	instance_class         = var.instance_class

	db_name                = var.db_name
	username               = var.username
	password               = var.password

	db_subnet_group_name   = aws_db_subnet_group.this.name
	vpc_security_group_ids = var.vpc_security_group_ids

	publicly_accessible    = true
	skip_final_snapshot    = true
}
