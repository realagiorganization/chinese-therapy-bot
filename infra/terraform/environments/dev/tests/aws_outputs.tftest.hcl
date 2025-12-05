mock_provider "azurerm" {
  mock_resource "azurerm_kubernetes_cluster" {
    defaults = {
      kubelet_identity = [{
        object_id                 = "44444444-4444-4444-4444-444444444444"
        client_id                 = "55555555-5555-5555-5555-555555555555"
        user_assigned_identity_id = null
      }]
    }
  }
}

mock_provider "aws" {}

mock_provider "random" {}

run "aws_outputs_and_metadata" {
  command = plan

  variables {
    project_name                        = "MindWell"
    environment                         = "dev"
    azure_subscription_id               = "00000000-0000-0000-0000-000000000000"
    azure_tenant_id                     = "11111111-1111-1111-1111-111111111111"
    azure_location                      = "eastasia"
    aws_region                          = "ap-northeast-1"
    vnet_address_space                  = ["10.25.0.0/16"]
    subnet_aks_system                   = "10.25.1.0/24"
    subnet_aks_workload                 = "10.25.2.0/24"
    subnet_postgres                     = "10.25.3.0/24"
    oncall_email                        = "oncall@mindwell.dev"
    oncall_country_code                 = "86"
    oncall_phone                        = "13800138000"
    aks_version                         = "1.29.4"
    aks_service_cidr                    = "10.26.0.0/16"
    aks_dns_service_ip                  = "10.26.0.10"
    postgres_sku_name                   = "GP_Standard_D4s_v3"
    key_vault_admin_object_id           = "33333333-3333-3333-3333-333333333333"
    key_vault_allowed_ips               = ["20.30.40.50"]
    placeholder_openai_api_key          = "sk-test-placeholder"
    kubelet_identity_object_id_override = "44444444-4444-4444-4444-444444444444"
  }

  override_data {
    target = data.aws_iam_policy_document.ci_runner_assume
    values = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"ec2.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"
    }
  }

  assert {
    condition     = aws_s3_bucket.conversation_logs.bucket == "mindwell-dev-conversation-logs"
    error_message = "Conversation log bucket name drifted from the expected <prefix>-<env>-conversation-logs pattern."
  }

  assert {
    condition     = aws_s3_bucket.summaries.bucket == "mindwell-dev-summaries"
    error_message = "Summaries bucket name drifted from the expected <prefix>-<env>-summaries pattern."
  }

  assert {
    condition     = aws_s3_bucket.media.bucket == "mindwell-dev-media"
    error_message = "Media bucket name drifted from the expected <prefix>-<env>-media pattern."
  }

  assert {
    condition     = aws_secretsmanager_secret.openai_api_key.name == "mindwell/dev/openai-api-key"
    error_message = "Secrets Manager naming drift detected. Expected mindwell/dev/openai-api-key."
  }

  assert {
    condition     = aws_iam_role.ci_runner.name == "mindwell-dev-ci-runner"
    error_message = "CI runner role name drifted and no longer matches the naming convention."
  }

  assert {
    condition     = aws_iam_role_policy.ci_runner_s3.name == "mindwell-dev-ci-s3"
    error_message = "CI runner inline policy should retain the mindwell-dev-ci-s3 naming convention."
  }

  assert {
    condition     = output.s3_conversation_logs_bucket == aws_s3_bucket.conversation_logs.bucket
    error_message = "Output s3_conversation_logs_bucket no longer mirrors the actual bucket name."
  }

  assert {
    condition     = output.s3_summaries_bucket == aws_s3_bucket.summaries.bucket
    error_message = "Output s3_summaries_bucket no longer mirrors the actual bucket name."
  }

  assert {
    condition     = output.s3_media_bucket == aws_s3_bucket.media.bucket
    error_message = "Output s3_media_bucket no longer mirrors the actual bucket name."
  }
}
