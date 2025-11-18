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

run "s3_hardening" {
  command = plan

  variables {
    project_name               = "MindWell"
    environment                = "dev"
    azure_subscription_id      = "00000000-0000-0000-0000-000000000000"
    azure_tenant_id            = "11111111-1111-1111-1111-111111111111"
    azure_location             = "eastasia"
    aws_region                 = "ap-northeast-1"
    vnet_address_space         = ["10.20.0.0/16"]
    subnet_aks_system          = "10.20.1.0/24"
    subnet_aks_workload        = "10.20.2.0/24"
    subnet_postgres            = "10.20.3.0/24"
    oncall_email               = "oncall@mindwell.dev"
    oncall_country_code        = "86"
    oncall_phone               = "13800138000"
    aks_version                = "1.29.4"
    aks_service_cidr           = "10.21.0.0/16"
    aks_dns_service_ip         = "10.21.0.10"
    postgres_sku_name          = "GP_Standard_D4s_v3"
    key_vault_admin_object_id  = "33333333-3333-3333-3333-333333333333"
    placeholder_openai_api_key = "sk-test-placeholder"
    kubelet_identity_object_id_override = "44444444-4444-4444-4444-444444444444"
  }

  override_data {
    target = data.aws_iam_policy_document.ci_runner_assume
    values = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }

  assert {
    condition     = aws_s3_bucket_versioning.conversation_logs.versioning_configuration[0].status == "Enabled"
    error_message = "Conversation log buckets must enable versioning."
  }

  assert {
    condition     = aws_s3_bucket_versioning.summaries.versioning_configuration[0].status == "Enabled"
    error_message = "Summary buckets must enable versioning."
  }

  assert {
    condition     = tolist(aws_s3_bucket_server_side_encryption_configuration.conversation_logs.rule)[0].apply_server_side_encryption_by_default[0].sse_algorithm == "aws:kms"
    error_message = "Conversation log buckets must enforce AWS KMS encryption."
  }

  assert {
    condition     = tolist(aws_s3_bucket_server_side_encryption_configuration.summaries.rule)[0].apply_server_side_encryption_by_default[0].sse_algorithm == "aws:kms"
    error_message = "Summary buckets must enforce AWS KMS encryption."
  }

  assert {
    condition     = tolist(aws_s3_bucket_server_side_encryption_configuration.media.rule)[0].apply_server_side_encryption_by_default[0].sse_algorithm == "AES256"
    error_message = "Media buckets must enforce AES-256 encryption."
  }

  assert {
    condition = alltrue([
      aws_s3_bucket_public_access_block.conversation_logs.block_public_acls,
      aws_s3_bucket_public_access_block.conversation_logs.block_public_policy,
      aws_s3_bucket_public_access_block.conversation_logs.restrict_public_buckets,
      aws_s3_bucket_public_access_block.conversation_logs.ignore_public_acls,
      aws_s3_bucket_public_access_block.summaries.block_public_acls,
      aws_s3_bucket_public_access_block.summaries.block_public_policy,
      aws_s3_bucket_public_access_block.summaries.restrict_public_buckets,
      aws_s3_bucket_public_access_block.summaries.ignore_public_acls,
    ])
    error_message = "Conversation log and summary buckets must block all public ACL/policy combinations."
  }

  assert {
    condition = alltrue([
      aws_s3_bucket_public_access_block.media.block_public_acls == false,
      aws_s3_bucket_public_access_block.media.block_public_policy == false,
      aws_s3_bucket_public_access_block.media.restrict_public_buckets == false,
      aws_s3_bucket_public_access_block.media.ignore_public_acls == false,
    ])
    error_message = "Media bucket intentionally keeps ACL/policy blocks disabled for CDN access; configuration drift detected."
  }

  assert {
    condition = (
      contains([for t in aws_s3_bucket_lifecycle_configuration.conversation_logs.rule[0].transition : t.days], 30) &&
      contains([for t in aws_s3_bucket_lifecycle_configuration.conversation_logs.rule[0].transition : t.days], 90) &&
      contains([for e in aws_s3_bucket_lifecycle_configuration.conversation_logs.rule[0].expiration : e.days], 365)
    )
    error_message = "Conversation log lifecycle rules must tier at 30/90 days and expire after 365 days."
  }

  assert {
    condition = tolist(aws_s3_bucket_lifecycle_configuration.media.rule[0].abort_incomplete_multipart_upload)[0].days_after_initiation == 7
    error_message = "Media lifecycle configuration must abort incomplete uploads after 7 days."
  }
}
