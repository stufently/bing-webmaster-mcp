# Owner-only launch tasks

The implementation is complete in the checkout. These steps require the repository
owner's external accounts and are intentionally not automated from a developer machine.

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
- [ ] Upload a 1280×640 PNG under Settings → General → Social preview.
- [ ] Publish the server to `registry.modelcontextprotocol.io` with `mcp-publisher`
  after the PyPI release, using the same verified GitHub identity.
- [ ] Submit the released server to the community catalogues listed in the launch plan.

## Open after the write-boundary review (2026-08-25)

- [ ] A stale apply lock has no operator recovery path. `PlanStore.applying` and
  `reject` both take `<plan_id>.lock` and unlink it in `finally`, so it only survives a
  SIGKILL or power loss — but then apply *and* reject both raise `PlanAlreadyApplied`
  forever and nothing but deleting the file by hand clears it. Decide between a
  `bing-wm plan unlock <id>` command that records the release in the audit log and
  simply documenting the manual removal in `docs/operations.md`.
- [ ] Re-run the Antigravity review over `0700dc5..7e5595f`. Its fourth pass failed with
  an OAuth/network timeout and returned nothing, so that range has Codex review only;
  `7e5595f` itself shipped without a review pass.
- [ ] Confirm three deliberate asymmetries, or change them:
  an IndexNow 5xx stays a retryable failure rather than `unknown_outcome` (resubmitting
  the same URLs is a protocol no-op); `delegated_url` is validated as an absolute URL
  but not scoped to the site's host (subdomain delegation is legitimate); the denylist
  matches one host exactly and does not cover subdomains.
- [ ] `RateLimiter.check()` no longer has a caller outside the tests now that
  `apply_plan` reserves with `consume()`. Keep it as a documented preflight or drop it.
