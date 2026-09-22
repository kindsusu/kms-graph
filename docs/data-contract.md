# KMS schema v2 data contract

The embedded payload has `schemaVersion: 2`, `title`, `generatedAt`, `items`, and `relations`.
An item has a unique `id`, `title`, `kind` (`document`, `tool`, or `ai_asset`) and metadata fields. `domain`, department, and tags are metadata, never generated nodes. URLs must be HTTP(S), contain no user information, and are validated before publication.

Only an `ai_asset` whose subtype is exactly `프롬프트` may have a `prompt` field. Legacy CSV prompt columns are intentionally excluded; they never create standalone assets. Use `--knowledge` or `knowledge_file` to register an explicit prompt asset.

Relations have unique IDs, existing distinct endpoint `source` and `target` IDs, and a `type` from `references`, `based_on`, `explains`, `uses_with`, or `related`. Legacy tools create `references` edges to their approved referenced documents. These are the only supported relationship input fields: `id`, `source`, `target`, `type`, and optional-string `label`. There is no separate live Notion or Google Sheets relationship schema in this repository.

Relation direction is `source → target`: a tool `references` a document, an item `based_on` its source material, and an explanatory manual `explains` the rule it describes. Those three types are directed, so a reverse record is a distinct relationship and is accepted. `uses_with` and `related` are symmetric: the UI renders them as undirected context and the validator rejects a reverse duplicate (`A → B` plus `B → A`) of the same type. Use one record per pair, with either endpoint order.

Explicit `ID`/`id` values take precedence. Without one, legacy tools derive a stable ID from their normalized URL and documents from their name. Renaming a legacy document therefore changes its ID; set an explicit ID before renaming to preserve identity.

Only documents referenced by approved legacy tools are published. Internal reports, unmatched values, and snapshots are stored outside the output directory in `state_dir` (or a sibling hidden state directory).

`report.json` records source-master counts separately from `public_counts`; the former must not be read as the number of published nodes.
