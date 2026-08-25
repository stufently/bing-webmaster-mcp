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
- `bing-wm indexnow key`
- `bing-wm plan submit-url|submit-urls|submit-sitemap|block-url|indexnow`
- `bing-wm plan create OPERATION --args-json OBJECT` covers every write below.
- `bing-wm plan list|show|reject|apply`; apply prompts unless `--yes` is supplied.

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

## MCP planning tools

Each sends nothing and returns a plan ID, summary, expiry, and CLI apply command.

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

There is no `bing_plan_apply` or `bing_plan_reject` tool.

## Write operation names

The generic planner accepts `add_blocked_url`, `add_connected_page`,
`add_country_region_settings`, `add_deep_link_block`, `add_page_preview_block`,
`add_query_parameter`, `add_site`, `add_site_roles`,
`enable_disable_query_parameter`, `fetch_url`, `indexnow_submit`,
`remove_blocked_url`, `remove_country_region_settings`, `remove_deep_link_block`,
`remove_feed`, `remove_page_preview_block`, `remove_query_parameter`, `remove_site`,
`remove_site_role`, `save_crawl_settings`, `submit_content`, `submit_feed`,
`submit_site_move`, `submit_url`, `submit_url_batch`, and `verify_site`.

Complex values use the exact property names in [the API surface](api-surface.md).
Enum-valued fields use numeric values; invented enum names are not accepted.

## State, audit, and recovery

Plan files are mode `0600` under a mode `0700` directory. Plans expire after 15 minutes
by default and move to terminal `applied`, `rejected`, or `unknown_outcome` states.
Applying acquires an exclusive lock before the request. A process crash after a request
therefore leaves a lock instead of allowing an accidental duplicate.

`bing-wm plan apply` prints the prepared request body before asking for confirmation,
because for the complex-object writes the one-line summary names only the site. A write
whose outcome cannot be known — a lost response, an HTTP 5xx from Bing, or a 2xx whose
body cannot be read — becomes `unknown_outcome` and is never retried automatically. A
plan whose TTL elapses while its request is in flight still records what happened to it.
An IndexNow 5xx is the exception and stays a plain retryable failure: resubmitting the
same URLs is a protocol-level no-op.

`audit.jsonl` records creation, attempts, failures, denials, unknown outcomes, and
successes without storing the API key or content bodies. `limits.sqlite3` stores
configured local counters transactionally; a plan reserves its cost before the request
and the reservation is released only if the request never reached Bing. For an unknown
outcome, inspect Bing and the audit log; do not create a replacement blindly.
