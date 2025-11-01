# Encryption Validation Log

This log captures the current validation of encryption controls across MindWell infrastructure resources. It focuses on ensuring encryption at rest and enforcing TLS for data in transit, aligning with the Phase 6 compliance deliverables.

## Validation Summary

| Resource | Encryption at Rest | Encryption in Transit | Evidence / Notes |
| --- | --- | --- | --- |
| Azure PostgreSQL Flexible Server | Enabled by default with Azure-managed keys | TLS enforced (`require_secure_transport = true` via managed service) | `infra/terraform/azure_postgres.tf` provisions Flexible Server; Microsoft enforces storage encryption + requires TLS. |
| Azure Key Vault | Azure-managed encryption (with optional customer-managed keys) | REST APIs available only via HTTPS | Referenced in `infra/terraform/azure_keyvault.tf`; native service guarantees both controls. |
| Azure Kubernetes Service | Node OS disks + etcd encrypted (platform-managed keys) | API server exposes HTTPS endpoints only | `infra/terraform/azure_aks.tf`; AKS defaults verified against Microsoft documentation (2025-05). |
| AWS S3 – Conversation Logs | SSE-KMS enforced | Deny non-TLS access | `infra/terraform/aws_storage.tf`: `aws_s3_bucket_server_side_encryption_configuration.conversation_logs` + bucket policy `conversation_logs_secure_transport`. |
| AWS S3 – Summaries | SSE-KMS enforced | Deny non-TLS access | Same file: `aws_s3_bucket_server_side_encryption_configuration.summaries` and secure transport policy. |
| AWS S3 – Therapist Media | SSE-S3 enforced | Deny non-TLS access | Added resource `aws_s3_bucket_server_side_encryption_configuration.media` and `media_secure_transport` policy. |
| Chat & API Endpoints | TLS terminated at Application Gateway / CDN | Clients enforce HTTPS via service URLs | `services/backend/app/main.py` (FastAPI) assumes reverse-proxy TLS termination; `docs/data_governance.md` captures the HTTPS-only exposure policy for public endpoints. |

## Verification Steps

1. Reviewed Terraform modules to confirm server-side encryption blocks exist for every bucket and that Azure managed services rely on platform encryption defaults.
2. Added explicit bucket policies to deny unsecured (`http`) access to S3 buckets, ensuring TLS usage for API/agent interactions.
3. Confirmed backend service configuration assumes TLS termination at the ingress layer, matching infrastructure plans for Azure Application Gateway and CDN edges.

## Outstanding Considerations

- When customer-managed keys (CMKs) become available, rotate Terraform configuration to reference dedicated KMS/Key Vault keys and document rotation cadences.
- Ensure GitHub Actions runners set `AWS_USE_SSL=true` in environments that interact with S3 to avoid accidental plaintext transmission (tracked in `docs/ci_runner_agent.md`).
- Capture automated compliance evidence (e.g., AWS Config, Azure Policy assignments) once cloud accounts are provisioned to maintain continuous guarantees.
