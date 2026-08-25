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
