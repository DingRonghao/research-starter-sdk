# Release data boundary

The Git-managed beta contains application code, dependency manifests, documentation, the `Inbox`/`Output` product structure, and one release-safe sample for each main feature.

The following remain local and are intentionally excluded from Git:

- `config.local.json`: machine-specific paths only. It points at, but does not contain, Codex account state.
- `.runtime/`: task history, uploads, generated outputs, local Obsidian Vault data, logs, caches, audits, and backups.
- `.venv/`, `runtime/`, and `node_modules/`: generated or bundled project dependencies. They stay out of Git history; `runtime/` and `node_modules/` are added only to the complete GitHub Release ZIP.
- Any Inbox/Output project other than the explicitly allow-listed `public-sample` directories.

Codex authentication and user state live in the external directory selected by `codex_home`. Git and the complete release ZIP store neither that directory nor copied credentials. A new host can start from `config.example.json` without editing it; the web Settings page creates its own `config.local.json` when saved.

The bundled samples contain only synthetic project-authored content. Existing personal tests and the redistribution-rights-uncertain paper/industry materials were not copied into the repository.
