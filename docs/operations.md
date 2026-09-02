# Operations

CLI and MCP are thin facades over the same operation and planning modules. CLI commands
accept `--json`; lists render as human-readable tables otherwise.

## CLI

- `bing-wm sites list|show|roles|moves`
- `bing-wm traffic queries|query|query-pages|query-page|pages|page|rank`
- `bing-wm index url|url-traffic|children|children-traffic`
- `bing-wm crawl stats|issues|settings|fetched|fetched-details`
- `bing-wm links counts|url|connected`
- `bing-wm keywords get|stats|related`
- `bing-wm sitemaps list|details`
- `bing-wm quota`, `content-quota`, `blocking`, `query-parameters`, `geo-settings`
- `bing-wm indexnow key HOST [--key KEY] [--key-location URL] [--check/--no-check]`
  generates or inspects an IndexNow key. It sends nothing to Bing or IndexNow and
  stores nothing: a generated key is printed once. `--check` fetches the key file on
  your own host to see whether it is already served, and is on by default with
  `--key` (a key generated here cannot be published yet).

One-step writes, available while `BING_WM_ALLOW_WRITES` is on (the default). They send
the change immediately and print the applied plan:

- `bing-wm submit-url|submit-urls|submit-sitemap|block-url`
- `bing-wm indexnow submit`
- `bing-wm write OPERATION --args-json OBJECT` covers every write below.

The reviewed path stays available in both modes and is the only path when
`BING_WM_ALLOW_WRITES=false`:

- `bing-wm plan submit-url|submit-urls|submit-sitemap|block-url|indexnow`
- `bing-wm plan create OPERATION --args-json OBJECT` covers every write below.
- `bing-wm plan list|show|reject|apply|unlock`; apply and unlock prompt unless `--yes`
  is supplied.

## MCP read tools

- `bing_sites_list`, `bing_site_roles`, `bing_site_moves`
- `bing_traffic_queries`, `bing_traffic_query`, `bing_query_page_stats`,
  `bing_query_page_detail_stats`, `bing_traffic_pages`, `bing_traffic_page`,
  `bing_traffic_rank`
- `bing_url_info`, `bing_url_traffic_info`, `bing_children_url_info`,
  `bing_children_url_traffic_info`
- `bing_crawl_stats`, `bing_crawl_issues`, `bing_crawl_settings`,
  `bing_fetched_urls`, `bing_fetched_url_details`
- `bing_submission_quota`, `bing_content_submission_quota`
- `bing_sitemaps`, `bing_sitemap_details`
- `bing_blocked_urls`, `bing_page_preview_blocks`, `bing_deep_link_blocks`
- `bing_query_parameters`, `bing_geo_settings`
- `bing_link_counts`, `bing_url_links`, `bing_connected_pages`
- `bing_keyword`, `bing_keyword_stats`, `bing_related_keywords`

`bing_crawl_issues` returns `{total, categories, http_codes, issues}`. Each row in
`issues` keeps every field Bing sent and gains a lower-case `categories` list, plus
`unknown_issue_bits` when Bing sets a flag Microsoft has not documented. Categories
come from Microsoft's `UrlWithCrawlIssues.CrawlIssues` flags enum — `redirect_301`,
`redirect_302`, `http_4xx`, `http_5xx`, `blocked_by_robots_txt`, `contains_malware`,
`important_url_blocked_by_robots_txt`, `dns_errors`, `timeout_errors` — plus `none`
for a row with no flags and `other` for anything unrecognised. Microsoft's enum stops
at `Code4xx`, so a row carrying that flag is split by its own `HttpCode` field into
`http_404` or `http_403`; those two are a subset of `http_4xx`, which still counts
every 4xx row, and any other 4xx code is left to `http_codes`. Bing has no `noindex`
crawl-issue flag, so there is no such category. `http_codes` counts the raw
`HttpCode` field on every row.

## MCP local read-only tools

- `bing_indexnow_key_plan` — generate or inspect IndexNow key material for a host:
  the key, the exact key-file URL, the bytes that file must contain, the URL prefix
  the key authorizes, and whether the file is already served. It reaches neither Bing
  nor `api.indexnow.org`, needs no API key, consumes no quota and records no plan, so
  there is nothing to apply. Its only network access is an optional unauthenticated
  GET of the key file on the host given, the same request the submission preflight
  makes; that check is skipped by default for a key the tool just generated. Before
  fetching, the host is resolved and refused if any address is not globally routable,
  and the MCP path ignores proxy environment variables — a syntactically valid name like
  `foo.localhost` or `127.0.0.1.nip.io` must not turn this tool into a way to reach the
  operator's own network. The key is not stored: it exists only in the response.

## MCP write tools

`BING_WM_ALLOW_WRITES` decides which of the two sets below is advertised. Both are
always dispatchable, so a client holding a stale tool list gets the operation's real
answer — a `POLICY_DENIED` for a disabled write — rather than "unknown tool".

## MCP one-step write tools (`BING_WM_ALLOW_WRITES=true`, the default)

Each sends the change to Bing immediately and returns the applied plan ID, the operation
and Bing's result. They are annotated `readOnlyHint: false`, `destructiveHint: true`.

- `bing_add_blocked_url`
- `bing_add_connected_page`
- `bing_add_country_region_settings`
- `bing_add_deep_link_block`
- `bing_add_page_preview_block`
- `bing_add_query_parameter`
- `bing_add_site`
- `bing_add_site_roles`
- `bing_enable_disable_query_parameter`
- `bing_fetch_url`
- `bing_indexnow_submit`
- `bing_remove_blocked_url`
- `bing_remove_country_region_settings`
- `bing_remove_deep_link_block`
- `bing_remove_feed`
- `bing_remove_page_preview_block`
- `bing_remove_query_parameter`
- `bing_remove_site`
- `bing_remove_site_role`
- `bing_save_crawl_settings`
- `bing_submit_content`
- `bing_submit_feed`
- `bing_submit_site_move`
- `bing_submit_url`
- `bing_submit_url_batch`
- `bing_verify_site`

## MCP planning tools (`BING_WM_ALLOW_WRITES=false`)

Each returns a plan ID, summary, expiry, and CLI apply command. No change is sent to
Bing; planning a quota-aware write does read Bing's quota.

- `bing_plan_add_blocked_url`
- `bing_plan_add_connected_page`
- `bing_plan_add_country_region_settings`
- `bing_plan_add_deep_link_block`
- `bing_plan_add_page_preview_block`
- `bing_plan_add_query_parameter`
- `bing_plan_add_site`
- `bing_plan_add_site_roles`
- `bing_plan_enable_disable_query_parameter`
- `bing_plan_fetch_url`
- `bing_plan_indexnow_submit`
- `bing_plan_remove_blocked_url`
- `bing_plan_remove_country_region_settings`
- `bing_plan_remove_deep_link_block`
- `bing_plan_remove_feed`
- `bing_plan_remove_page_preview_block`
- `bing_plan_remove_query_parameter`
- `bing_plan_remove_site`
- `bing_plan_remove_site_role`
- `bing_plan_save_crawl_settings`
- `bing_plan_submit_content`
- `bing_plan_submit_feed`
- `bing_plan_submit_site_move`
- `bing_plan_submit_url`
- `bing_plan_submit_url_batch`
- `bing_plan_verify_site`
- `bing_plan_list`, `bing_plan_show`

There is no `bing_plan_apply` or `bing_plan_reject` tool in either mode, and no MCP tool
accepts a plan ID: a plan recorded for review is applied or refused by a human at the
CLI. A direct write applies the plan it creates in the same call. Enabling one-step
writes replaces the planning tools with direct ones rather than adding a tool that can
confirm a plan somebody else wrote.

A direct write is not idempotent. Retrying one creates a new plan and sends the change
again; the one-shot guarantee is per plan, and there is no client-supplied idempotency
key. Before repeating a call whose response was lost, read `audit.jsonl` or `bing_plan_list`.

## Write operation names

`bing-wm write` and `bing-wm plan create` both accept `add_blocked_url`, `add_connected_page`,
`add_country_region_settings`, `add_deep_link_block`, `add_page_preview_block`,
`add_query_parameter`, `add_site`, `add_site_roles`,
`enable_disable_query_parameter`, `fetch_url`, `indexnow_submit`,
`remove_blocked_url`, `remove_country_region_settings`, `remove_deep_link_block`,
`remove_feed`, `remove_page_preview_block`, `remove_query_parameter`, `remove_site`,
`remove_site_role`, `save_crawl_settings`, `submit_content`, `submit_feed`,
`submit_site_move`, `submit_url`, `submit_url_batch`, and `verify_site`.

Complex values use the exact property names in [the API surface](api-surface.md).
Enum-valued fields use numeric values; invented enum names are not accepted.

`add_site_roles.delegated_url` must be an absolute HTTP(S) URL but is deliberately not
restricted to `site_url`'s host. Microsoft's JSON example delegates `example.com` to
`host1.example.com`, so a cross-host value is part of the documented operation shape.

## State, audit, and recovery

A one-step write is not a second write implementation: it records the same durable plan
and then goes through the same apply boundary, so the denylist, Bing's own submission
quota, the local daily ceiling, one-shot application and the audit trail are identical.
The only thing `BING_WM_ALLOW_WRITES` removes is the human between the two steps.

Plan files are mode `0600` under a mode `0700` directory. Plans expire after 15 minutes
by default and move to terminal `applied`, `rejected`, or `unknown_outcome` states.
Applying acquires an exclusive lock before the request. A process crash after a request
therefore leaves a lock instead of allowing an accidental duplicate.

If recording `applied` or `unknown_outcome` fails after dispatch, the apply process also
keeps its lock. This deliberately converts a local disk failure into the same audited
operator-recovery path as a process crash instead of leaving a retryable `pending` plan.

`bing-wm plan apply` prints the prepared request body before asking for confirmation,
because for the complex-object writes the one-line summary names only the site. A write
whose outcome cannot be known — a lost response, an HTTP 5xx from Bing, or a 2xx whose
body cannot be read — becomes `unknown_outcome` and is never retried automatically. A
plan whose TTL elapses while its request is in flight still records what happened to it.
An IndexNow 5xx is the exception and leaves the plan pending as a retryable failure:
the protocol directs callers to resubmit a valid request after a non-success response.
The CLI does not retry automatically, and repeated submissions can consume crawl quota.

`audit.jsonl` records creation, attempts, failures, denials, unknown outcomes, and
successes without storing the API key or content bodies. `limits.sqlite3` stores
configured local counters transactionally; a plan reserves its cost before the request
and the reservation is released only if the request never reached Bing. For an unknown
outcome, inspect Bing and the audit log; do not create a replacement blindly.

A SIGKILL or power loss can leave `<plan_id>.lock` after its process has died. Run
`bing-wm plan unlock <plan_id>` to recover it. The command refuses a live PID, a
malformed lock, or a plan with no lock. Before removing a dead process's lock it marks
any unfinished plan `unknown_outcome`, so recovery cannot enable an accidental second
write; an already-terminal plan keeps its state. Both the start and completion of the
recovery are appended to `audit.jsonl`.

Site-scoped and IndexNow URL paths reject literal or repeatedly percent-encoded dot
segments before ownership and denylist comparisons. IndexNow key-file preflight does not
follow redirects, accepts only the submitted multi-label DNS host on the default HTTPS port,
and requires the response body to contain exactly the key.
