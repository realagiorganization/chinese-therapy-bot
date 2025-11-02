resource "random_password" "aws_rds_master" {
  length          = 24
  special         = true
  override_special = "!@#%^*-_=+"
}

resource "aws_security_group" "rds" {
  name        = "mindwell-${var.environment}-rds"
  description = "MindWell RDS ingress rules."
  vpc_id      = aws_vpc.mindwell.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.default_tags, { Name = "mindwell-${var.environment}-rds" })
}

resource "aws_security_group_rule" "rds_from_agent" {
  description              = "Allow agent hosts to connect to PostgreSQL."
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.agent.id
}

resource "aws_db_instance" "mindwell" {
  identifier = "mindwell-${var.environment}"

  engine               = "postgres"
  engine_version       = var.aws_rds_engine_version
  instance_class       = var.aws_rds_instance_class
  db_name              = var.aws_rds_database_name
  username             = var.aws_rds_master_username
  password             = random_password.aws_rds_master.result
  allocated_storage    = var.aws_rds_allocated_storage
  storage_type         = "gp3"
  max_allocated_storage = var.aws_rds_max_allocated_storage

  multi_az                    = var.aws_rds_multi_az
  storage_encrypted           = true
  publicly_accessible         = false
  performance_insights_enabled = var.aws_rds_performance_insights
  auto_minor_version_upgrade  = true
  deletion_protection         = var.aws_rds_deletion_protection
  backup_retention_period     = var.aws_rds_backup_retention_days
  maintenance_window          = var.aws_rds_maintenance_window
  backup_window               = var.aws_rds_backup_window
  skip_final_snapshot         = var.aws_rds_skip_final_snapshot

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  tags = merge(local.default_tags, { Name = "mindwell-${var.environment}-rds" })
}

resource "aws_secretsmanager_secret" "rds_master_credentials" {
  name = "mindwell/${var.environment}/rds/postgres"
  tags = merge(local.default_tags, { Name = "mindwell-${var.environment}-rds-credentials" })
}

resource "aws_secretsmanager_secret_version" "rds_master_credentials" {
  secret_id     = aws_secretsmanager_secret.rds_master_credentials.id
  secret_string = jsonencode({
    username = var.aws_rds_master_username
    password = random_password.aws_rds_master.result
    host     = aws_db_instance.mindwell.address
    port     = aws_db_instance.mindwell.port
    database = var.aws_rds_database_name
  })
}
