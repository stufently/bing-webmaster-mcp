# Product boundaries

These are dated product decisions, not missing implementation work.

- **2026-08-25 — no SOAP or POX/XML.** Microsoft retires both on 2026-08-31. Only
  `.../api.svc/json/` is supported.
- **2026-08-25 — no Bing Search API or SERP scraping.** The classic Bing Search API is
  retired; Azure's replacement and scraping have different contracts and legal exposure.
- **2026-08-25 — no Google Search Console, GA4, or AdSense.** This is a focused Bing
  Webmaster implementation.
- **2026-08-25 — no apply or reject tool over MCP.** Prompt injection must not present
  its own approval as human review. No MCP tool accepts a plan ID, so a plan recorded
  for review is applied or rejected only at the CLI.
- **2026-08-30 — no idempotency key for one-step writes.** `BING_WM_ALLOW_WRITES=true`
  makes a write repeatable by retrying the call: each retry records a new plan and sends
  the change again. The one-shot guarantee is per plan. Operators who need
  exactly-once semantics use the reviewed path, whose plan can only be applied once.
- **2026-09-02 — no `noindex` crawl-issue category.** Microsoft's
  `UrlWithCrawlIssues.CrawlIssues` flags enum has no such member, and nothing in this
  API reports a `noindex` meta tag or an `X-Robots-Tag` header. A category derived from
  anything else would be a guess wearing Bing's authority, so `bing_crawl_issues`
  reports none. The 404/403 split is the opposite case: Bing sends the exact status in
  `HttpCode` on the same row, so `http_404` and `http_403` are read off real data.
- **2026-09-02 — no way to reveal a verification secret over MCP.** `AuthenticationCode`,
  `DnsVerificationCode` and `DelegatedCode` are ownership proofs, so they are redacted in
  every response and the reveal switch exists only as a CLI flag. A tool argument would
  be model-controlled: text a read tool returned could then talk a model into fetching a
  code and writing it into a transcript, a log or a report. The operator who needs one is
  the person publishing the proof on the site, and they are at a terminal.
- **2026-09-02 — a plan keeps its secret on disk and hides it in every view.** An
  `add_site_roles` plan cannot be applied without the `authentication_code` it records,
  so the record is not scrubbed. What changed is that showing a plan is no longer a way
  to read one back: `bing_plan_show`, `bing_plan_list`, `bing-wm plan show|list` and the
  `plan apply` confirmation all render through `Plan.public_dump()`, and only the CLI can
  ask to reveal. The alternative — dropping the code from the record and asking for it
  again at apply time — was rejected: it would put the credential back on the operator's
  command line at the exact moment the plan exists to avoid retyping it, and a plan whose
  arguments are not what will be sent is no longer a review artifact.
- **2026-09-02 — a read's shape is declared, never inferred.** Deciding structurally
  whether a response carried rows cannot work: `GetCrawlSettings` returns one record
  whose `CrawlRate` is an hourly-rate array and `GetLinkCounts` returns a container whose
  `Links` array is the rows, and both look like "a mapping with an empty list in it".
  Each read therefore carries `@row_read` or `@single_record`, and single-record reads
  are exempt from the emptiness test rather than being given cleverer heuristics. Naming
  the row-bearing field of every container read was considered and refused for the
  reads Microsoft's pages do not document: `Links` is verified for `GetLinkCounts`, the
  rest would be invention, and the generic "any list-valued field" test is correct for
  both shapes once single records are out of it.
- **2026-09-02 — the API key stays in the query string.** Moving it to a header would
  end the whole class of URL-quoting leaks at the source rather than covering them at the
  exit. Microsoft's pages do not offer that for a key: every example on
  [Getting started](https://learn.microsoft.com/en-us/bingwebmaster/getting-started) puts
  it in the URL, and the only documented header form,
  `Authorization: Bearer` on
  [the OAuth2 page](https://learn.microsoft.com/en-us/bingwebmaster/oauth2), carries an
  OAuth2 access token obtained through client registration and user consent — a different
  credential, not the key in a different place. Inventing an `apikey:` or
  `Ocp-Apim-Subscription-Key:` header would be guessing at the API. Redaction it is,
  until OAuth2 is implemented; that work would remove the exposure as a side effect,
  because the token would travel in a header.
- **2026-09-02 — successful response bodies are not scanned for the credential.**
  Redaction by literal covers error text, where a URL demonstrably arrives from a proxy
  or from Bing's own message. Bing's success payloads return site data, not a copy of the
  request, so searching every string of every large response for the key would cost a
  second walk on the common path to cover a shape never observed. If a method is ever
  seen echoing the request URL, the place to fix it is `client._decode_success`, which is
  where the credential is known.
- **2026-09-02 — no attempt to resolve an empty response.** Nothing in the API says
  whether an empty answer means "nothing to report" or "not reported", and this server
  does not guess: it labels the response `empty_response` and leaves the ambiguity
  visible. Corroborating by calling other endpoints, or by fetching the site, would
  invent a coverage signal Bing does not provide.
- **2026-09-02 — no derived HTTP status for a URL.** `UrlInfo.HttpStatus` is 0 when Bing
  reports no status; the row is labelled `http_status_reported: false` and the raw 0 is
  kept. Fetching the URL to fill the gap would report this project's own request as if it
  were Bing's observation, on data whose date is `LastCrawledDate`, not today.
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
