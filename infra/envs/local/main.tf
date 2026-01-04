module "events_queue" {
  source = "../../modules/sqs"

  name = var.events_queue_name
}

resource "aws_vpc" "main" {
  cidr_block = "10.10.0.0/16"
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.10.1.0/24"
  availability_zone = "us-east-1a"
}

resource "aws_subnet" "public_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.10.2.0/24"
  availability_zone = "us-east-1b"
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "alb" {
  name   = "local-alb"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name   = "local-db"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "redis" {
  name   = "local-redis"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

module "ecs" {
  source = "../../modules/ecs"

  cluster_name = "local-ecs"
}

module "alb" {
  source = "../../modules/alb"

  name               = "local-alb"
  vpc_id             = aws_vpc.main.id
  subnet_ids         = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  security_group_ids = [aws_security_group.alb.id]
  target_port        = 8000
}

module "rds" {
  source = "../../modules/rds"

  identifier             = "local-postgres"
  db_name                = "fintech"
  username               = "postgres"
  password               = "postgres"
  subnet_ids             = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  vpc_security_group_ids = [aws_security_group.db.id]
}

module "redis" {
  source = "../../modules/redis"

  name               = "local-redis"
  subnet_ids         = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  security_group_ids = [aws_security_group.redis.id]
}

module "cloudfront" {
  source = "../../modules/cloudfront"

  bucket_name = "fintech-local-cdn-origin"
}
