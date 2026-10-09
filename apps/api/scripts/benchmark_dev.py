# Usage: cd apps/api && python ../../scripts/benchmark_dev.py  (adapt paths if you place it elsewhere)
import json, sys, time
from collections import Counter, defaultdict
sys.path.insert(0, ".")
from app.infrastructure.rule_engine.config import RULES_DIR
from app.infrastructure.rule_engine.stores.policy_store import PolicyStore
from app.infrastructure.rule_engine.core.engine import evaluate_claim

root = "../../data/evaluation/development/"
claims = [json.loads(l) for l in open(root + "claims.jsonl", encoding="utf-8")]
gold = {}
for l in open(root + "expected_results.jsonl", encoding="utf-8"):
    r = json.loads(l); gold[(r["claim_id"], r["rule_id"])] = r
store = PolicyStore.from_dir(RULES_DIR)
pred, lat = {}, []
for c in claims:
    t = time.perf_counter()
    for r in evaluate_claim(c, store):
        pred[(r.claim_id, r.rule_id)] = r.model_dump(mode="json")
    lat.append((time.perf_counter() - t) * 1000)
rules = sorted({k[1] for k in gold}); st = {}
tot = Counter(); conf = Counter(); evbad = Counter(); claim_ok = defaultdict(lambda: True)
for k, g in gold.items():
    p = pred[k]; gs, ps = g["status"], p["status"]
    conf[(k[1], gs, ps)] += 1
    if gs != ps: claim_ok[k[0]] = False
    elif [ (e["path"], e["value"]) for e in g["evidence"]] != [(e["path"], e["value"]) for e in p["evidence"]]:
        evbad[k[1]] += 1
def prf(rs):
    tp = sum(v for (r,g,p),v in conf.items() if r in rs and g=="FAIL" and p=="FAIL")
    fp = sum(v for (r,g,p),v in conf.items() if r in rs and g!="FAIL" and p=="FAIL")
    fn = sum(v for (r,g,p),v in conf.items() if r in rs and g=="FAIL" and p!="FAIL")
    P = tp/(tp+fp) if tp+fp else None; R = tp/(tp+fn) if tp+fn else None
    F = 2*P*R/(P+R) if P and R else (0.0 if P is not None and R is not None else None)
    return tp, fp, fn, P, R, F
f1s = []
for r in rules:
    tp, fp, fn, P, R, F = prf({r}); f1s.append(F if F is not None else 0)
    acc = sum(v for (rr,g,p),v in conf.items() if rr==r and g==p)/400
    print(r, f"TP={tp} FP={fp} FN={fn} P={P} R={R} F1={F} acc={acc:.3f} evidence_mismatch={evbad[r]}")
tp, fp, fn, P, R, F = prf(set(rules))
acc = sum(v for (r,g,p),v in conf.items() if g==p)/len(gold)
print("OVERALL micro P/R/F1", P, R, F, "| macro F1", sum(f1s)/len(f1s), "| status acc", round(acc,4))
print("claim exact match", sum(claim_ok[c["claim_id"]] for c in claims), "/", len(claims))
lat.sort(); print("latency ms p50/p95", round(lat[len(lat)//2],2), round(lat[int(len(lat)*.95)],2))
print("errors:", sorted(((k,v) for k,v in conf.items() if k[1]!=k[2]), key=lambda x:-x[1])[:20])