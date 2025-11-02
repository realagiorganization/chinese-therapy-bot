locals {
  aws_private_az_a = var.aws_az_private_a != null ? var.aws_az_private_a : "${var.aws_region}a"
  aws_private_az_b = var.aws_az_private_b != null ? var.aws_az_private_b : "${var.aws_region}c"
  aws_public_az    = var.aws_az_public != null ? var.aws_az_public : "${var.aws_region}a"
}

resource "aws_vpc" "mindwell" {
  cidr_block           = var.aws_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = merge(
    local.default_tags,
    {
      Name = "mindwell-${var.environment}"
    },
  )
}

resource "aws_internet_gateway" "mindwell" {
  vpc_id = aws_vpc.mindwell.id
  tags   = merge(local.default_tags, { Name = "mindwell-${var.environment}-igw" })
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.mindwell.id
  cidr_block              = var.aws_public_subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = local.aws_public_az
  tags = merge(
    local.default_tags,
    {
      Name = "mindwell-${var.environment}-public"
      scope = "public"
    },
  )
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.mindwell.id
  cidr_block        = var.aws_private_subnet_cidrs[0]
  availability_zone = local.aws_private_az_a
  tags = merge(
    local.default_tags,
    {
      Name = "mindwell-${var.environment}-private-a"
      scope = "private"
    },
  )
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.mindwell.id
  cidr_block        = var.aws_private_subnet_cidrs[1]
  availability_zone = local.aws_private_az_b
  tags = merge(
    local.default_tags,
    {
      Name = "mindwell-${var.environment}-private-b"
      scope = "private"
    },
  )
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.mindwell.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.mindwell.id
  }
  tags = merge(
    local.default_tags,
    {
      Name = "mindwell-${var.environment}-public-rt"
    },
  )
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_db_subnet_group" "main" {
  name       = "mindwell-${var.environment}-db"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  tags       = merge(local.default_tags, { Name = "mindwell-${var.environment}-db-subnets" })
}

