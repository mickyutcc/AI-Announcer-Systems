import csv
import json
import statistics
import sys


def read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def _get_field(row, *names):
    for name in names:
        if name in row and row[name] != "":
            return row[name]
    return ""


def analyze(rows):
    per_item = {}
    overall_a = []
    overall_b = []
    for r in rows:
        sid = _get_field(r, "sentence_id", "sentence id", "Sentence ID")
        if not sid:
            continue
        try:
            mos_a = float(_get_field(r, "mos_A", "MOS A"))
            mos_b = float(_get_field(r, "mos_B", "MOS B"))
        except Exception:
            continue
        pref = (_get_field(r, "preference", "Preference") or "").strip()
        per_item.setdefault(sid, {"A": [], "B": [], "pref": {"A": 0, "B": 0, "N": 0}})
        per_item[sid]["A"].append(mos_a)
        per_item[sid]["B"].append(mos_b)
        if pref.upper() == "A":
            per_item[sid]["pref"]["A"] += 1
        elif pref.upper() == "B":
            per_item[sid]["pref"]["B"] += 1
        else:
            per_item[sid]["pref"]["N"] += 1
        overall_a.append(mos_a)
        overall_b.append(mos_b)
    results = {}
    for sid, v in per_item.items():
        results[sid] = {
            "A_mean": statistics.mean(v["A"]) if v["A"] else None,
            "A_median": statistics.median(v["A"]) if v["A"] else None,
            "B_mean": statistics.mean(v["B"]) if v["B"] else None,
            "B_median": statistics.median(v["B"]) if v["B"] else None,
            "pref_A": v["pref"]["A"],
            "pref_B": v["pref"]["B"],
            "pref_N": v["pref"]["N"],
            "n": len(v["A"]),
        }
    overall = {
        "overall_A_mean": statistics.mean(overall_a) if overall_a else None,
        "overall_B_mean": statistics.mean(overall_b) if overall_b else None,
        "n_responses": len(rows),
    }
    return results, overall


def print_report(results, overall):
    print("MOS Analysis Report")
    print("===================")
    print(f"Responses: {overall['n_responses']}")
    if overall["overall_A_mean"] is not None and overall["overall_B_mean"] is not None:
        print(
            f"Overall A mean: {overall['overall_A_mean']:.3f}, Overall B mean: {overall['overall_B_mean']:.3f}"
        )
    print()

    def _sort_key(x):
        return int(x) if str(x).isdigit() else str(x)

    for sid, r in sorted(results.items(), key=lambda x: _sort_key(x[0])):
        print(f"Sentence {sid}: n={r['n']}")
        if r["A_mean"] is not None and r["A_median"] is not None:
            print(f"  A mean={r['A_mean']:.3f}, median={r['A_median']:.3f}")
        if r["B_mean"] is not None and r["B_median"] is not None:
            print(f"  B mean={r['B_mean']:.3f}, median={r['B_median']:.3f}")
        print(f"  Pref: A={r['pref_A']} B={r['pref_B']} None={r['pref_N']}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: mos_analyze.py responses.csv")
        sys.exit(1)
    rows = read_csv(sys.argv[1])
    results, overall = analyze(rows)
    print_report(results, overall)
    with open("mos_report.json", "w", encoding="utf-8") as f:
        json.dump(
            {"results": results, "overall": overall}, f, ensure_ascii=False, indent=2
        )
    print("Saved mos_report.json")
