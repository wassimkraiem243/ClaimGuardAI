"""Generate docs/evaluation/EVALUATION_REPORT.md + metrics JSON from the real engine.

Usage (from apps/api):  python scripts/make_eval_report.py
Splits are discovered under data/evaluation/<split>/ (needs claims.jsonl + expected_results.jsonl).
Every number in the report is computed here; nothing is typed by hand.
"""
import json, subprocess, sys, time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, ".")
from app.infrastructure.rule_engine.config import RULES_DIR
from app.infrastructure.rule_engine.core.engine import evaluate_claim
from app.infrastructure.rule_engine.stores.policy_store import PolicyStore
from app.infrastructure.audit_log import digest, ruleset_fingerprint

REPO = Path(__file__).resolve().parents[3]
EVAL = REPO / "data" / "evaluation"
OUT = REPO / "docs" / "evaluation"
STATUSES = ["PASS", "FAIL", "UNABLE_TO_ASSESS", "NOT_APPLICABLE"]


def load(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def prf(tp, fp, fn):
    P = tp / (tp + fp) if tp + fp else None
    R = tp / (tp + fn) if tp + fn else None
    F = None if P is None or R is None else (0.0 if P + R == 0 else 2 * P * R / (P + R))
    return P, R, F


def evaluate_split(name, store):
    claims = load(EVAL / name / "claims.jsonl")
    gold = {(r["claim_id"], r["rule_id"]): r for r in load(EVAL / name / "expected_results.jsonl")}
    pred, lat = {}, []
    for c in claims:
        t = time.perf_counter()
        for r in evaluate_claim(c, store):
            pred[(r.claim_id, r.rule_id)] = r.model_dump(mode="json")
        lat.append((time.perf_counter() - t) * 1000)
    missing = [k for k in gold if k not in pred]
    extra = [k for k in pred if k not in gold]
    rules = sorted({k[1] for k in gold})
    conf, ev_bad, claim_ok = Counter(), Counter(), defaultdict(lambda: True)
    for k, g in gold.items():
        p = pred.get(k)
        ps = p["status"] if p else "MISSING"
        conf[(k[1], g["status"], ps)] += 1
        if g["status"] != ps:
            claim_ok[k[0]] = False
        elif [(e["path"], e["value"]) for e in g["evidence"]] != [(e["path"], e["value"]) for e in p["evidence"]]:
            ev_bad[k[1]] += 1
    def counts(rs):
        tp = sum(v for (r, g, p), v in conf.items() if r in rs and g == "FAIL" and p == "FAIL")
        fp = sum(v for (r, g, p), v in conf.items() if r in rs and g != "FAIL" and p == "FAIL")
        fn = sum(v for (r, g, p), v in conf.items() if r in rs and g == "FAIL" and p != "FAIL")
        neg = sum(v for (r, g, p), v in conf.items() if r in rs and g != "FAIL")
        return tp, fp, fn, neg
    per_rule, f1s = {}, []
    for r in rules:
        tp, fp, fn, neg = counts({r}); P, R, F = prf(tp, fp, fn)
        n = sum(v for (rr, g, p), v in conf.items() if rr == r)
        acc = sum(v for (rr, g, p), v in conf.items() if rr == r and g == p) / n
        per_rule[r] = dict(tp=tp, fp=fp, fn=fn, precision=P, recall=R, f1=F, status_accuracy=acc,
                           false_alarm_rate=fp / neg if neg else None, evidence_mismatch=ev_bad[r])
        f1s.append(0.0 if F is None else F)   # undefined F1 counted as 0 in the macro average (conservative)
    tp, fp, fn, neg = counts(set(rules)); P, R, F = prf(tp, fp, fn)
    lat.sort()
    abst = lambda f: sum(v for (r, g, p), v in conf.items() if f(g, p))
    return dict(
        split=name, n_claims=len(claims), n_pairs=len(gold), missing_pairs=len(missing), extra_pairs=len(extra),
        micro=dict(precision=P, recall=R, f1=F, false_alarm_rate=fp / neg if neg else None),
        macro_f1=sum(f1s) / len(f1s) if f1s else None,
        status_accuracy=abst(lambda g, p: g == p) / len(gold),
        false_abstentions=abst(lambda g, p: p == "UNABLE_TO_ASSESS" and g != "UNABLE_TO_ASSESS"),
        missed_abstentions=abst(lambda g, p: g == "UNABLE_TO_ASSESS" and p != "UNABLE_TO_ASSESS"),
        claim_exact_match=sum(claim_ok[c["claim_id"]] for c in claims),
        latency_ms=dict(p50=lat[len(lat) // 2], p95=lat[int(len(lat) * .95)], max=lat[-1]),
        per_rule=per_rule,
        confusion=sorted(
            ({"expected": g, "predicted": p, "count": sum(c for (_, gg, pp), c in conf.items() if gg == g and pp == p)}
             for g in STATUSES for p in STATUSES + ["MISSING"] if any(gg == g and pp == p for (_, gg, pp) in conf)),
            key=lambda x: (x["expected"], x["predicted"])),
    )


def fmt(x, pct=False):
    if x is None: return "null"
    return f"{x:.3f}" if not pct else f"{x*100:.1f}%"


def md(results, commit, tag, fp_):
    L = [f"# Evaluation report — ClaimGuard AI (Phase 2)", "",
         f"_Generated {date.today().isoformat()} by `apps/api/scripts/make_eval_report.py`. All numbers are computed, not typed._", "",
         "## 1. Reproducibility", "",
         f"- Commit: `{commit}`" + (f" (tag `{tag}`)" if tag else ""),
         f"- Ruleset fingerprint (sha256 of rule files, first 16): `{digest(fp_)[:16]}`",
         "- Command: `cd apps/api && python scripts/make_eval_report.py`",
         "- Rulebook: fictional teaching rulebook v1.0.0 (04_Rulebook); metrics follow 07_Evaluation_and_Acceptance.", ""]
    L += ["## 2. Data discipline (declaration)", "",
          "- Development split: used to build and tune the rule engine. **Perfect scores on it are expected and are not evidence of generalisation.**",
          "- A commit was frozen (tag `phase2-freeze`) before any validation run.",
          "- Validation / stress splits: reported below only if their labelled files were available in `data/evaluation/`. "
          "If validation labels influence any later change, that change must be listed in section 6.",
          "- Held-out inputs/labels were never available to the team.", ""]
    L += ["## 3. Summary", "", "| Split | Claims | Pairs | Macro F1 | Issue P | Issue R | Issue F1 | False-alarm | Status acc. | Claim exact | p50 / p95 ms |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        m = r["micro"]
        L.append(f"| {r['split']} | {r['n_claims']} | {r['n_pairs']} | {fmt(r['macro_f1'])} | {fmt(m['precision'])} | {fmt(m['recall'])} | "
                 f"{fmt(m['f1'])} | {fmt(m['false_alarm_rate'])} | {fmt(r['status_accuracy'])} | {r['claim_exact_match']}/{r['n_claims']} | "
                 f"{r['latency_ms']['p50']:.2f} / {r['latency_ms']['p95']:.2f} |")
    L += ["", "Metric definitions: issue = FAIL status at claim-rule level; undefined precision/recall is `null` (never 100%); "
          "an undefined per-rule F1 counts as 0 in the macro average. False-alarm rate = predicted FAIL among pairs whose expected status is not FAIL.", ""]
    for r in results:
        L += [f"## 4. Split `{r['split']}`", "",
              f"Missing pairs: {r['missing_pairs']} · extra pairs: {r['extra_pairs']} · false abstentions: {r['false_abstentions']} · "
              f"missed abstentions: {r['missed_abstentions']}", "",
              "| Rule | TP | FP | FN | Precision | Recall | F1 | Status acc. | Evidence mismatch |", "|---|---|---|---|---|---|---|---|---|"]
        for k, v in r["per_rule"].items():
            L.append(f"| {k} | {v['tp']} | {v['fp']} | {v['fn']} | {fmt(v['precision'])} | {fmt(v['recall'])} | {fmt(v['f1'])} | "
                     f"{fmt(v['status_accuracy'])} | {v['evidence_mismatch']} |")
        L += ["", "Confusion (expected → predicted):", "", "| Expected | Predicted | Count |", "|---|---|---|"]
        L += [f"| {c['expected']} | {c['predicted']} | {c['count']} |" for c in r["confusion"]]
        L.append("")
    L += ["## 5. Latency", "", "Measured in-process per claim (15 rules), single thread, on the author's machine; "
          "excludes HTTP, database and audit-log I/O. Treat as an order of magnitude.", ""]
    L += ["## 6. Limitations (to keep honest)", "",
          "- Synthetic, rule-based benchmark: high accuracy here says nothing about real payer data or clinical correctness.",
          "- Evidence checks compare JSON pointer + observed value; they do not prove semantic relevance.",
          "- Ambiguous inputs follow the rulebook literally (no trimming, case-sensitive IDs): e.g. a whitespace-only authorization id counts as present (R008); "
          "numeric strings in `quantity` give UNABLE_TO_ASSESS (R013). Real data may need a documented policy for these.",
          "- Deterministic checks carry `confidence=null`; routing to human review is based on status and severity, not on a probability.",
          "- Audit log is a local hash-chained file (tamper-evident, not immutable); anchors must be stored elsewhere.",
          "- LLM-assisted explanations (if used) are evaluated separately; a model failure must never remove a deterministic finding.", ""]
    return "\n".join(L)


def git(*a):
    try:
        return subprocess.check_output(["git", *a], cwd=REPO, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


if __name__ == "__main__":
    store = PolicyStore.from_dir(RULES_DIR)
    splits = [d.name for d in sorted(EVAL.iterdir()) if (d / "claims.jsonl").exists() and (d / "expected_results.jsonl").exists()]
    if not splits:
        sys.exit("No split with claims.jsonl + expected_results.jsonl under data/evaluation/")
    results = [evaluate_split(s, store) for s in splits]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    commit, tag = git("rev-parse", "--short", "HEAD"), git("tag", "--points-at", "HEAD")
    (OUT / "EVALUATION_REPORT.md").write_text(md(results, commit or "unknown", tag, ruleset_fingerprint(str(RULES_DIR))), encoding="utf-8")
    print("Splits:", ", ".join(splits)); print("Wrote", OUT / "EVALUATION_REPORT.md")