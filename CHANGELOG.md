# Changelog

## Unreleased

- Implement all 59 supported Bing Webmaster Tools API methods.
- Add the CLI and a 62-tool MCP stdio server with no apply capability over MCP.
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
