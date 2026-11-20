# Independent Services Deployment

## Current implementation evidence
- 12 local specialist worker processes launched separately on the connected Windows host.
- Coordinator process runs at localhost port 8787.
- Health API reported 12/12 workers online after restart.
- Task dispatch smoke test completed successfully across CEO, Research and Quality workers.
- Python bytecode compilation passed for coordinator.py and service.py.

## Important boundary
The local implementation is active on the connected desktop only. It is not yet deployed to independent cloud servers. The available host has no Docker executable, so container deployment could not be run here. Docker Compose deployment files are supplied for a suitable host.

The workers currently provide role-scoped task acceptance/dispatch scaffolding; model-backed reasoning is not yet integrated. Do not describe them as autonomous AI agents that complete real work until each adapter has a model/provider connection and task-quality tests.

## Next engineering gates
1. Add authenticated request signing and rate limits.
2. Add persistent queue/result store.
3. Implement provider adapters using approved credentials from a secret manager.
4. Add retries, idempotency, structured traces and per-worker tests.
5. Deploy to 12 isolated containers or services on a cloud host.
6. Verify TLS, monitoring, backups and restart behavior.
7. Keep high-impact external actions approval-gated.
