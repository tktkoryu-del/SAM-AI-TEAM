# External Integration Boundary

The 12 local workers currently call the shared Ollama/OpenAI model endpoint. They do not possess authenticated access to third-party SaaS connectors.

## Available from the ChatGPT orchestration layer
When a task needs external capabilities, the ChatGPT session can use connected tools such as GitHub, Exa, Canva, Figma, video-generation providers, Metricool, and other available connectors. Each connector must be checked for account connection and permissions at the time of use.

## Not connected inside the local workers
The local Python runtime cannot call those ChatGPT connector tools directly. The following are therefore not to be marked connected until a separately authenticated adapter and a live health test exist:
- Research/search: Exa or other search API
- Design: Canva and Figma APIs
- Video: HeyGen, Higgsfield, or fal APIs
- Social publishing/analytics: Metricool or platform APIs

## Required adapter contract
Each integration adapter must provide:
1. Explicit connection status and a safe health check
2. Least-privilege OAuth/API credentials from environment or a secret store
3. Dry-run mode and idempotency keys
4. Audit logs with request IDs and redacted payloads
5. Approval enforcement before publish, send, spend, delete, or permission changes

Do not put OAuth tokens or API keys in source control or task JSON files.
