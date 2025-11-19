# Dev Infrastructure Provisioning Runbook

This guide captures the repeatable steps for standing up the **dev** Azure/AWS
infrastructure described in `PROGRESS.md` Phase 2, gathering kubeconfig
artifacts, and validating workload identity.

## 1. Prerequisites

Install the following tools locally or on the automation runner:

- [Terraform](https://developer.hashicorp.com/terraform/downloads) v1.6+
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (for AKS kubeconfig)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) (only needed for the optional OIDC check)
- `jq` for parsing Terraform outputs

Ensure the repository root contains an `artifacts/` directory or let the script
create it for you.

## 2. Authenticate against Azure & AWS

### Azure (azurerm provider)

Export the `ARM_*` environment variables for your service principal:

```bash
export ARM_TENANT_ID="<tenant>"
export ARM_SUBSCRIPTION_ID="<subscription>"
export ARM_CLIENT_ID="<appId>"
export ARM_CLIENT_SECRET="<password>"
```

Alternatively, log in with the Azure CLI (`az login`) and Terraform will reuse
the active context.

### AWS (S3/IAM resources)

Use either long‑lived credentials or an assumed role:

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-1
# or rely on AWS_PROFILE / aws sts assume-role etc.
```

## 2.5. Populate the environment tfvars

The root module expects a `dev.auto.tfvars` (or similar) file inside
`infra/terraform/environments/dev/`. Copy the new template
`dev.auto.tfvars.example` into place and replace the placeholder GUIDs, CIDRs,
and contact details with your real subscription/account values:

```bash
cp infra/terraform/environments/dev/dev.auto.tfvars.example \
   infra/terraform/environments/dev/dev.auto.tfvars
```

Store sensitive secrets (e.g., `placeholder_openai_api_key`) in your preferred
secret manager or `tfvars` file and avoid committing real values to the repo.

## 2.7. Offline readiness check (no cloud credentials required)

Before attempting the real plan/apply flow, run the lightweight readiness helper
to ensure formatting, validation, and the Terraform tests (including the new
AWS outputs/policy guardrail suite) all pass locally:

```bash
./infra/scripts/check_infra_readiness.sh --environment dev
```

Flags allow you to skip specific stages (fmt/validate/tests) when iterating, and
the script forces `terraform init` to use a local backend so it works in air‑
gapped environments. Keeping this check green guarantees the mocked tests catch
bucket/ARN/policy drift early, which in turn shortens the later apply cycle.

## 3. Run the provisioning helper

The helper script lives at `infra/scripts/provision_dev_infra.sh` and wraps the
full Terraform flow inside `infra/terraform/environments/<env>`.

```bash
./infra/scripts/provision_dev_infra.sh \
  --environment dev \
  --tfvars infra/terraform/environments/dev/generated.auto.tfvars \
  --backend-config infra/terraform/backend.hcl
```

The script now performs lightweight Azure/AWS credential checks before running
Terraform so you fail fast instead of waiting for the providers to error out.
Pass `--skip-credential-checks` only if you are injecting credentials through an
alternate mechanism (e.g., custom `AWS_PROFILE` resolution inside a wrapper).

What the script does:

1. Runs `terraform init/plan/apply` for the chosen environment.
2. Stores the plan (`*.tfplan`) and JSON outputs under
   `artifacts/provisioning/<env>/`.
3. Fetches the AKS kubeconfig via `az aks get-credentials` and saves it as
   `artifacts/provisioning/<env>/kubeconfig-<env>.yaml`.

### Flags

- `--plan-only` — stop after saving the plan artifact.
- `--skip-kubeconfig` — do not call `az aks get-credentials`.
- `--validate-oidc` — run the workload identity validation job described below.
- `--skip-credential-checks` — bypass the new Azure/AWS credential guard (not
  recommended unless you are absolutely sure Terraform will be able to obtain
  credentials another way).

## 4. Optional: workload identity validation

The helper script `infra/scripts/validate_workload_identity.sh` renders the
sample manifest, injects the kubelet identity client ID + Key Vault name, runs
the validation job, captures the logs, and optionally cleans up the namespace.

It accepts either explicit flags for the required identifiers or a pointer to
the JSON file produced by `terraform output -json`:

```bash
./infra/scripts/validate_workload_identity.sh \
  --terraform-outputs artifacts/provisioning/dev/dev-terraform-outputs.json \
  --kubeconfig artifacts/provisioning/dev/kubeconfig-dev.yaml \
  --environment dev \
  --secret-name postgres-admin-password
```

The script stores the rendered manifest logs under
`artifacts/oidc-validation/<env>-oidc-<timestamp>.log`. Because the pod prints
the actual Key Vault secret value, handle the log file carefully or delete it
after confirming success.

Passing `--validate-oidc` to `provision_dev_infra.sh` now invokes the helper
above automatically (with values sourced from the freshly-written Terraform
outputs). Use this evidence when checking off the “Validate workload
identity/OIDC” item inside `PROGRESS.md`.
Override the default secret or timeout by exporting `OIDC_SECRET_NAME` /
`OIDC_VALIDATION_TIMEOUT` before running the provisioning helper.

## 5. Capturing bucket/IAM outputs

After a successful apply, inspect the JSON file created in
`artifacts/provisioning/<env>/<env>-terraform-outputs.json`. It includes:

- AKS resource group/name + OIDC issuer
- Azure Postgres FQDN and Key Vault URI
- S3 bucket names (conversations, summaries, media)
- CI runner IAM role ARN

Provide these identifiers to the Monitoring/Data Sync agents or CI pipelines as
needed.

### Automated storage export helper

When only the AWS storage + CI runner values are required, run
`infra/scripts/export_storage_outputs.sh`. The script expects that `terraform
apply` already ran inside `infra/terraform/environments/<env>` (so the state and
outputs exist) and will emit two files:

```bash
./infra/scripts/export_storage_outputs.sh dev \
  --out-dir artifacts/storage/dev
```

- `artifacts/storage/dev/storage-outputs.json`
- `artifacts/storage/dev/storage-outputs.env`

The JSON file mirrors the Terraform output keys, while the `.env` file contains
shell‑friendly variables (`CONVERSATION_LOGS_BUCKET_ARN`, `SUMMARIES_BUCKET_ARN`,
`MEDIA_BUCKET_ARN`, `CI_RUNNER_ROLE_ARN`) for drop‑in usage by CI workflows or
agent bootstrap scripts. The helper fails fast if any of the expected outputs
are missing so you know to re-run Terraform first.
