# Changelog

## Unreleased

- Redact the verification secrets Bing returns beside a site. `GetUserSites` sends
  `AuthenticationCode` and `DnsVerificationCode` and `GetSiteRoles` sends
  `DelegatedCode`; these are ownership proofs, and listing 74 sites was putting 148 of
  them into a caller's transcript, logs and reports for a read that does not need one.
  They now come back as `[redacted: verification secret]` from every read, in the MCP
  server and the CLI alike, because the redaction sits in the shared fetch helper rather
  than in the two operations known to carry a code today. A field Bing left `null` stays
  `null`. The only way to see one is `bing-wm sites list|show|roles
  --reveal-verification-codes`: no MCP tool takes that argument and unknown tool
  arguments are refused, so no model, and no text a model read, can ask for a code.
- Label a read that returned nothing, so silence cannot be reported as a clean bill of
  health. Several older endpoints answer some accounts empty while another endpoint
  reports plenty for the same site: `bing_link_counts`, `bing_crawl_issues` and
  `bing_fetched_urls` all came back empty for a site whose `bing_crawl_stats` reported
  `InLinks: 1700` and `CrawlErrors: 4` in the same minute. Such a result now carries
  `empty_response: {rows_returned: 0, measured: false, note: …}` beside `result` over
  MCP, and the same note on stderr at the CLI. `result` keeps the shape Bing's response
  had. A single record such as `bing_url_info` or a quota is never called empty: a zero
  in it is a reading, not a silence.
- Say when Bing reports no HTTP status for a URL. `GetUrlInfo` returns `HttpStatus: 0`
  with `IsPage: true` for URLs that answer 404 today, which reads as a healthy page.
  `bing_url_info` and `bing_children_url_info` now add `http_status_reported` to every
  row, with an `http_status_note` when it is false, and keep the raw `HttpStatus`.

- Split a crawl issue Bing flagged `Code4xx` into `http_404` or `http_403` using the
  `HttpCode` on the same row, beside the broad `http_4xx` rather than instead of it, so
  a caller counting 4xx rows keeps counting all of them. Microsoft's flags enum has no
  404 or 403 member, so this comes from the status code Bing itself reported and from
  nothing else: without the `Code4xx` flag, or with any other 4xx code, no refinement is
  added. Bing still reports no `noindex` anywhere in this API, and no category invents
  one.

- Add `SKILL.md`: the task recipes an agent needs to drive this server — onboarding a
  new site, a recurring crawl and traffic audit, when IndexNow replaces `submit_url` —
  together with the rules it must not work around.
- Categorise `bing_crawl_issues` / `bing-wm crawl issues` by Microsoft's
  `UrlWithCrawlIssues.CrawlIssues` flags, with a count per category and per raw
  `HttpCode`. Every field Bing returned is kept; an undocumented flag lands in `other`
  and reports its bits rather than disappearing. The read now returns
  `{total, categories, http_codes, issues}` instead of a bare list.
- Add `bing_indexnow_key_plan` and options on `bing-wm indexnow key`, so generating an
  IndexNow key, working out where its key file belongs and checking whether it is
  already served is available to an agent and not only at the CLI. It sends nothing to
  Bing or IndexNow, needs no API key and records no plan, so it is not a write.
- Refuse an IndexNow key-file check whose host resolves to a non-public address, and
  ignore proxy environment variables on the MCP path. `foo.localhost` and
  `127.0.0.1.nip.io` are well-formed multi-label names, and the check is the one request
  an MCP client can make the server send to a host it named.
- Let a tool declare `openWorldHint` itself, so `bing_indexnow_key_plan` can admit that
  it reaches an arbitrary host while the Bing reads stay closed-world.
- Record `UrlWithCrawlIssues`, `UrlInfo`, `QueryStats` and `RankAndTrafficStats` in
  `docs/api-surface.md` with their Microsoft sources. Bing returns no CTR field and no
  robots-directive or content-changed property; the docs now say so.
- Add `BING_WM_ALLOW_WRITES` (default `true`) to choose the write path. With it on,
  the MCP server advertises one-step `bing_<operation>` tools and the CLI gains
  `bing-wm write`, `submit-url`, `submit-urls`, `submit-sitemap`, `block-url` and
  `indexnow submit`, all of which reach Bing on the first call. Setting it to
  `false` restores the previous behaviour: only `bing_plan_<operation>` tools, and
  a human applies the plan with `bing-wm plan apply`. A one-step write still
  records a plan and goes through the same apply boundary, so the denylist, Bing's
  quota check, the local daily ceiling, one-shot application and the audit trail
  are unchanged. No MCP tool accepts a plan ID in either mode, so none can apply or
  reject a plan recorded for review.
- Refuse a one-step write's plan when the write itself fails, so a plan nobody reviewed
  cannot be applied by hand later, and name the plan in the error so an unknown outcome
  can be traced.
- Report `POLICY_DENIED` rather than `AUTH_FAILED` for a write attempted while
  `BING_WM_ALLOW_WRITES=false` and no API key is set.
- Implement all 59 supported Bing Webmaster Tools API methods.
- Add the CLI and the MCP stdio server with no apply capability over MCP.
- Put all Bing mutations and IndexNow submission behind durable, expiring plans.
- Add auditing, unknown-outcome protection, site policy, and local limits.
- Add protocol-correct IndexNow key verification and batch validation.
- Add an optional bearer-gated, loopback-only Streamable HTTP transport.
- Sanitize and label attacker-influenced response fields.
- Record a plan's outcome even when its TTL elapses while the request is in flight.
- Treat an HTTP 5xx on a mutating request as an unknown outcome instead of a
  retryable failure, so a retry cannot duplicate a write Bing may have processed.
- Match `BING_WM_DENIED_SITES` on the parsed host and re-check it when a plan is
  applied, not only when it is created.
- Show the prepared request body in the `plan apply` confirmation prompt.
- Validate URL ownership inside country-region and site-move payloads.
- Parse the scheme before validating a site URL, and reject hostnames that are not
  hostnames in IndexNow instead of raising a bare `ValueError`.
- Report a non-JSON list variable as `INVALID_REQUEST` rather than a traceback.
- Enforce argument types in the MCP server instead of trusting the client's schema.
- Close SQLite connections in the local write limiter, and reserve the local daily
  ceiling before a write instead of counting it afterwards, releasing the reservation
  only when the request provably never reached Bing.
- Treat a 2xx a mutating call cannot decode as an unknown outcome rather than a
  failure that would leave the plan pending.
- Keep `plan reject` on the expiry check and refuse it while an apply holds the lock.
- Parse host and port through one guarded splitter, so a bad port or bracket is an
  `INVALID_REQUEST` everywhere including IndexNow key locations and URL batches.
- Strip bidi and other format characters from the apply confirmation prompt, and
  show every element of a batch rather than a truncated head.
- Bind a released reservation to the day it was taken on, so a request spanning a UTC
  midnight cannot raise the new day's ceiling.
- Report an out-of-range tick date as a malformed response, and treat any failure to
  read a write's response as an unknown outcome.
- Refuse a denylist entry that names no host, and detect the scheme by parsing so an
  entry like `a.example/shop//eu` still matches.
- Record a cancelled write as an unknown outcome instead of leaving the plan pending.
- Compare host and non-default port, not only the hostname, when checking that a URL
  belongs to the site, and keep the brackets on an IPv6 authority. The scheme stays out
  of it: a legacy `http://` property still submits its live `https://` URLs.
- Keep the IndexNow key-file check out of the unknown-outcome zone, and release the
  reservation if the audit write itself fails.
- Reject a tick date whose timezone minutes are 60 or more.
- Recover locks left by dead apply processes through an audited `bing-wm plan unlock`
  command, marking unfinished plans as unknown instead of making them retryable.
- Compare explicit ports against the default for their own scheme when validating that
  a submitted URL belongs to a site.
- Make the repository test command import the local package in a clean checkout.
- Keep IndexNow 5xx plans retryable because the protocol directs callers to resubmit a
  valid request after a non-success response; no retry is automatic.
- Preserve the apply lock if a terminal plan outcome cannot be written after dispatch,
  and make plan and audit writes resilient to partial operating-system writes.
- Reject invalid hostnames and ambiguous literal or repeatedly encoded dot segments
  before site ownership, denylist, and IndexNow subpath checks.
- Require an exact, bounded IndexNow key-file response without redirects, IP literals,
  single-label hosts, alternate ports, query strings, or fragments.
- Enforce Microsoft's 10 MB uncompressed `SubmitContent` limit across the combined
  decoded content fields rather than independently for each field.
- Return `INVALID_REQUEST` for an unknown MCP tool and run lint, tests, and the MCP smoke
  handshake before Trusted Publishing can upload a tagged release.
