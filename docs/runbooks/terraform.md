# Runbook – Terraform Plan & Apply

## Overview
This runbook supports infrastructure changes for Azure/AWS resources defined under `infra/terraform/`. It complements the `infra-plan` and `infra-apply` GitHub workflows introduced in Phase 7.

## 1. Preconditions
- Ensure required secrets are configured in GitHub (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AWS_TERRAFORM_ROLE_ARN`, region defaults).
- Acquire approval from platform lead before applying to production environments.
- Confirm `infra/terraform/environments/<env>/generated.auto.tfvars` exists or provide a secure tfvars file.

## 2. Generate Plan
1. Trigger **Terraform Plan** workflow (`.github/workflows/infra-plan.yml`) via GitHub UI, selecting target environment.
2. Review plan summary artifact `plan-<env>.txt` for resource changes and outputs.
3. Share plan summary in `#mindwell-infra` Slack channel for peer review.

## 3. Apply Changes
1. Trigger **Terraform Apply** workflow (`.github/workflows/infra-apply.yml`) with same environment.
2. The `plan` job will regenerate the plan artifact; wait for reviewers to approve the environment gate.
3. Once approved, the `apply` job downloads the signed plan and executes `infra/scripts/run_terraform_apply.sh --auto-approve`.
4. Monitor job logs for drift or apply failures; rerun with `TF_BACKEND_CONFIG_FILE` if remote state is required.

## 4. Manual CLI Execution
```
export AZURE_CLIENT_ID=...
export AZURE_TENANT_ID=...
export AZURE_SUBSCRIPTION_ID=...
export AWS_PROFILE=mindwell

./infra/scripts/run_terraform_plan.sh dev
./infra/scripts/run_terraform_apply.sh dev --auto-approve
```

## 5. Post-Apply Tasks
- Capture outputs and update shared password vault / Key Vault secrets if credentials rotate.
- Notify Monitoring Agent to validate alert baselines (AKS CPU, App Insights error rate).
- Log change summary with run ID in `docs/infra/changelog.md` (create if missing).
