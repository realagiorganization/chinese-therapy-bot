# CI Runner Agent – AWS Role Assumption Guide

The CI Runner Agent executes GitHub Actions workflows on self-hosted EC2 runners. This guide documents how the runner acquires temporary AWS credentials to access S3 buckets and other infrastructure defined in Terraform.

## Prerequisites
- Runner EC2 instance joined to the GitHub Actions self-hosted runner pool.
- IAM role configured with trust policy for the GitHub OIDC provider (see `infra/terraform/aws_storage.tf` outputs).
- `aws` CLI v2, `curl`, and `jq` installed on the runner AMI.

## Usage in GitHub Actions

Add the following step prior to any AWS CLI/Terraform commands:

```yaml
- name: Assume AWS role for S3 access
  shell: bash
  run: infra/scripts/assume_ci_role.sh "${{ secrets.AWS_CI_ROLE_ARN }}" "mindwell-ci-${{ github.run_id }}"
```

The script performs these actions:
1. Requests a GitHub OIDC token using `ACTIONS_ID_TOKEN_REQUEST_URL` / `ACTIONS_ID_TOKEN_REQUEST_TOKEN`.
2. Calls `aws sts assume-role-with-web-identity` for the supplied role ARN.
3. Appends the resulting credentials to `GITHUB_ENV`, exposing them to subsequent steps as standard environment variables.

### Validation Step

Optionally verify the credentials by listing the target S3 bucket:

```yaml
- name: Verify S3 access
  shell: bash
  env:
    S3_BUCKET: ${{ needs.provision.outputs.conversation_logs_bucket }}
  run: aws s3 ls "s3://${S3_BUCKET}" --summarize
```

## Local Debugging

For engineers replicating CI failures locally, use `scripts/bootstrap-local-env.sh`:

```bash
./scripts/bootstrap-local-env.sh arn:aws:iam::123456789012:role/mindwell-sandbox-developer
source .env.local
```

The script writes temporary credentials into `.env.local` and echoes the expiration timestamp. Re-run the script to refresh.

## Monitoring & Expiration

- GitHub Actions automatically revokes credentials when the workflow ends.
- The Monitoring Agent ingests CloudTrail events to ensure only GitHub runner principals assume the CI role.
- Alerts fire if assumptions originate from unexpected AWS principals or outside standard CI maintenance windows (02:00–05:00 UTC).
