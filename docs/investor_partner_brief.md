# MindWell Investor & Partner Brief

## 1. Executive Summary
- **Mission:** Deliver accessible, culturally attuned mental health support for Chinese-speaking users by combining empathetic AI coaching with licensed therapists.
- **Core Offering:** A hybrid assistant that triages conversations, generates actionable guidance, and recommends vetted therapists with transparent pricing and availability.
- **Differentiator:** Purpose-built Mandarin experience (voice + text), longitudinal journey insights, and automated compliance guardrails tuned for APAC privacy norms.

## 2. Market Opportunity
- **Audience:** Urban professionals and expatriates seeking discreet, on-demand support; secondary segments include campus wellness programs and corporate EAP partners.
- **Need:** Therapist scarcity (ratio < 2.5 / 100k) and rising anxiety / burnout rates create unmet demand for blended self-guided + live therapy journeys.
- **Addressable Channels:** Direct-to-consumer mobile app (iOS, Android), WeChat mini-program pilots, enterprise APIs for HR teams, and therapist marketplaces.

## 3. Product Experience
- **Conversational AI Coach:** Provides context-aware coping strategies, micro-exercises, and empathetic reflection using Azure OpenAI with AWS Bedrock failover.
- **Therapist Directory:** Localised profiles, availability slots, and science-backed matching. Browsing supports filtering by specialty, language, budget, and recommended status.
- **Journey Insights:** Daily/weekly summaries (“Spotlight” moments, mood deltas, recurring themes) power personal progress dashboards and therapist prep notes.
- **Explore Modules:** Guided breathing, psychoeducation micro-courses, and trend-driven content activated through feature flags for experimentation.

## 4. Intelligent Automation
- **Summary Scheduler Agent:** Generates and stores daily + weekly conversation summaries in S3, feeding Journey dashboards and therapist prep packets.
- **Data Sync Agent:** Normalises therapist rosters, applies locale-specific copy, and refreshes S3 payloads every four hours.
- **Monitoring Agent:** Samples Azure App Insights and AWS Cost Explorer, dispatching alerts when latency, error-rate, or spend guardrails are breached.
- **Retention & Privacy:** Automated purges, data subject export tooling, and PII scrubbing workflows satisfy regional compliance expectations.

## 5. Technology & Operations
- **Architecture:** FastAPI backend, Vite web client, Expo mobile app, Postgres primary store, S3 object storage, and Azure AKS for orchestration.
- **Observability:** Log Analytics + App Insights dashboards, runbook-backed alerting, and CI coverage (backend, web, mobile) executed via EC2-hosted GitHub runners.
- **Security:** OIDC workload identity across agents, scoped IAM roles, compartmentalised S3 buckets, and Key Vault–backed secret rotation.
- **Scalability:** Stateless APIs with horizontal auto-scaling, streaming chat endpoints, and RAG-ready embedding service for future therapist recommendations.

## 6. Commercial Model
- **Pricing Concepts:** Freemium chat access, premium subscription unlocking extended summaries + therapist matching, and per-session therapist commissions.
- **Cost Structure:** Estimated infrastructure baseline USD ~$162/month (compute, DB, storage) plus token usage (~$3 input / $15 output per 1M tokens in production).
- **Partnership Opportunities:** Shared revenue with therapist networks, white-label deployments for hospital groups, and API licensing for third-party wellness apps.

## 7. KPIs & Insight Streams
- **Engagement:** Daily active listeners, conversation depth, template utilisation, and repeat sessions.
- **Therapist Funnel:** Profile views → consultations → booked sessions tracked via analytics service and surfaced in partner dashboards.
- **Outcomes:** Mood deltas from Journey summaries, adherence to recommended exercises, and feedback loops captured during UAT pilots.
- **Governance:** Monitoring Agent logs, compliance audit trails, and incident response playbooks align with enterprise procurement requirements.

## 8. Roadmap Highlights
- **Near Term (0–3 months):** AKS provisioning, workload identity validation, therapist filtering refinements, and TestFlight / Android beta onboarding.
- **Mid Term (4–6 months):** Memory-aware RAG context injection, enterprise SSO integrations, and clinician back-office tooling.
- **Long Term (6–12 months):** Personalised care plans, multimodal sentiment tracking, localisation for additional APAC markets, and evidence-backed outcomes reporting.

## 9. Call to Action
- **Pilot Programs:** Corporate wellness cohorts and university counselling centres for structured feedback.
- **Investment Needs:** Capital for regulated clinician onboarding, expanded go-to-market, and additional model evaluation.
- **Contact:** partnerships@mindwell.example — briefing deck and sandbox access available upon request.

