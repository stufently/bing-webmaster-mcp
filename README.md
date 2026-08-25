# bing-webmaster-mcp

bing-webmaster-mcp gives an AI agent read access to what Bing knows about your sites — traffic, indexing, crawl issues, inbound links, keywords — and a reviewed, two-step path for the operations that change something.

It ships a Python 3.12+ CLI and MCP server for the JSON Bing Webmaster Tools API,
plus protocol-correct IndexNow submission. SOAP and POX are deliberately absent.

## Why the write path has two steps

Read tools execute immediately. Every operation that changes Bing state creates a
durable plan first:

```console
$ bing-wm plan submit-url example.com https://example.com/new-page --json
{
  "plan_id": "…",
  "summary": "submit url https://example.com/new-page for https://example.com",
  "apply_with": "bing-wm plan apply …"
}
$ bing-wm plan apply PLAN_ID
Apply this plan? [y/N]: y
```

There is deliberately no apply tool over MCP: a confirmation an agent can send is a
confirmation prompt injection can send. An MCP client that also has shell access can
still invoke the CLI; the compensating controls are a readable plan, an append-only
audit trail, one-shot application, expiry, a site denylist, and restart-persistent
local limits.

## Install

```console
python -m pip install bing-webmaster-mcp
```

The supported matrix is Python 3.12, 3.13, and 3.14. Development and images use the
exact versions in `constraints.txt`; published dependencies remain compatible floors.

Create an API key in Bing Webmaster Tools under Settings → API Access and provide it
through the environment:

```console
export BING_WM_API_KEY='…'
bing-wm sites list
```

Never put a real key in the repository. See [configuration](docs/configuration.md) for
all settings.

## MCP client configuration

Run the stdio server with `bing-webmaster-mcp`. Point an MCP client at that executable
and pass `BING_WM_API_KEY` through its protected environment configuration. The server
exposes 34 read tools, a planning tool for every supported write, and plan inspection.
It exposes no plan application or rejection tool.

An optional Streamable HTTP entry point is also available:

```console
export BING_WM_HTTP_BEARER_TOKEN='a-random-token-of-at-least-32-characters'
bing-webmaster-mcp-http
```

It refuses non-loopback bind addresses and unauthenticated requests.

## Common questions

### How do I check if Bing has indexed my page?

```console
bing-wm index url example.com https://example.com/page
```

### How do I submit URLs to Bing from the command line?

Create a plan from one URL or a newline-delimited file, review it, then apply it:

```console
bing-wm plan submit-url example.com https://example.com/page
bing-wm plan submit-urls example.com --file PATH
bing-wm plan show PLAN_ID
bing-wm plan apply PLAN_ID
```

The planner calls `GetUrlSubmissionQuota`; no quota number is hardcoded. Bing's method
documentation also limits one `SubmitUrlBatch` call to 500 URLs.

### Does IndexNow work with Google?

Google does not participate in IndexNow. The live IndexNow registry currently lists
Bing, Yandex, Seznam, Naver, Yep, Internet Archive, and Amazonbot. Submission through
`api.indexnow.org` fans out to participating engines.

Generate a key, host the displayed UTF-8 key file, then plan a submission:

```console
bing-wm indexnow key example.com
bing-wm plan indexnow example.com --file PATH --key KEY
bing-wm plan apply PLAN_ID
```

The apply step checks that the key file is reachable and contains the key before it
sends the batch. Batches above 10,000 URLs and URLs outside the authorized host or key
subpath are rejected locally. There is intentionally no unverified 2,048-character URL
cap.

## Output safety

Anchor text, crawl-issue URLs, titles, messages, and query strings may be controlled by
strangers. The shared operation layer removes control and bidirectional-formatting
characters, truncates extreme values, and returns these fields as
`{"value": "…", "untrusted": true}`. Consumers must treat them as data, never as
instructions.

## Coverage and references

- [CLI commands, MCP tools, and write operations](docs/operations.md)
- [Complete 62-method Microsoft interface transcription](docs/api-surface.md)
- [Product boundaries](docs/product-boundaries.md)
- [Configuration](docs/configuration.md)

The Microsoft interface contains 62 methods: 59 supported here and three obsolete
deep-link methods deliberately excluded. Keyword research is standalone because its
official signatures contain no site parameter. Content submission is exposed because
it remains present in Microsoft's current interface; account-side eligibility can only
be confirmed by Bing for a particular account.

## Licence

MIT.
