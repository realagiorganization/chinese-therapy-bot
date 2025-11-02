data "aws_ssm_parameter" "amazon_linux_2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_security_group" "agent" {
  name        = "mindwell-${var.environment}-agent"
  description = "Automation agent access rules."
  vpc_id      = aws_vpc.mindwell.id

  ingress {
    description = "SSH access to automation agents."
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.aws_agent_allowed_ssh_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.default_tags, { Name = "mindwell-${var.environment}-agent-sg" })
}

resource "aws_instance" "automation_agent" {
  ami                         = var.aws_agent_ami_id != null ? var.aws_agent_ami_id : data.aws_ssm_parameter.amazon_linux_2023.value
  instance_type               = var.aws_agent_instance_type
  subnet_id                   = aws_subnet.public.id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.agent.id]
  key_name                    = var.aws_agent_ssh_key_name
  monitoring                  = var.aws_agent_enable_detailed_monitoring

  root_block_device {
    encrypted   = true
    volume_size = var.aws_agent_root_volume_size
    volume_type = "gp3"
  }

  user_data = var.aws_agent_user_data

  tags = merge(
    local.default_tags,
    {
      Name = "mindwell-${var.environment}-agent-1"
      role = "automation-agent"
    },
  )
}

