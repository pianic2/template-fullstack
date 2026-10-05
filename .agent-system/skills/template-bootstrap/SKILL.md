---
name: template-bootstrap
description: Initialize a clone into a new product without changing dependency ownership or unrelated source.
---

# Template bootstrap

- **Trigger:** A clone is renamed or initialization behavior changes.
- **Inputs:** Product name, slug, Python identifier, bundle ID, optional ports/features.
- **Steps:** Use `make init` or `scripts/bootstrap.py`; preview scoped replacement files; preserve the external component-library dependency; refuse unsafe repeated runs; write a local initialization marker.
- **Validation:** Unit tests and `scripts/bootstrap-smoke.sh` on a disposable copy; verify JSON/TOML and lockfile consistency.
- **Expected output:** Safe initialized settings plus exact test evidence and next setup commands.
