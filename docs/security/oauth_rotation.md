# Google OAuth Secret Rotation Runbook

This runbook documents the process for rotating Google OAuth client secrets used by MindWell web and mobile clients. Follow the steps in order and record completion in the Security change log.

## Preconditions
- Access to the `MindWell OAuth` 1Password vault.
- Google Cloud project owner or editor permissions for the OAuth client.
- Azure Key Vault access policy covering `kv-mindwell-<env>` secrets.
- Firebase console access (if mobile apps consume the same credentials).

## Rotation Steps
1. **Schedule Maintenance**
   - Coordinate with Mobile and Web teams to identify a low-traffic window (typically 02:00–04:00 CST).
   - Notify CI Runner Agent owners; deployments will temporarily pause during rotation.

2. **Generate Replacement Secret**
   - In Google Cloud Console navigate to *APIs & Services → Credentials*.
   - Locate the OAuth client (`MindWell Web` or `MindWell Mobile`) and select *Reset secret*.
   - Copy the new client secret. Immediately store it in the 1Password entry as a new field labeled with ISO timestamp (e.g. `Secret 2025-05-08T02:30Z`).

3. **Update Firebase / Platform Integrations**
   - If the mobile app relies on Firebase, update the OAuth client secret in the Firebase console.
   - For TestFlight builds, update the Expo/React Native config values (see `clients/mobile/app.config.ts` once live).

4. **Propagate to Azure Key Vault**
   - Create a new secret version in `kv-mindwell-<env>` with the name `google-oauth-client-secret`.
   - Use the `az keyvault secret set` command or the Key Vault portal, pasting the freshly generated secret.
   - Tag the secret with `rotated-by`, `rotation-date`, and `notes` metadata for auditing.

5. **Sync to Kubernetes**
   - Trigger the `platform-secrets-refresh` GitHub Actions workflow.
   - Confirm the workflow completes and the new secret version is mounted in the AKS namespaces (`mindwell-backend`, `mindwell-agents`).

6. **Validate Authentication**
   - Run the regression suite `services/backend/tests/test_auth_google.py`.
   - Perform manual sign-in via staging web app to ensure the new secret works end-to-end.

7. **Retire Old Secret**
   - After successful validation, delete the previous secret version from Key Vault.
   - Update the 1Password record to mark the old secret entry as revoked.

8. **Close Out**
   - Notify stakeholders rotation completed.
   - Update the Security change log and PROGRESS checklist if applicable.
   - Monitoring Agent should confirm no increase in authentication failures over the next 24 hours.
