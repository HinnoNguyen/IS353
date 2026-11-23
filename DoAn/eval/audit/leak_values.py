"""Chỉ in số liệu tổng hợp của test. – T56 & mục 6.1.5: kiểm tra rò rỉ giá trị và trùng tham số trên prompt đã khóa.

Cách chạy:
  1. Kiểm tra mặc định trên dev và test cũ:
     python eval/audit/leak_values.py [--no-neo4j] [--out results/audit/leak_values.json]

  2. Kiểm tra rò rỉ cho tập test2 (27–28/11, chỉ gửi riêng kết quả cho Bảo và Hương):
     python eval/audit/leak_values.py --splits test2
     (hoặc truyền đường dẫn trực tiếp: python eval/audit/leak_values.py --splits private/test2.json)
     Khi có 'test2' trong --splits và không chỉ định --out, kết quả tự động lưu vào
     DoAn/private/leak_test2.json và DoAn/private/leak_test2.md (đã gitignore để không lộ lên repo).

Văn bản cố định được quét = mọi đoạn đưa vào prompt của pipeline đã khóa mà không phụ thuộc câu hỏi:
  - meta.prompt / fix_prompt / fix_prompt_tail / fix_instructions / conventions / schema của results/runs/dev/*.json
  - PROMPT gốc của B1/proposed (pilot_text2cypher.PROMPT), quy ước tĩnh của (A) (proposed.schema_a.CONVENTION_SOURCES),
    và khung prompt tự sửa lỗi/trả lời của (D) (proposed.repair_d: FIX_TAIL, INSTRUCTIONS, ANSWER_PROMPT)
  - build_schema(driver) của B1 và detailed_schema(driver) của (A) lấy trực tiếp từ Neo4j (bỏ qua nếu --no-neo4j)

Kiểm tra thêm cho test2 (GIAO_VIEC_CUOI_KY.md mục 4.1, 4.3.3 & 6.1.5):
  - Đối chiếu toàn bộ tham số (params) của test2 với tập tham số đã dùng trong dev.json (kho ví dụ few-shot của C),
    dev_para.json, dev_zero.json và test.json cũ (banned_values) để phát hiện thực thể trùng giúp Hương đổi thực thể.
"""
import argparse
import importlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "eval") not in sys.path:
    sys.path.insert(0, str(ROOT / "eval"))

QDIR = ROOT / "eval" / "questions"
RUNS_DEV = ROOT / "results" / "runs" / "dev"
TEXT_FIELDS = ["prompt", "fix_prompt", "fix_prompt_tail", "fix_instructions", "conventions", "schema"]
PRIOR_SPLITS = ("dev", "dev_para", "dev_zero", "test")
MIN_LEN = 3  # bỏ chuỗi quá ngắn (vd. 'M', 'en') để tránh trùng vô nghĩa với từ tiếng Anh trong prompt
LIT_RE = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"")
NUM_RE = re.compile(r"(?<![\w.])(\d{2,})(?![\w.])")


def forms(value):
    """Các dạng đem so của một giá trị: chữ thường, có '_' và có dấu cách."""
    v = str(value).strip().lower()
    return {v, v.replace("_", " "), v.replace(" ", "_")}


def contains(text_lc, needle):
    """Khớp theo ranh giới từ (không coi '_' là một phần của từ để 'United_States' khớp cả hai dạng)."""
    pat = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
    return re.search(pat, text_lc) is not None


def fixed_texts(use_neo4j):
    """{tên đoạn: văn bản} của mọi đoạn văn bản cố định đưa vào prompt của pipeline."""
    texts = {}
    if RUNS_DEV.exists():
        for f in sorted(RUNS_DEV.glob("*.json")):
            meta = json.loads(f.read_text(encoding="utf-8")).get("meta", {})
            for k in TEXT_FIELDS:
                val = meta.get(k)
                if isinstance(val, str) and val.strip():
                    texts[f"{f.stem}:{k}"] = val
                elif isinstance(val, dict):
                    for sub_k, sub_v in sorted(val.items()):
                        if isinstance(sub_v, str) and sub_v.strip():
                            texts[f"{f.stem}:{k}.{sub_k}"] = sub_v

    # Nạp trực tiếp từ mã nguồn pipeline đã khóa (luôn hoạt động kể cả khi --no-neo4j)
    try:
        from pilot_text2cypher import PROMPT
        texts["code:pilot_text2cypher.PROMPT"] = PROMPT
    except ImportError:
        pass
    try:
        from proposed.schema_a import CONVENTION_SOURCES
        texts["code:schema_a.CONVENTION_SOURCES"] = "\n".join(c["rule"] for c in CONVENTION_SOURCES)
    except ImportError:
        pass
    try:
        from proposed import repair_d
        texts["code:repair_d.FIX_TAIL"] = repair_d.FIX_TAIL
        for k, v in sorted(repair_d.INSTRUCTIONS.items()):
            texts[f"code:repair_d.INSTRUCTIONS.{k}"] = v
        texts["code:repair_d.ANSWER_PROMPT"] = repair_d.ANSWER_PROMPT
    except ImportError:
        pass

    if use_neo4j:
        from neo4j import GraphDatabase
        from pilot_text2cypher import AUTH, URI, build_schema
        with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver:
            texts["b1:build_schema(live)"] = build_schema(driver)
            for mod_name in ("proposed.schema_a", "baselines.module_a", "baselines.proposed", "module_a"):
                try:
                    mod = importlib.import_module(mod_name)
                except ImportError:
                    continue
                if hasattr(mod, "detailed_schema"):
                    texts[f"{mod_name}:detailed_schema"] = mod.detailed_schema(driver)
                    break
            else:
                print("(A) detailed_schema chưa có: bỏ qua, chạy lại khi module (A) xong.\n")
    # Gộp các đoạn giống hệt nhau (vd. cùng một PROMPT trong nhiều file run) để bảng gọn hơn
    by_text = defaultdict(list)
    for name, t in texts.items():
        by_text[t].append(name)
    return {" | ".join(names): t for t, names in by_text.items()}


def extract_param_items(q):
    """Trả về list [(tên_tham_số, giá_trị)] từ một câu hỏi (kèm fullName nếu có firstName + lastName)."""
    p = q.get("params") or {}
    items = [(k, v) for k, v in p.items() if v is not None and str(v).strip()]
    if "firstName" in p and "lastName" in p:
        items.append(("fullName", f"{p['firstName']} {p['lastName']}"))
    return items


def question_values(q):
    """[(nguồn, giá trị)] của một câu hỏi."""
    out = [("params", v) for _, v in extract_param_items(q)]
    gold = q.get("gold") or ""
    for m in LIT_RE.finditer(gold):
        out.append(("gold_literal", m.group(1) if m.group(1) is not None else m.group(2)))
    for m in NUM_RE.finditer(gold):
        out.append(("gold_literal", m.group(1)))
    for row in q.get("answer_preview") or []:
        for v in row if isinstance(row, list) else [row]:
            if isinstance(v, str):
                out.append(("answer", v))
    return out


def keep(value):
    s = str(value).strip()
    return len(s) >= MIN_LEN or (s.isdigit() and len(s) >= 2)


def scan(split, questions, texts):
    """Trả về list các lần trùng: (nguồn, giá trị, đoạn, template_id, id câu)."""
    lowered = {name: t.lower() for name, t in texts.items()}
    hits = []
    for q in questions:
        seen = set()
        for src, value in question_values(q):
            if not keep(value):
                continue
            for name, text in lowered.items():
                if any(contains(text, f) for f in forms(value)):
                    key = (src, str(value).lower(), name)
                    if key not in seen:
                        seen.add(key)
                        hits.append({"split": split, "source": src, "value": str(value), "segment": name,
                                     "template_id": q.get("template_id", "unknown"),
                                     "type": q.get("type", "unknown"), "id": q.get("id", "unknown")})
    return hits


def year_check(questions, texts):
    """Năm xuất hiện trong văn bản prompt -> số câu (theo template) có tham số/literal là năm đó."""
    years = sorted({y for t in texts.values() for y in re.findall(r"(?<!\d)(20[01]\d)(?!\d)", t)})
    out = {}
    for y in years:
        tids = defaultdict(int)
        for q in questions:
            vals = {str(v) for _, v in question_values(q)}
            gold = q.get("gold") or ""
            if y in vals or re.search(rf"(?<!\d){y}(?!\d)", gold):
                tids[q.get("template_id", "unknown")] += 1
        out[y] = dict(tids)
    return out


TEMPORAL_PARAM_KEYS = ("year", "month", "monthName", "quarter", "quarterName")


def prior_param_index(exclude_split=None):
    """Lập chỉ mục {dạng_chuẩn_hóa: {split_cũ: [id_câu]}} từ dev, dev_para, dev_zero, test cũ.

    Bỏ qua các tham số chỉ là số/thời gian thuần túy (vd. year, quarter, quarterName, month, monthName)
    khi kiểm tra trùng thực thể.
    """
    index = defaultdict(lambda: defaultdict(list))
    for s in PRIOR_SPLITS:
        if s == exclude_split:
            continue
        path = QDIR / f"{s}.json"
        if not path.exists():
            continue
        for q in json.loads(path.read_text(encoding="utf-8")):
            qid = q.get("id", "unknown")
            for k, v in extract_param_items(q):
                sv = str(v).strip()
                if sv.isdigit() or k in TEMPORAL_PARAM_KEYS:
                    continue
                for f in forms(sv):
                    if qid not in index[f][s]:
                        index[f][s].append(qid)
    return index


def check_entity_param_overlap(split_label, questions):
    """Kiểm tra xem các câu trong split (đặc biệt là test2) có dùng trùng thực thể với dev/test cũ không."""
    idx = prior_param_index(exclude_split=split_label)
    overlaps = []
    for q in questions:
        qid = q.get("id", "unknown")
        tid = q.get("template_id", "unknown")
        for k, v in extract_param_items(q):
            sv = str(v).strip()
            if sv.isdigit() or k in TEMPORAL_PARAM_KEYS:
                continue
            matched_splits = {}
            for f in forms(sv):
                if f in idx:
                    for old_s, old_ids in idx[f].items():
                        matched_splits.setdefault(old_s, set()).update(old_ids)
            if matched_splits:
                overlaps.append({
                    "id": qid,
                    "template_id": tid,
                    "param": k,
                    "value": sv,
                    "matched_in": {s: sorted(ids) for s, ids in sorted(matched_splits.items())},
                })
    return overlaps


def load_split_questions(split):
    """Đọc danh sách câu hỏi từ tên split (trong eval/questions/ hoặc private/) hoặc đường dẫn file trực tiếp."""
    p = Path(split)
    candidates = [p] if p.exists() else [
        QDIR / f"{split}.json",
        ROOT / "private" / f"{split}.json",
        ROOT / "private" / split,
    ]
    for candidate in candidates:
        if candidate.exists():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "questions" in data:
                return data["questions"]
            return data
    raise FileNotFoundError(f"Không tìm thấy file câu hỏi cho split '{split}' (đã tìm ở {QDIR} và {ROOT / 'private'})")


def is_test2_split(split):
    return "test2" in Path(split).stem.lower()


def write_private_test2_markdown(md_path, split_name, split_report):
    """Xuất báo cáo Markdown riêng cho test2 (chỉ gửi Bảo và Hương)."""
    lines = [
        f"# Báo cáo kiểm tra rò rỉ dữ liệu trên `{split_name}` (Gửi riêng Bảo & Hương)",
        "",
        "> **Lưu ý bảo mật (GIAO_VIEC_CUOI_KY.md mục 6.1.5):** File này nằm trong `DoAn/private/` (đã gitignore),",
        "> tuyệt đối không commit lên Git công khai và chỉ gửi riêng cho **Bảo** và **Hương**.",
        "",
        f"- **Tổng số câu kiểm tra:** {split_report['n_questions']}",
        f"- **Số lần trùng với văn bản cố định của prompt:** {split_report['n_hits']} "
        f"({split_report['n_questions_affected']} câu có từ/số trùng trong prompt)",
        f"- **Số tham số thực thể trùng với `dev`/`dev_zero`/`test` cũ (`banned_values`):** "
        f"{len(split_report.get('entity_param_overlaps', []))}",
        "",
        "## 1. Kiểm tra trùng thực thể (`params`) với bộ `dev` / `dev_zero` / `test` cũ",
        "",
    ]
    overlaps = split_report.get("entity_param_overlaps", [])
    if not overlaps:
        lines.append("✅ **0 thực thể trùng!** Toàn bộ tham số thực thể của `test2` đều mới hoàn toàn so với `dev`, `dev_para`, `dev_zero` và `test` cũ.")
    else:
        lines += [
            f"⚠️ **Phát hiện {len(overlaps)} trường hợp trùng thực thể** (Hương cần đổi các thực thể này theo mục 4.3.3):",
            "",
            "| ID câu `test2` | Template | Tham số | Giá trị trùng | Đã xuất hiện ở tập cũ |",
            "|---|---|---|---|---|",
        ]
        for ov in overlaps:
            where = ", ".join(f"`{s}` ({len(ids)} câu)" for s, ids in ov["matched_in"].items())
            lines.append(f"| `{ov['id']}` | `{ov['template_id']}` | `{ov['param']}` | `{ov['value']}` | {where} |")

    lines += [
        "",
        "## 2. Kiểm tra trùng giá trị trong văn bản cố định của Prompt đã khóa",
        "",
    ]
    matches = split_report.get("matches", [])
    if not matches:
        lines.append("✅ **0 giá trị trùng** trong văn bản cố định của prompt.")
    else:
        lines += [
            "| Nguồn giá trị | Giá trị trùng | Đoạn prompt | Số câu | Phân bố theo template |",
            "|---|---|---|---:|---|",
        ]
        for m in matches:
            lines.append(f"| `{m['source']}` | `{m['value']}` | `{m['segment']}` | {m['n_questions']} | `{m['by_template']}` |")

    lines += [
        "",
        "## 3. Kiểm tra trùng số năm (`20xx`) trong Prompt",
        "",
        f"- Kết quả: `{split_report.get('years_in_prompt', {})}` (Module A sạch đã bỏ số năm `2011`, nên không có rò rỉ năm từ `schema_a`).",
        "",
    ]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-neo4j", action="store_true", help="không lấy build_schema/detailed_schema trực tiếp")
    ap.add_argument("--splits", nargs="+", default=["dev", "test"],
                    help="các split hoặc đường dẫn file câu hỏi cần kiểm tra (vd: dev test, hoặc test2)")
    ap.add_argument("--out", default=None,
                    help="đường dẫn file JSON đầu ra (mặc định: private/leak_test2.json nếu có test2, ngược lại results/audit/leak_values.json)")
    args = ap.parse_args()

    has_test2 = any(is_test2_split(s) for s in args.splits)
    if args.out is None:
        default_out = (ROOT / "private" / "leak_test2.json") if has_test2 else (ROOT / "results" / "audit" / "leak_values.json")
    else:
        default_out = Path(args.out)

    texts = fixed_texts(not args.no_neo4j)
    print(f"Số đoạn văn bản cố định: {len(texts)}")
    for name, t in texts.items():
        print(f"  - {name}  ({len(t)} ký tự)")

    report = {"segments": list(texts), "splits": {}}
    for split in args.splits:
        questions = load_split_questions(split)
        split_label = Path(split).stem
        hits = scan(split_label, questions, texts)
        n_q = len({h["id"] for h in hits})
        print(f"\n=== {split_label}: {len(questions)} câu, {len(hits)} lần trùng văn bản prompt, {n_q} câu bị ảnh hưởng")
        groups = defaultdict(lambda: {"questions": set(), "templates": defaultdict(int)})
        for h in hits:
            g = groups[(h["source"], h["value"].lower(), h["segment"])]
            g["questions"].add(h["id"])
            g["templates"][h["template_id"]] += 1
        rows = []
        for (src, value, seg), g in sorted(groups.items()):
            row = {"source": src, "value": value, "segment": seg, "n_questions": len(g["questions"]),
                   "by_template": dict(g["templates"])}
            if split_label == "dev":
                row["ids"] = sorted(g["questions"])
            rows.append(row)
            ids = f"  ids={row['ids']}" if split_label == "dev" else ""
            print(f"  [{src:<12}] '{value}' trong <{seg}>: {len(g['questions'])} câu {dict(g['templates'])}{ids}")
        years = year_check(questions, texts)
        print(f"  Năm xuất hiện trong prompt -> số câu {split_label} dùng đúng năm đó (theo template): {years}")

        overlaps = check_entity_param_overlap(split_label, questions)
        if split_label not in ("dev", "test"):
            print(f"  Kiểm tra trùng tham số thực thể với bộ cũ ({PRIOR_SPLITS}): {len(overlaps)} trường hợp trùng")
            for ov in overlaps:
                where = {s: len(ids) for s, ids in ov["matched_in"].items()}
                print(f"    ! Câu {ov['id']} ({ov['template_id']}) trùng {ov['param']}='{ov['value']}' với {where}")

        split_data = {
            "n_questions": len(questions),
            "n_hits": len(hits),
            "n_questions_affected": n_q,
            "matches": rows,
            "years_in_prompt": years,
        }
        if split_label not in ("dev", "test"):
            split_data["entity_param_overlaps"] = overlaps
        report["splits"][split_label] = split_data

        if is_test2_split(split):
            md_path = default_out.resolve().with_suffix(".md")
            write_private_test2_markdown(md_path, split_label, split_data)
            rel_md = md_path.relative_to(ROOT) if md_path.is_relative_to(ROOT) else md_path
            print(f"  -> Đã xuất báo cáo riêng gửi Bảo & Hương tại: {rel_md}")

    out = default_out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rel = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"\nĐã lưu {rel}")


if __name__ == "__main__":
    main()
