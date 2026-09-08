<p align="center"><img src="assets/kms-graph-hero-v2.svg" alt="KMS Graph, a portal for exploring connected workplace knowledge" width="100%"></p>

# KMS Graph

English · [한국어](README.ko.md)

KMS Graph is a read-focused internal knowledge portal for searching and exploring documents, work tools, and AI assets. It embeds approved material collected from CSV, Google Sheets, or Notion in a static site. Domain, department, and tags remain searchable metadata rather than graph nodes. Prompt text is accepted and displayed only for AI assets with the `프롬프트` subtype.

## Quick start

Node.js 22.12+ (recommended) and Python 3.10+ are required. If using Node.js 20, use 20.19 or newer. Run from the repository root:

```bash
npm --prefix frontend ci
npm --prefix frontend run build
python build.py --csv-dir sample --out out --no-check-urls
python -m http.server --directory out 8765
```

Open `http://localhost:8765`. Opening `index.html` directly over `file://` can prevent Workers and assets from loading under browser security rules.

For frontend development, run `npm --prefix frontend run dev`. The dev server uses 150 clearly marked sample items only when no embedded data exists. Open `http://localhost:5173/?demo=1000` for a 1,000-item graph stress check; this option has no effect in published builds.

## Using the portal

- Start in the compact library list to compare title, type, domain, owner, connected-item count, and update date. Switch to the graph to pan, zoom, and explore relationships.
- List view uses the same search, type, and business-domain filters. Opening a row keeps the list in place; its graph icon explicitly moves to the selected node.
- Press `/` to focus search and `Esc` to clear it. Selection is stored in the URL hash for browser back/forward navigation and shareable item links.
- `Open original` appears only when a work tool has a safe HTTP(S) address.

## Inputs and builds

Local CSV examples are in `sample/`. For operational input, copy `config.example.json` to the ignored `config.json` and configure read access to Google Sheets or Notion. External collection is not tested without account credentials. Never commit `config.json`, service-account keys, or tokens.

Schema version 2 JSON can add richer knowledge items and explicit relationships:

```bash
python build.py --csv-dir sample --knowledge sample/knowledge.json --out out --no-check-urls
```

The generated HTML contains all published data. Anyone who can read the static files can read that data; this application does not implement per-document authorization. Review the hosting and authentication layer before any external publication.

## Verification

```bash
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
python test_build.py
python test_knowledge.py
```

The current scope is a searchable, read-only portal over collected material. SSO, server persistence, collaborative editing, uploads, registration or permission controls in the UI, AI execution, real-account setup, and external deployment are outside this implementation.

The portal published through Cloudflare is read-only. Add, edit, or remove material in the connected Notion or Google Sheets source; the next static-site build publishes those changes.

## Main files

| Path | Role |
|---|---|
| `frontend/` | React + TypeScript UI and graph Worker |
| `build.py` | Input collection, validation, and static-site build |
| `knowledge.py` | Schema version 2 knowledge processing |
| `sample/` | Local test inputs |
| `out/` | Generated publish output (ignored by Git) |

## License

PolyForm Noncommercial 1.0.0. Free for personal, non-profit, educational, and research use; commercial use is restricted.
