# oauth2-proxy Secret Rotation Runbook

This runbook describes how to rotate the secrets used by oauth2-proxy for MindWell (cookie encryption secret and upstream client credentials). Follow the checklist and log completion in the security change log.

## Preconditions
- Access to the `MindWell Auth` vault in 1Password.
- Administrative rights for the upstream identity provider (e.g. Azure AD, Google Workspace) configured for oauth2-proxy.
- Azure Key Vault permissions for `kv-mindwell-<env>` and AWS Secrets Manager access to `mindwell/<env>/oauth2-proxy/*` secrets.
- Ability to trigger GitHub Actions deploy workflows for the backend and oauth2-proxy manifests.

## Rotation Steps
1. **Schedule a Window**
   - Coordinate with product/CS teams to identify a low-traffic window (preferably 02:00–04:00 CST).
   - Announce expected impact (short-lived reauthentication) in `#ops-announcements` and pause staged deployments.

2. **Generate New Secrets**
   - Produce a 32-byte random string for `OAUTH2_PROXY_COOKIE_SECRET` (`openssl rand -hex 32`).
   - If required by the upstream IdP, create a new client secret and record the value in 1Password alongside timestamp metadata.

3. **Update Secret Stores**
   - Write the new cookie secret to AWS Secrets Manager (`mindwell/<env>/oauth2-proxy/cookie-secret`).
   - Mirror the value into Azure Key Vault `oauth2-proxy-cookie-secret` using `az keyvault secret set`.
   - Store refreshed upstream client secrets under `oauth2-proxy-client-secret` if applicable.

4. **Redeploy oauth2-proxy & Backend**
   - Trigger the `platform-secrets-refresh` GitHub Action to sync secrets into AKS ConfigMaps/Secrets.
   - Kick off the deployment pipelines for oauth2-proxy and the FastAPI backend so pods receive the updated values.

5. **Validate Authentication**
   - Confirm `/oauth2/start` redirects and completes successfully in staging.
   - Exercise the token exchange by visiting the web login panel; ensure `/api/auth/session` returns tokens and session cookies are refreshed.
   - Verify demo code login remains unaffected (`/api/auth/demo`).

6. **Retire Previous Secrets**
   - Revoke the prior upstream client secret in the IdP console (if rotated).
   - Remove the superseded secret versions in Key Vault and Secrets Manager after validation.

7. **Close & Monitor**
   - Update 1Password entries with rotation date, operator, and ticket reference.
   - Note completion in the security change log and notify stakeholders.
   - Monitor oauth2-proxy error logs and API 401 rates for the next 24 hours via Monitoring Agent dashboards.
