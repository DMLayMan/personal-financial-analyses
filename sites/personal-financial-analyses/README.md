# Personal Financial Analyses · private hosted edition

Three connected research workspaces: methods/knowledge/review; market and source coverage; sector/company evidence reports. Owner-private Sites access. Python Decimal/SQLite/PDF kernel runs in a browser Web Worker through pinned Pyodide; D1 maintains atomic version heads and R2 keeps content-addressed originals plus immutable SQLite snapshots. No external model service is configured.

`kernel/` mirrors source-only inputs from the parent research repository using `scripts/sync-hosted.py`. `kernel-manifest.json` verifies this mirror. No database, original document, credential, account or holding is in Git. Initial user data is imported separately after publication; `/cloud/admin/` is a service import API behind the confirmed owner-private Sites boundary. Do not change the Site audience without revisiting that authorization model.

- Install dependencies with the Sites installer after changing package inputs.
- `npm test`: source, paths, stream limits and same-origin controls.
- `npm run build`: verify source digests, prepare fixed self-hosted runtime assets, then build the supplied Vinext worker.
- `npm run dev -- --port 5173 --hostname 127.0.0.1`: local QA. Local-only mock sign-in is provided by the Sites starter.
- Schema changes: append Drizzle migrations; no runtime DDL or data-seeding migrations.
- Publish using the Sites source helper and native private-deployment operation. Persist the exact returned ID in `.openai/hosting.json`.

Before accepting a release, run the research repository's quality gate, the browser runtime controls, six-company/report/source checks, and a disposable local two-writer persistence test. Never equate those engineering checks with underwritten forecasts, fair value, independent opposition or investment performance.

Constraints: manual refresh while a page is open; no background monitoring; first evidence load approximately 59 MB plus the Python runtime; SQLite snapshots limited to16 MB; no implicit ongoing synchronization with the local workspace. Conflict or unconfirmed cloud save pauses mutations and permits database recovery export. Read `kernel/docs/operations/hosted-service.md` and `kernel/docs/quality/review-2026-10-25.md` for the current permitted use and unresolved priorities.
