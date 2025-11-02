# Workload Identity Validation

This directory contains supporting assets for validating Azure AD workload identity on the MindWell AKS cluster. Apply the manifest after Terraform has provisioned the cluster and Key Vault integration.

## Prerequisites
- AKS cluster provisioned and reachable via `kubectl`.
- Workload identity federation configured (Terraform enables this by default).
- Key Vault secret populated with a test value.
- The managed identity client ID from Terraform output `aks_managed_identity_client_id`.

## Usage
1. Replace the placeholder values in `workload-identity-validation.yaml`:
   - `<WORKLOAD_IDENTITY_CLIENT_ID>`
   - `<AZURE_TENANT_ID>`
   - `<KEY_VAULT_NAME>`
   - `<SECRET_NAME>`
2. Apply the manifest:
   ```bash
   kubectl apply -f workload-identity-validation.yaml
   ```
3. Inspect the job logs:
   ```bash
   kubectl logs job/keyvault-secret-validation -n workload-identity-validation
   ```
   If the secret value is printed, workload identity is functioning.
4. Clean up resources:
   ```bash
   kubectl delete -f workload-identity-validation.yaml
   ```
