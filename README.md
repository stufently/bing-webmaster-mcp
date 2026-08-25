# bing-webmaster-mcp

An MCP server and CLI over the Bing Webmaster Tools API: what Bing knows about
your sites — traffic, indexing, crawl issues, inbound links, keywords — plus
first-class IndexNow submission, with a reviewed two-step path for every
operation that changes something.

Bing is the retrieval layer behind ChatGPT search and Copilot, so Bing Webmaster
Tools is where the ground truth about AI-search visibility lives. The API is free.

> **Status: design.** Nothing is implemented yet. The contract for the first
> implementation is [`SPEC.md`](SPEC.md); the task-by-task build order is
> [`docs/superpowers/plans/2026-08-25-bing-webmaster-mcp.md`](docs/superpowers/plans/2026-08-25-bing-webmaster-mcp.md);
> conventions for whoever writes it are in [`AGENTS.md`](AGENTS.md).

## What makes it different

- **Every write goes through plan-and-apply.** A `plan_*` tool records intent and
  returns a summary; applying it is a CLI command. There is deliberately no apply
  tool over MCP — a confirmation an agent can send is a confirmation prompt
  injection can send.
- **IndexNow done properly** — batch, key-file verification, fan-out to all seven
  participating engines. Google is not one of them, and never adopted it.
- **Complete Bing coverage in a focused server**, not Bing as an afterthought in a
  Google-first tool.

## Not in scope

The classic Bing Search API was retired by Microsoft (announced 2025-08-11,
instances deactivated through 2026-08). This project does not talk to it or to its
paid Azure replacement, and does not scrape search results. It is about Webmaster
Tools — your own verified sites.

## Licence

MIT.
