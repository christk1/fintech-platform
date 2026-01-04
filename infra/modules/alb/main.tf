resource "aws_lb" "this" {
	name               = var.name
	load_balancer_type = "application"
	internal           = false
	subnets            = var.subnet_ids
	security_groups    = var.security_group_ids
}

resource "aws_lb_target_group" "http" {
	name        = "${var.name}-tg"
	port        = var.target_port
	protocol    = "HTTP"
	vpc_id      = var.vpc_id
	target_type = "ip"

	health_check {
		path = "/healthz"
	}
}

resource "aws_lb_listener" "http" {
	load_balancer_arn = aws_lb.this.arn
	port              = 80
	protocol          = "HTTP"

	default_action {
		type             = "forward"
		target_group_arn = aws_lb_target_group.http.arn
	}
}
