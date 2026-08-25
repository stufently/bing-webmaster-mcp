# Configuration

Settings come from environment variables. Secrets use `SecretStr` and are never written
to plans or audit entries.

| Variable | Default | Effect |
|---|---|---|
| `BING_WM_API_KEY` | required for Bing calls | API key; not required for IndexNow-only planning |
| `BING_WM_BASE_URL` | `https://ssl.bing.com/webmaster/api.svc/json` | JSON API base |
| `BING_WM_CALLS_PER_SECOND` | `5` | local throttle, not a claimed Bing quota |
| `BING_WM_MAX_ATTEMPTS` | `3` | attempts for retryable safe reads; writes never auto-retry |
| `BING_WM_PLAN_TTL_SECONDS` | `900` | seconds before a plan expires |
| `BING_WM_STATE_DIR` | user state directory | plans, audit log, and local counters |
| `BING_WM_DENIED_SITES` | `[]` | JSON list of sites that may never be mutated |
| `BING_WM_MAX_WRITES_PER_DAY` | unset | optional operator local ceiling |
| `BING_WM_HTTP_HOST` | `127.0.0.1` | literal loopback bind address |
| `BING_WM_HTTP_PORT` | `8765` | optional HTTP port |
| `BING_WM_HTTP_BEARER_TOKEN` | unset | required for HTTP; at least 32 characters |

Denylist matching is case-insensitive and ignores a trailing slash.
