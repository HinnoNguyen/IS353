"""Tổng hợp các lượt chạy thành gói kết quả giữa kỳ ở results/midterm/.

Chạy:  python eval/summarize.py --split test

Đọc mọi file results/runs/<split>/*.json (oracle chỉ dùng cho mục kiểm tra khung, không vào bảng so sánh) và tạo:
  RESULTS.md       mục a–g: thông tin chạy, hạn mức Groq, kiểm tra khung, bảng EX theo loại + phân bố nhãn,
                   ví dụ lỗi tiêu biểu, ví dụ câu trả lời, những gì chưa làm
  errors_B1.md     toàn bộ câu sai của B1 run 1
  ex_by_type.png   EX theo loại câu, mỗi cấu hình một màu, thanh lỗi = độ lệch chuẩn khi có ≥ 2 lần chạy
  verdicts.png     phân bố nhãn (run 1) theo cấu hình
Phần viết tay lấy từ results/midterm/manual.json: groq_limits (mục b), error_picks (mục e),
answer_picks (mục f, bỏ trống thì tự chọn), not_done và code_changes_after_test (mục g).
"""
import argparse
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from run_eval import CACHE_DIR, RUNS_DIR, VERDICTS, file_name  # noqa: E402
from split_dev_test import TYPES, canonical_hash  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QDIR = ROOT / "eval" / "questions"
OUT_DIR = ROOT / "results" / "midterm"
# (tên, baseline, model) theo thứ tự trong bảng; màu gắn cố định với cấu hình. Groq đã gỡ llama-3.1-8b-instant và
# llama-3.3-70b-versatile (16/08/2026) nên B1 dùng gpt-oss-20b (model yếu), B3 dùng gpt-oss-120b (model mạnh).
CONFIGS = [
    ("B1", "b1_zeroshot", "openai/gpt-oss-20b"),
    ("B3", "b1_zeroshot", "openai/gpt-oss-120b"),
    ("B2", "b2_langchain", "openai/gpt-oss-20b"),
]
PLANNED_RUNS = 3
# Bảng màu phân loại (đã kiểm tra mù màu theo cặp kề nhau), dùng theo thứ tự cố định, không xoay vòng
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
CONFIG_COLORS = {name: SERIES[i] for i, (name, _, _) in enumerate(CONFIGS)}
VERDICT_COLORS = dict(zip(VERDICTS, SERIES))
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#ffffff"


def fmt_time(iso):
    return iso.replace("T", " ")[:16] if iso else "?"


def ex(results, t=None):
    rs = [r for r in results if t is None or r["type"] == t]
    return 100 * sum(r["verdict"] == "correct" for r in rs) / len(rs)


def cell(values):
    if len(values) == 1:
        return f"{values[0]:.1f} (1 lần)"
    return f"{statistics.mean(values):.1f} ± {statistics.stdev(values):.1f}"


def code(text, lang=""):
    return f"```{lang}\n{text}\n```"


def short(rows, n=5):
    return json.dumps(rows[:n], ensure_ascii=False) + (f" … ({len(rows)} dòng)" if len(rows) > n else "")


def load_runs(split):
    """{(baseline, model): {run: dữ liệu}} của mọi lượt đã chạy xong."""
    runs = {}
    for f in sorted((RUNS_DIR / split).glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        data["file"] = f.relative_to(ROOT).as_posix()
        runs.setdefault((data["meta"]["baseline"], data["meta"]["model"]), {})[data["meta"]["run"]] = data
    return runs


def cache_progress(baseline, model, run, questions):
    path = CACHE_DIR / file_name(baseline, model, run)
    if not path.exists():
        return 0
    cache = json.loads(path.read_text(encoding="utf-8"))
    return sum(q["id"] in cache for q in questions)


# ---------- biểu đồ ----------

def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.set_axisbelow(True)


def contrast(hex1, hex2):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    a, b = sorted((lum(hex1), lum(hex2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def finish(fig, ax, path, title, legend_cols, note=None):
    """Tiêu đề + chú giải căn trái ở đầu hình (không đè lên vùng vẽ), chú thích nhỏ ở cuối, lưu PNG 200 dpi."""
    height = fig.get_figheight()
    handles, labels = ax.get_legend_handles_labels()
    rows = -(-len(labels) // legend_cols)
    fig.suptitle(title, x=0.01, y=1 - 0.12 / height, ha="left", va="top", color=INK, fontsize=11)
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 1 - 0.45 / height), ncol=legend_cols,
               frameon=False, fontsize=8, labelcolor=INK2, handlelength=1, handleheight=1, columnspacing=1.2)
    if note:
        fig.text(0.01, 0.12 / height, note, color=MUTED, fontsize=7)
    fig.tight_layout(pad=0.6, rect=(0, 0.25 / height if note else 0, 1, 1 - (0.5 + 0.2 * rows) / height))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def plot_ex(rows, path, n_per_type):
    """rows: [(tên, model, {loại: [EX từng lần chạy]})] -> cột nhóm theo loại câu."""
    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=200, facecolor=SURFACE)
    style(ax)
    group = 0.8
    width = group / len(rows)
    for i, (name, model, vals) in enumerate(rows):
        xs = [x - group / 2 + width * (i + 0.5) for x in range(len(TYPES))]
        means = [statistics.mean(vals[t]) for t in TYPES]
        errs = [statistics.stdev(vals[t]) if len(vals[t]) >= 2 else 0 for t in TYPES]
        n_runs = len(vals[TYPES[0]])
        ax.bar(xs, means, width, color=CONFIG_COLORS.get(name, MUTED), edgecolor=SURFACE, linewidth=0.8,
               label=f"{name} · {model} ({n_runs} lần chạy)",
               yerr=errs if n_runs >= 2 else None,
               error_kw={"ecolor": INK2, "elinewidth": 1, "capsize": 3, "capthick": 1})
    ax.set_xticks(range(len(TYPES)), TYPES)
    ax.set_ylim(0, 100)
    ax.set_ylabel("EX (%)", color=INK2, fontsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    multi = any(len(v[TYPES[0]]) >= 2 for _, _, v in rows)
    finish(fig, ax, path, f"Execution accuracy theo loại câu hỏi – tập test ({n_per_type} câu/loại)", 2,
           "Cột = trung bình các lần chạy; thanh lỗi = độ lệch chuẩn (khi có ≥ 2 lần chạy)." if multi else None)


def plot_verdicts(rows, path, total):
    """rows: [(tên, model, {nhãn: số câu})] của run 1 -> thanh ngang chồng theo nhãn."""
    fig, ax = plt.subplots(figsize=(8, 1.9 + 0.55 * len(rows)), dpi=200, facecolor=SURFACE)
    style(ax)
    present = [v for v in VERDICTS if any(c[v] for _, _, c in rows)]
    ys = list(range(len(rows)))[::-1]
    for v in present:
        lefts = [sum(c[u] for u in VERDICTS[:VERDICTS.index(v)]) for _, _, c in rows]
        widths = [c[v] for _, _, c in rows]
        color = VERDICT_COLORS[v]
        ax.barh(ys, widths, 0.55, left=lefts, color=color, edgecolor=SURFACE, linewidth=0.8, label=v)
        text_color = INK if contrast(color, INK) >= contrast(color, SURFACE) else SURFACE
        for y, left, w in zip(ys, lefts, widths):
            if w >= total * 0.045:  # chỉ ghi số khi đoạn đủ rộng
                ax.text(left + w / 2, y, str(w), ha="center", va="center", fontsize=7.5, color=text_color)
    ax.set_yticks(ys, [f"{name}  {model}" for name, model, _ in rows])
    ax.set_xlim(0, total)
    ax.set_xlabel("Số câu (run 1)", color=INK2, fontsize=9)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    finish(fig, ax, path, f"Phân bố nhãn theo cấu hình – tập test ({total} câu, run 1)", len(present))


# ---------- file Markdown ----------

def example_block(r, reason=None):
    lines = [f"**{r['id']}** ({r['type']}) – nhãn `{r['verdict']}`", "", f"- Câu hỏi: {r['question']}"]
    if reason:
        lines.append(f"- **Nguyên nhân:** {reason}")
    lines += ["- Cypher sinh ra:", "", code(r["cypher"] or "(trống)", "cypher"), "", "- Cypher gold:", "",
              code(r["gold"], "cypher"), "", f"- Kết quả gold: `{short(r.get('gold_answer') or [])}`"]
    if "pred_preview" in r:
        lines.append(f"- Kết quả sinh ra ({r.get('pred_rows')} dòng, tối đa 5 dòng đầu): "
                     f"`{json.dumps(r['pred_preview'], ensure_ascii=False)}`")
    if r.get("error"):
        lines.append(f"- Lỗi: `{r['error']}`")
    return "\n".join(lines) + "\n"


def write_errors(b1_run1, path):
    wrong = [r for r in b1_run1["results"] if r["verdict"] != "correct"]
    m = b1_run1["meta"]
    lines = [f"# Câu sai của B1 run 1 ({m['model']}, {m['split']})", "",
             f"{len(wrong)}/{len(b1_run1['results'])} câu sai. Nguồn: `{b1_run1['file']}`. "
             "Thứ tự: theo loại câu, rồi theo id.", ""]
    for t in TYPES:
        rs = [r for r in wrong if r["type"] == t]
        lines += [f"## {t} ({len(rs)} câu sai)", ""]
        lines += [example_block(r) for r in rs]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Tổng hợp kết quả thành gói kết quả giữa kỳ.")
    ap.add_argument("--split", default="test", choices=["dev", "test"])
    args = ap.parse_args()

    questions = json.loads((QDIR / f"{args.split}.json").read_text(encoding="utf-8"))
    split_info = json.loads((QDIR / "split_info.json").read_text(encoding="utf-8"))
    expected_sha = canonical_hash(questions)
    n_per_type = {t: sum(q["type"] == t for q in questions) for t in TYPES}
    manual_path = OUT_DIR / "manual.json"
    manual = json.loads(manual_path.read_text(encoding="utf-8")) if manual_path.exists() else {}
    runs = load_runs(args.split)
    oracle = runs.pop(("oracle", "none"), {})
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # chỉ nhận lượt chạy đủ bộ câu và đúng file câu hỏi
    rejected = []
    for key in list(runs):
        for k, data in list(runs[key].items()):
            m = data["meta"]
            if m["questions_sha256"] != expected_sha or m["n_questions"] != len(questions):
                rejected.append(f"`{data['file']}`: sai file câu hỏi hoặc thiếu câu, không đưa vào bảng")
                del runs[key][k]
        if not runs[key]:
            del runs[key]
    known = {(b, m) for _, b, m in CONFIGS}
    configs = [(n, b, m) for n, b, m in CONFIGS if (b, m) in runs] + \
              [(f"{b}/{m}", b, m) for b, m in sorted(runs) if (b, m) not in known]

    out = [f"# Kết quả giữa kỳ – baseline Text-to-Cypher (tập {args.split})", "",
           "Tạo tự động bằng `python eval/summarize.py --split " + args.split + "` từ các file trong "
           f"`results/runs/{args.split}/`. Mọi con số là kết quả chạy thật; cấu hình/lần chạy chưa chạy xong "
           "không có trong bảng (xem mục g).", ""]

    # a. Thông tin chạy
    all_runs = [(n, runs[(b, m)][k]) for n, b, m in configs for k in sorted(runs[(b, m)])]
    out += ["## a. Thông tin chạy", ""]
    plan_changes = manual.get("changes_from_plan", [])
    if plan_changes:
        out += ["**Thay đổi so với kế hoạch:**", ""] + [f"- {x}" for x in plan_changes] + [""]
    if all_runs:
        out += ["| Cấu hình | Model (ID trên Groq) | Lần | Sinh Cypher (giờ gọi LLM) | Chấm điểm | Số câu |",
                "|---|---|---|---|---|---|"]
        for n, d in all_runs:
            m = d["meta"]
            out.append(f"| {n} | `{m['model']}` | {m['run']} | {fmt_time(m['llm_first_call_at'])} → "
                       f"{fmt_time(m['llm_last_call_at'])} | {fmt_time(m['finished_at'])} | {m['n_questions']} |")
        metas = [d["meta"] for _, d in all_runs]
        schemas = {m.get("schema_sha256") for m in metas if m.get("schema_sha256")}
        first = metas[0]
        out += ["",
                f"- Temperature: {', '.join(sorted({str(m['temperature']) for m in metas}))}; "
                f"timeout mỗi truy vấn: {first['timeout_s']} s; chạy ở chế độ chỉ đọc; "
                f"đọc tối đa {first['max_rows_read']} dòng kết quả (gold ≤ 20 dòng nên không ảnh hưởng chấm).",
                f"- Số lần chạy mỗi cấu hình: " + ", ".join(f"{n} = {len(runs[(b, m)])}" for n, b, m in configs) + ".",
                f"- Neo4j: {first['neo4j']}. Thư viện: "
                + ", ".join(f"{k} {v}" for k, v in first["packages"].items()) + ".",
                f"- SHA-256 của `{args.split}.json` (chuẩn hóa như `split_info.json`): `{expected_sha}`"
                + (f" – **{'khớp' if expected_sha == split_info['test_sha256'] else 'KHÔNG khớp'}** "
                   "`split_info.json`." if args.split == "test" else "."),
                f"- Schema đưa vào prompt: {'giống nhau ở mọi lượt' if len(schemas) <= 1 else 'KHÁC NHAU giữa các lượt'}"
                + (f" (SHA-256 `{next(iter(schemas))[:16]}…`)." if len(schemas) == 1 else "."), ""]
        prompt_meta = next((m for m in metas if m.get("prompt")), None)
        if prompt_meta:
            out += ["Prompt zero-shot của B1/B3 (giữ nguyên `PROMPT` trong `eval/pilot_text2cypher.py`; "
                    "`{schema}` là schema trích tự động bằng `build_schema`):", "", code(prompt_meta["prompt"]), ""]
        answer_meta = next((m["answers"] for m in metas if m.get("answers")), None)
        if answer_meta:
            out += [f"Prompt sinh câu trả lời văn bản (`{answer_meta['model']}`, tối đa {answer_meta['max_rows']} "
                    "dòng kết quả):", "", code(answer_meta["prompt"]), ""]
    else:
        out += ["Chưa có lượt chạy nào hoàn tất.", ""]

    # b. Hạn mức Groq
    limits = manual.get("groq_limits", {})
    out += ["## b. Hạn mức Groq", ""]
    if limits.get("table"):
        out += [f"Nguồn: {limits.get('source', '?')}; tra ngày {limits.get('checked_at', '?')}.", "",
                "| Model | Requests/phút | Requests/ngày | Tokens/phút | Tokens/ngày |", "|---|---|---|---|---|"]
        out += [f"| `{r['model']}` | {r['rpm']} | {r['rpd']} | {r['tpm']} | {r['tpd']} |" for r in limits["table"]]
        out += [""] + [f"- {x}" for x in limits.get("notes", [])] + [""]
    else:
        out += ["(Chưa điền trong `manual.json`.)", ""]

    # c. Kiểm tra khung bằng oracle
    out += ["## c. Kiểm tra khung chấm bằng oracle", "",
            "Oracle trả về đúng Cypher gold; khung đúng khi chấm 100% `correct`. Oracle không phải baseline.", "",
            "| Tập | Đúng | Tỉ lệ | Ngày chạy |", "|---|---|---|---|"]
    for split in ("dev", "test"):
        f = RUNS_DIR / split / file_name("oracle", None, 1)
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            ok = sum(r["verdict"] == "correct" for r in d["results"])
            out.append(f"| {split} | {ok}/{len(d['results'])} | {100 * ok / len(d['results']):.0f}% | "
                       f"{fmt_time(d['meta']['finished_at'])} |")
        else:
            out.append(f"| {split} | chưa chạy | – | – |")
    out.append("")

    # d. Bảng EX + phân bố nhãn
    out += ["## d. Execution accuracy (EX) theo loại câu hỏi", ""]
    ex_rows = []
    if configs:
        out += [f"EX = % câu `correct` ({' / '.join(str(n_per_type[t]) for t in TYPES)} câu mỗi loại, "
                f"{len(questions)} câu tổng). Có ≥ 2 lần chạy: trung bình ± độ lệch chuẩn mẫu (n−1); "
                "có 1 lần: số của lần đó, ghi \"(1 lần)\".", "",
                "| Cấu hình | Model | Số lần chạy | " + " | ".join(TYPES) + " | Tổng |",
                "|---|---|---|" + "---|" * (len(TYPES) + 1)]
        for n, b, m in configs:
            rs = [runs[(b, m)][k]["results"] for k in sorted(runs[(b, m)])]
            vals = {t: [ex(r, t) for r in rs] for t in TYPES}
            ex_rows.append((n, m, vals))
            out.append(f"| {n} | `{m}` | {len(rs)} | " + " | ".join(cell(vals[t]) for t in TYPES)
                       + f" | {cell([ex(r) for r in rs])} |")
        out += ["", "### Phân bố nhãn (run 1)", "",
                "| Cấu hình | Model | " + " | ".join(VERDICTS) + " | Tổng |", "|---|---|" + "---|" * (len(VERDICTS) + 1)]
        verdict_rows = []
        for n, b, m in configs:
            if 1 not in runs[(b, m)]:
                out.append(f"| {n} | `{m}` | " + " | ".join("–" for _ in VERDICTS) + " | chưa có run 1 |")
                continue
            res = runs[(b, m)][1]["results"]
            counts = {v: sum(r["verdict"] == v for r in res) for v in VERDICTS}
            verdict_rows.append((n, m, counts))
            out.append(f"| {n} | `{m}` | " + " | ".join(str(counts[v]) for v in VERDICTS) + f" | {len(res)} |")
        out += ["", "Biểu đồ: `ex_by_type.png`, `verdicts.png`.", "",
                "![EX theo loại câu](ex_by_type.png)", "", "![Phân bố nhãn](verdicts.png)", ""]
        plot_ex(ex_rows, OUT_DIR / "ex_by_type.png", n_per_type[TYPES[0]])
        if verdict_rows:
            plot_verdicts(verdict_rows, OUT_DIR / "verdicts.png", len(questions))
    else:
        out += ["Chưa có lượt chạy nào hoàn tất.", ""]

    # e. Ví dụ lỗi + errors_B1.md
    b1 = runs.get(next((b, m) for n, b, m in CONFIGS if n == "B1"), {}).get(1)
    out += ["## e. Ví dụ lỗi tiêu biểu (B1 run 1)", ""]
    if b1:
        write_errors(b1, OUT_DIR / "errors_B1.md")
        by_id = {r["id"]: r for r in b1["results"]}
        picks = [p for p in manual.get("error_picks", []) if p["id"] in by_id]
        out += [f"Chọn tay từ `errors_B1.md` (toàn bộ {sum(r['verdict'] != 'correct' for r in b1['results'])} "
                "câu sai của B1 run 1).", ""]
        out += [example_block(by_id[p["id"]], p["reason"]) for p in picks] or ["(Chưa chọn ví dụ.)", ""]
        if manual.get("error_notes"):
            out += ["**Ghi chú thêm:**", ""] + [f"- {x}" for x in manual["error_notes"]] + [""]
    else:
        out += ["Chưa có B1 run 1 nên chưa có `errors_B1.md`.", ""]

    # f. Ví dụ câu trả lời
    out += ["## f. Ví dụ câu trả lời văn bản (B1 run 1, câu đúng)", ""]
    with_answer = [r for r in (b1["results"] if b1 else []) if r["verdict"] == "correct" and r.get("answer")]
    if with_answer:
        chosen = [r for r in with_answer if r["id"] in manual.get("answer_picks", [])]
        if not chosen:  # tự chọn: mỗi loại một câu, tối đa 3 câu
            for t in TYPES:
                chosen += [r for r in with_answer if r["type"] == t][:1]
            chosen = chosen[:3]
        for r in chosen:
            out += [f"**{r['id']}** ({r['type']})", "", f"- Câu hỏi: {r['question']}", "- Cypher:", "",
                    code(r["cypher"], "cypher"), "", f"- Kết quả: `{short(r['pred_preview'])}`",
                    f"- Câu trả lời: {r['answer']}", ""]
    else:
        out += ["Chưa có (cần chạy B1 test run 1 với cờ `--answers`).", ""]

    # g. Những gì chưa làm
    out += ["## g. Những gì chưa làm hoặc chưa chạy", ""]
    for n, b, m in CONFIGS:
        todo = [k for k in range(1, PLANNED_RUNS + 1) if k not in runs.get((b, m), {})]
        progress = {k: cache_progress(b, m, k, questions) for k in todo}
        if len(todo) == PLANNED_RUNS and not any(progress.values()):
            out.append(f"- {n} (`{m}`): chưa chạy lần nào.")
            continue
        for k in todo:
            status = (f"chưa chạy xong (mới sinh Cypher cho {progress[k]}/{len(questions)} câu)" if progress[k]
                      else "chưa chạy")
            out.append(f"- {n} (`{m}`) run {k}: {status}.")
    out += [f"- {x}" for x in rejected + manual.get("not_done", [])]
    changes = manual.get("code_changes_after_test", [])
    out += ["", "Sửa code sau khi đã chạy test (quy tắc 2): " + ("" if changes else "không có."), ""]
    out += [f"- {x}" for x in changes] + ([""] if changes else [])

    (OUT_DIR / "RESULTS.md").write_text("\n".join(out), encoding="utf-8")
    print(f"Đã ghi {(OUT_DIR / 'RESULTS.md').relative_to(ROOT)}"
          + (", errors_B1.md" if b1 else "") + (", ex_by_type.png, verdicts.png" if configs else ""))


if __name__ == "__main__":
    main()
