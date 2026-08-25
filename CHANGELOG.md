# Changelog

## Unreleased

- Implement all 59 supported Bing Webmaster Tools API methods.
- Add the CLI and a 62-tool MCP stdio server with no apply capability over MCP.
- Put all Bing mutations and IndexNow submission behind durable, expiring plans.
- Add auditing, unknown-outcome protection, site policy, and local limits.
- Add protocol-correct IndexNow key verification and batch validation.
- Add an optional bearer-gated, loopback-only Streamable HTTP transport.
- Sanitize and label attacker-influenced response fields.
