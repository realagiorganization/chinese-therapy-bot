locals {
  s3_bucket_encryption = {
    server_side_encryption_configuration = [{
      rule = {
        apply_server_side_encryption_by_default = {
          sse_algorithm = "aws:kms"
        }
      }
    }]
  }
}

resource "aws_s3_bucket" "conversation_logs" {
  bucket = var.s3_logs_bucket_name
  tags   = local.default_tags
}

resource "aws_s3_bucket_versioning" "conversation_logs" {
  bucket = aws_s3_bucket.conversation_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "conversation_logs" {
  bucket = aws_s3_bucket.conversation_logs.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "conversation_logs" {
  bucket                  = aws_s3_bucket.conversation_logs.id
  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket" "summaries" {
  bucket = var.s3_summaries_bucket_name
  tags   = local.default_tags
}

resource "aws_s3_bucket_versioning" "summaries" {
  bucket = aws_s3_bucket.summaries.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "summaries" {
  bucket = aws_s3_bucket.summaries.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "summaries" {
  bucket                  = aws_s3_bucket.summaries.id
  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket" "media" {
  bucket = var.s3_media_bucket_name
  tags   = local.default_tags
}

resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    allowed_headers = ["*"]
    max_age_seconds = 300
  }
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = false
  block_public_policy     = false
  restrict_public_buckets = false
  ignore_public_acls      = false
}

data "aws_iam_policy_document" "ci_runner_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.aws_account_id}:root"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ci_runner" {
  name               = var.ci_runner_role_name
  assume_role_policy = data.aws_iam_policy_document.ci_runner_assume_role.json
  tags               = local.default_tags
}

data "aws_iam_policy_document" "ci_runner_policy" {
  statement {
    sid    = "S3Access"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.conversation_logs.arn,
      "${aws_s3_bucket.conversation_logs.arn}/*",
      aws_s3_bucket.summaries.arn,
      "${aws_s3_bucket.summaries.arn}/*",
      aws_s3_bucket.media.arn,
      "${aws_s3_bucket.media.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "ci_runner_inline" {
  name   = "ci-runner-s3-access"
  role   = aws_iam_role.ci_runner.id
  policy = data.aws_iam_policy_document.ci_runner_policy.json
}
