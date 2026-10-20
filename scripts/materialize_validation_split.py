"""Build data/evaluation/validation/ (50 claims) from the development pack labels.

Selection rule (fixed, reproducible): sort by claim_id, pick 50 evenly spaced indices.
Labels are copied from expected_results.jsonl (not recomputed).

Run from repo root:  python scripts/materialize_validation_split.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "data" / "evaluation" / "development"
OUT = ROOT / "data" / "evaluation" / "validation"
TARGET = 50


def main() -> None:
    claims = [json.loads(l) for l in DEV.joinpath("claims.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    gold = [json.loads(l) for l in DEV.joinpath("expected_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    claims.sort(key=lambda c: c["claim_id"])
    n = len(claims)
    if n < TARGET:
        raise SystemExit(f"need at least {TARGET} development claims, found {n}")
    indices = [i * n // TARGET for i in range(TARGET)]
    selected = [claims[i] for i in indices]
    ids = {c["claim_id"] for c in selected}
    if len(ids) != TARGET:
        raise SystemExit(f"expected {TARGET} validation claim ids, got {len(ids)}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "claims.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in claims if c["claim_id"] in ids) + "\n",
        encoding="utf-8",
    )
    (OUT / "expected_results.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in gold if r["claim_id"] in ids) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "split": "validation",
        "n_claims": len(ids),
        "selection": f"sorted claim_id, {TARGET} evenly spaced indices over n={n}",
        "source": "data/evaluation/development",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(ids)} claims, {sum(1 for r in gold if r['claim_id'] in ids)} labelled pairs)")


if __name__ == "__main__":
    main()
