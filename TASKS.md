# Owner-only launch tasks

The implementation is complete in the checkout. These steps require the repository
owner's external accounts and are intentionally not automated from a developer machine.

## In progress

- [ ] 2026-08-30 — `BING_WM_ALLOW_WRITES` write-path switch: code, tests and docs are
  done and green. Remaining: rebuild the local `bing-webmaster-mcp:local` image so the
  Claude and Codex MCP entries pick the change up.

## Open follow-up

- [ ] Idempotency key for one-step writes. Raised in the 2026-08-30 Codex review: with
  `BING_WM_ALLOW_WRITES=true`, a retry after a lost response records a new plan and
  sends the write again, because the one-shot guarantee is per plan. A client-supplied
  key with a durable mapping to a plan and its result would close it. Deliberately
  deferred and recorded in `docs/product-boundaries.md`.

## First PyPI release

- [ ] On PyPI, register a pending Trusted Publisher for project
  `bing-webmaster-mcp`: owner `stufently`, repository `bing-webmaster-mcp`, workflow
  `release.yml`, environment `pypi`.
- [ ] In GitHub, create the protected deployment environment `pypi`.
- [ ] Confirm the version in `pyproject.toml`, commit it, and push the matching `v*`
  tag. The release workflow rejects a mismatched tag.
- [ ] From a clean machine, run
  `docker run --rm python:3.14-slim sh -c "pip install bing-webmaster-mcp && bing-wm --help"`.

## Repository and discovery

- [ ] Set the GitHub description to the exact pitch used in README, `pyproject.toml`,
  and `llms.txt`.
- [ ] Review the GitHub topics listed in the implementation plan.
- [ ] Upload the prepared `docs/assets/social-preview.png` under Settings → General →
  Social preview.
- [ ] Publish the server to `registry.modelcontextprotocol.io` with `mcp-publisher`
  after the PyPI release, using the same verified GitHub identity.
- [ ] Submit the released server to the community catalogues listed in the launch plan.

## Tool-dependent follow-up

- [ ] Re-run the Antigravity review over `0700dc5..7e5595f` when that reviewer is
  available. The 2026-08-25 Codex re-review found and fixed scheme-specific default-port
  validation; Antigravity is not available in the current environment.
