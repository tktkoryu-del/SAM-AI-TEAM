# Verified Connector Status

Last checked: 2026-11-21

This is the status of the ChatGPT orchestration-layer connectors, not the local Python worker runtime. A successful connector call here does not mean a local worker has an API credential or can call that connector directly.

| Capability | Live check | Result | Boundary |
|---|---|---|---|
| Exa research | Read-only Exa web search request | Connected and search returned official API documentation | Local workers still need a separately provisioned EXA_API_KEY to call Exa directly |
| Figma design | Figma whoami | Connected; current team seat is View | Do not assume write/design-edit permission from a View seat |
| Metricool publishing/analytics | Read-only brand settings | Connected; brand "مغامرات SAM" returned with Facebook, TikTok, YouTube and other network metadata | Do not publish or schedule without explicit user approval; local workers do not inherit the ChatGPT connector session |
| Canva design | Connector actions are available in the ChatGPT tool layer | Not independently account-verified in this check | Account/link selection and write permission must be confirmed before a design write |

## Runtime integration status

The 12 Python workers still share the local Ollama model. They do not have direct access to ChatGPT's authenticated connector sessions. No external API keys, OAuth refresh tokens, or platform credentials are stored in the repository.

## Safe integration path

1. Use ChatGPT's authenticated connectors for research, design, and platform work during an orchestrated session.
2. For local-worker access, implement a separately authenticated adapter per provider using the provider's official API and least-privilege scopes.
3. Keep credentials in a secret manager or environment variables, never in source control or task JSON.
4. Keep publishing, scheduling, spending, sending, deletion, and permission changes behind explicit approval.
5. Verify each adapter with a read-only identity/health call before enabling write operations.

## References

- Exa Search API: https://exa.ai/docs/reference/search
- Figma REST API authentication: https://developers.figma.com/docs/rest-api/authentication/
- Canva REST API reference: https://www.canva.dev/docs/apps/rest-apis/reference/
- Metricool API access: https://help.metricool.com/basic-guide-for-api-integration-r97af
