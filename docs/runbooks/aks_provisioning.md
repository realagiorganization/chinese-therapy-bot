---
title: Azure AKS Provisioning Runbook
---

# Azure AKS & AWS Storage Provisioning Runbook

This runbook turns the outstanding Phase 2 infrastructure tasks (AKS creation, workload identity validation, and AWS S3 provisioning) into a repeatable checklist. Follow it end-to-end whenever you need to stand up a new environment (e.g., `dev`, `staging`, `prod`).

> **Scope:** Terraform resources under `infra/terraform` plus supporting scripts in `infra/scripts/`. The process assumes you can authenticate to both Azure and AWS with the correct permissions.

---

## 1. Prerequisites

1. Install required CLIs:
   - Terraform `>= 1.5.0`
   - Azure CLI `az` `>= 2.60`
   - AWS CLI `aws` `>= 2.15`
2. Clone the repository and ensure you can run shell scripts (macOS/Linux or WSL recommended).
3. Collect credential details:
   - **Azure** subscription ID, tenant ID, and either:
     - A logged-in Azure CLI session (`az login`), _or_
     - Service principal credentials exported as `ARM_CLIENT_ID` + `ARM_CLIENT_SECRET`.
   - **AWS** account credentials with permission to create IAM roles, S3 buckets, VPCs, and RDS.
4. Optional but recommended: configure an Azure Storage account for Terraform remote state (see `infra/terraform/README.md`).

Run the automated preflight check to confirm tools and credentials:

```bash
./infra/scripts/check_cloud_prereqs.sh
```

Resolve any ❌ output before proceeding.

---

## 2. Prepare Environment Variables & tfvars

1. Copy the example tfvars and fill in real values:

   ```bash
   cp infra/terraform/dev.tfvars.example infra/terraform/dev.tfvars
   ```

   Update at minimum:
   - `environment`
   - `azure_subscription_id`
   - `azure_tenant_id`
   - `aws_account_id`
   - S3 bucket names (must be globally unique)
   - Budget contacts and Key Vault admin object IDs

2. If you use service principal authentication, export:

   ```bash
   export ARM_SUBSCRIPTION_ID=<subscription-id>
   export ARM_TENANT_ID=<tenant-id>
   export ARM_CLIENT_ID=<app-id>
   export ARM_CLIENT_SECRET=<password>
   ```

   Otherwise run `az login` and confirm the active subscription with `az account show`.

3. Make AWS credentials available (`aws configure`, environment variables, or `./infra/scripts/assume_ci_role.sh` if you are on the CI runner host).

4. (Optional) Define `TF_BACKEND_CONFIG_FILE` with the path to your backend configuration if you are using remote state:

   ```bash
   export TF_BACKEND_CONFIG_FILE=$PWD/infra/terraform/backend.hcl
   ```

---

## 3. Generate a Terraform Plan

Run the standard plan wrapper from the repo root:

```bash
./infra/scripts/run_terraform_plan.sh dev
```

Key behaviors:

- The script infers `dev.tfvars` automatically. Override by setting `TF_VARS_FILE`.
- A binary plan is written to `infra/terraform/environments/dev/plan-dev.tfplan`.
- A human-readable summary is produced at `infra/terraform/environments/dev/plan-dev.txt`.
- If you rely on remote state, ensure `TF_BACKEND_CONFIG_FILE` is exported before running the script.

Review `plan-dev.txt` for any unexpected changes before continuing.

---

## 4. Apply Terraform

Once reviewers sign off on the plan (or you are working in a sandbox account), apply the changes:

```bash
./infra/scripts/run_terraform_apply.sh dev
```

> The apply wrapper automatically reuses the most recent `plan-dev.tfplan`. If you need to override variables for a one-off apply, re-run the plan step first with the updated parameters.

During the apply you will provision:

- Azure resource group, virtual network, subnets
- AKS cluster (system + workload pools)
- Azure Database for PostgreSQL Flexible Server
- Log Analytics workspace, dashboards, and monitor alerts
- Azure Key Vault with CSI integration artifacts
- AWS VPC, subnets, internet gateway, route tables
- AWS S3 buckets (logs, summaries, media) with lifecycle policies
- AWS IAM roles/policies for automation agents and cross-cloud integrations
- AWS RDS (optional replica) and EC2 agent host baseline

---

## 5. Post-Apply Actions

1. **Bootstrap kubeconfig**  
   ```bash
   ./infra/scripts/bootstrap_kubeconfig.sh \
     --resource-group <rg-name> \
     --cluster-name <aks-cluster-name> \
     --output kubeconfig.dev
   ```
   Distribute the resulting kubeconfig to CI runners or developers as appropriate.

2. **Validate cluster access**
   ```bash
   KUBECONFIG=kubeconfig.dev kubectl get nodes
   ```
   You should see both system and workload node pools.

3. **Validate workload identity**  
   Apply the sample job that fetches a Key Vault secret:
   ```bash
   KUBECONFIG=kubeconfig.dev kubectl apply -f infra/kubernetes/samples/workload-identity-validation.yaml
   ```
   Inspect the job logs to confirm the secret retrieval succeeds, then clean up the sample resources.

4. **Confirm S3 buckets**  
   ```bash
   aws s3 ls | grep mindwell
   aws s3api get-bucket-lifecycle-configuration --bucket <bucket-name>
   ```
   Ensure lifecycle rules match expectations for transcripts and media retention.

5. **Record outputs**  
   Capture the relevant Terraform outputs for downstream automation (`terraform output -json` in `infra/terraform/environments/dev`). Store the kubeconfig path, AKS resource IDs, S3 bucket ARNs, IAM role ARNs, and database endpoints in your secrets manager or runbook notes.

---

## 6. Maintenance & Tear-Down

- **Re-run plan/apply:** Use the same wrappers whenever you modify Terraform modules. Always check `plan-dev.txt` into change reviews for visibility.
- **Rotate credentials:** Update Key Vault secrets and AWS access keys per the cadence documented in `ENVS.md`.
- **Destroy environment:** Only in disposable environments, run `terraform destroy` from `infra/terraform/environments/dev` (no helper script is provided to reduce accidental deletion risk).

---

## 7. Troubleshooting

| Symptom | Likely Cause | Resolution |
| --- | --- | --- |
| `azurerm` provider fails with authentication error | Missing ARM_* variables and `az login` not active | Re-run `az login` or export service principal credentials |
| `aws` provider fails with `NoCredentialProviders` | AWS CLI not configured | Run `aws configure`, source credentials, or use `assume_ci_role.sh` |
| `kubectl get nodes` times out | AKS not yet provisioned or kubeconfig not applied | Wait for cluster creation to finish, then re-run `bootstrap_kubeconfig.sh` |
| Workload identity job fails to fetch secret | Federated identity missing or Key Vault access policy not applied | Re-run Terraform (ensures identities are created) and check `infra/kubernetes/samples/README.md` for troubleshooting steps |

---

## 8. Next Steps

- Deploy automation agents defined in `infra/kubernetes/agents/` once AKS is live.
- Coordinate with the CI Runner Agent team to upload the kubeconfig and configure GitHub OIDC trust relationships.
- Move on to Phase 6 user acceptance testing once infrastructure is confirmed stable.
