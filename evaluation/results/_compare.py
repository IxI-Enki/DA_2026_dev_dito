import json, pathlib

results_dir = pathlib.Path(__file__).parent
files = sorted(results_dir.glob("model_*.json"))

rows = []
for f in files:
    d = json.loads(f.read_text(encoding="utf-8"))
    exp = d["experiment"]
    m = d["aggregate_metrics"]
    rows.append({
        "name": exp["name"],
        "model": exp["model"],
        "dim": exp["dimensions"],
        "mrr": m["mrr"]["mean"],
        "ndcg": m["ndcg_at_10"]["mean"],
        "p5": m["precision_at_5"]["mean"],
        "r10": m["recall_at_10"]["mean"],
        "map": m["map"]["mean"],
        "hit": m["hit_rate"],
        "chunks": d["performance"]["corpus_chunks"],
    })

rows.sort(key=lambda r: r["mrr"], reverse=True)

header = f"{'Model':<40} {'Dim':>5} {'MRR':>7} {'NDCG@10':>8} {'P@5':>7} {'R@10':>7} {'MAP':>7} {'Hit%':>7}"
print(header)
print("-" * len(header))
for r in rows:
    line = (
        f"{r['name']:<40} {r['dim']:>5}"
        f" {r['mrr']:>7.4f} {r['ndcg']:>8.4f}"
        f" {r['p5']:>7.4f} {r['r10']:>7.4f}"
        f" {r['map']:>7.4f} {r['hit']*100:>6.1f}%"
    )
    print(line)

print(f"\nAll evaluated on 78 Q&A pairs, {rows[0]['chunks']} corpus chunks")
