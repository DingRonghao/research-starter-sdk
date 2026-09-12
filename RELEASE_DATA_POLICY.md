# Release data boundary

The Git-managed beta contains application code, dependency manifests, documentation, the `Inbox`/`Output` product structure, and one release-safe sample for each main feature.

The following remain local and are intentionally excluded from Git:

- `config.local.json`: machine-specific paths only. It points at, but does not contain, Codex account state.
- `.runtime/`: task history, uploads, generated outputs, local Obsidian Vault data, logs, caches, audits, and backups.
- `.venv/` and `node_modules/`: reproducible project dependencies.
- Any Inbox/Output project other than the explicitly allow-listed `public-sample` directories.

Codex authentication and user state live in the external directory selected by `codex_home`. Git stores neither that directory nor copied credentials. A new host creates its own `config.local.json` from `config.example.json` on first launch.

The bundled samples contain only synthetic project-authored content. Existing personal tests and the redistribution-rights-uncertain paper/industry materials were not copied into the repository.
