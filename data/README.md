# Data directory

Store **synthetic** challenge data here only. See [docs/FOLDER_STRUCTURE.md](../docs/FOLDER_STRUCTURE.md) for the full map.

| Subfolder | Use |
|-----------|-----|
| `synthetic-claims/fhir/` | FHIR R4 JSON bundles per claim |
| `synthetic-claims/csv/` | CSV claim exports if provided |
| `payer-rules/` | Fictional payer rule catalogue (10–15 rules) |
| `evaluation/benchmark/` | 50-claim set + ground truth for metrics |
| `attachments/samples/` | Synthetic PDFs for optional OCR/RAG |

Add a short `SOURCES.md` in each dataset folder noting who generated the files and when.
