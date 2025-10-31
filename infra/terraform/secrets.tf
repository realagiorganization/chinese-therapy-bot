resource "aws_secretsmanager_secret" "openai_api_key" {
  name = "mindwell/${var.environment}/openai/api-key"
  tags = local.default_tags
}

resource "aws_secretsmanager_secret" "bedrock_model_id" {
  name = "mindwell/${var.environment}/bedrock/model-id"
  tags = local.default_tags
}

resource "aws_secretsmanager_secret" "sms_provider_api_key" {
  name = "mindwell/${var.environment}/sms-provider/api-key"
  tags = local.default_tags
}

resource "aws_secretsmanager_secret" "therapist_data_ingest" {
  name = "mindwell/${var.environment}/therapists/ingest"
  tags = local.default_tags
}
