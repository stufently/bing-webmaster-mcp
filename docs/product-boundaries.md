# Product boundaries

These are dated product decisions, not missing implementation work.

- **2026-08-25 — no SOAP or POX/XML.** Microsoft retires both on 2026-08-31. Only
  `.../api.svc/json/` is supported.
- **2026-08-25 — no Bing Search API or SERP scraping.** The classic Bing Search API is
  retired; Azure's replacement and scraping have different contracts and legal exposure.
- **2026-08-25 — no Google Search Console, GA4, or AdSense.** This is a focused Bing
  Webmaster implementation.
- **2026-08-25 — no apply or reject tool over MCP.** Prompt injection must not present
  its own approval as human review. Application remains a CLI operation.
- **2026-08-25 — no obsolete deep-link methods.** Microsoft marks
  `GetDeepLinkAlgoUrls`, `GetDeepLink`, and `UpdateDeepLink` obsolete.
- **2026-08-25 — OAuth2 is designed for but not implemented.** API-key authentication
  sits behind a provider interface so OAuth2 can be added when a user needs it.
- **2026-08-25 — no stored analytics, scheduler, or dashboard.** Stored state is limited
  to plans, audit records, and local write counters.
- **2026-08-25 — no hardcoded Bing quota.** Planning reads quota from Bing. The optional
  local ceiling is operator policy and is disabled by default.
- **2026-08-25 — Content Submission remains exposed.** Microsoft's current interface
  documents it without a beta label. Bing remains authoritative for account eligibility.
- **2026-08-25 — HTTP is loopback only.** The optional local transport also requires a
  bearer token; remote hosting needs a separate deployment-auth design.
