"""T59 – Sinh eval/questions/dev_zero.json: 20 câu dev có đáp án đúng là rỗng hoặc 0 (Bằng).

Dùng để chỉnh (D) sao cho không "sửa nhầm" câu vốn đúng (GIAO_VIEC_CUOI_KY.md mục 5.2, 5.4).
Mỗi template dev (10 template, xem split_info.json) có 2 câu. Câu hỏi và Cypher gold lấy nguyên từ
eval/templates/, chỉ khác cách chọn tham số: chọn sao cho gold ra rỗng hoặc [[0]].

Tham số lấy ngẫu nhiên (seed cố định) trong các ứng viên ở ZERO bên dưới. Ứng viên bị loại khi:
- trùng tham số của dev.json, dev_para.json, test.json cũ, câu pilot hoặc tên mẫu trong prompt của (A);
- người có thật nhưng trùng họ tên, hoặc người "không có thật" lại trùng tên một người trong DB;
- gold không ra rỗng/0 hoặc chạy quá 10 s;
- thực thể đã dùng cho câu khác của dev_zero.
Hai template LK-04 (ngày sinh) và MH-01 (quốc gia đang sống) luôn có đáp án với người có thật, nên
dùng người không có trong DB: tên của một người ghép với họ của một người khác cùng quốc gia.

Chạy:  python eval/make_dev_zero.py     (cần Neo4j đủ 327.588 node, 1.477.965 cạnh)
Kiểm tra: python eval/run_eval.py --baseline oracle --split dev_zero   (phải đúng 20/20)
"""
import json
import random
import re
import zlib
from collections import defaultdict
from itertools import zip_longest

from neo4j import GraphDatabase

from generate_questions import (AUTH, OUT_DIR, SEED, TEMPLATE_DIR, URI, display, inline, pilot_entities, reject_reason,
                                run, unique_person)
from proposed.schema_a import sample_names
from split_dev_test import canonical_hash

PER_TEMPLATE = 2
AUTHOR = "Bằng"
NOT_ENTITY = {"monthName", "quarterName"}   # tham số chỉ để hiển thị, không phải thực thể
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
UNIQUE_PERSON = ("MATCH (p:Person) WITH p.firstName AS firstName, p.lastName AS lastName, collect(p) AS ps "
                 "WHERE size(ps) = 1 WITH firstName, lastName, ps[0] AS p ")
MADE_UP = "made_up_person"   # ứng viên do Python sinh (người không có trong DB)
OUTSIDE_MONTHS = "outside_months"

# template_id -> (ghi chú đưa vào trường note, Cypher ứng viên hoặc tên bộ sinh ứng viên bằng Python)
ZERO = {
    "AG-01": ("Quốc gia có trong DB nhưng không ai sống ở đó: đáp án 0.",
              "MATCH (k:Country) WHERE k.name <> 'Australia' "
              "AND NOT EXISTS { (:Person)-[:IS_LOCATED_IN]->(:City)-[:IS_PART_OF]->(k) } "
              "RETURN k.name AS country ORDER BY country"),
    "AG-03": ("Tag có trong DB nhưng không gắn vào Post hay Comment nào: đáp án 0 dù hiểu 'posts' theo cách nào.",
              "MATCH (t:Tag) WHERE t.name =~ '[A-Za-z][A-Za-z0-9_]*' AND NOT EXISTS { (:Message)-[:HAS_TAG]->(t) } "
              "RETURN t.name AS tag ORDER BY tag"),
    "LK-03": ("Người có trong DB nhưng không học trường nào: đáp án rỗng.",
              UNIQUE_PERSON + "WHERE NOT EXISTS { (p)-[:STUDY_AT]->(:University) } "
              "RETURN firstName, lastName ORDER BY lastName, firstName"),
    "LK-04": ("Người không có trong DB (tên và họ lấy từ hai người khác nhau cùng quốc gia): đáp án rỗng.", MADE_UP),
    "MH-01": ("Người không có trong DB (tên và họ lấy từ hai người khác nhau cùng quốc gia): đáp án rỗng.", MADE_UP),
    "MH-03": ("Người có bạn nhưng không người bạn nào sống cùng thành phố: đáp án rỗng.",
              UNIQUE_PERSON + "MATCH (p)-[:IS_LOCATED_IN]->(c:City) WHERE EXISTS { (p)-[:KNOWS]-() } "
              "AND NOT EXISTS { (p)-[:KNOWS]-(:Person)-[:IS_LOCATED_IN]->(c) } "
              "RETURN firstName, lastName ORDER BY lastName, firstName"),
    "PA-01": ("Người thứ nhất không có bạn nào nên không có đường đi: đáp án rỗng.",
              "MATCH (a:Person) WHERE NOT EXISTS { (a)-[:KNOWS]-() } WITH a ORDER BY a.id WITH collect(a) AS loners "
              "MATCH (b:Person) WHERE EXISTS { (b)-[:KNOWS]-() } WITH loners, b ORDER BY b.id "
              "WITH loners, collect(b) AS others UNWIND range(0, size(loners) - 1) AS i "
              "WITH loners[i] AS a, others[(i * 7 + 13) % size(others)] AS b "
              "RETURN a.firstName AS firstName1, a.lastName AS lastName1, b.firstName AS firstName2, "
              "b.lastName AS lastName2 ORDER BY lastName1, firstName1"),
    "PA-03": ("Hai người đều có ít nhất 2 bạn, không là bạn của nhau và không có bạn chung: đáp án rỗng.",
              "MATCH (a:Person) WHERE COUNT { (a)-[:KNOWS]-() } >= 2 WITH a ORDER BY a.id WITH collect(a) AS people "
              "UNWIND range(0, size(people) - 1) AS i WITH people[i] AS a, people[(i * 7 + 13) % size(people)] AS b "
              "WHERE a <> b AND NOT EXISTS { (a)-[:KNOWS]-(b) } "
              "AND NOT EXISTS { (a)-[:KNOWS]-(:Person)-[:KNOWS]-(b) } "
              "RETURN a.firstName AS firstName1, a.lastName AS lastName1, b.firstName AS firstName2, "
              "b.lastName AS lastName2 ORDER BY lastName1, firstName1, lastName2, firstName2"),
    "TM-02": ("Tháng nằm ngoài khoảng dữ liệu (tài khoản được tạo từ 01/2010 đến 09/2012): đáp án 0.", OUTSIDE_MONTHS),
    "TM-04": ("Người có viết comment trước và sau quý này nhưng không viết comment nào trong quý: đáp án 0.",
              UNIQUE_PERSON + "MATCH (c:Comment)-[:HAS_CREATOR]->(p) WITH firstName, lastName, "
              "collect(DISTINCT c.creationDate.year * 4 + c.creationDate.quarter - 1) AS ks "
              "UNWIND range(reduce(m = ks[0], k IN ks | CASE WHEN k < m THEN k ELSE m END), "
              "reduce(m = ks[0], k IN ks | CASE WHEN k > m THEN k ELSE m END)) AS k "
              "WITH firstName, lastName, ks, k WHERE NOT k IN ks "
              "RETURN firstName, lastName, k / 4 AS year, k % 4 + 1 AS quarter, "
              "['first', 'second', 'third', 'fourth'][k % 4] AS quarterName ORDER BY lastName, firstName, year, quarter"),
}


def variants(value):
    s = str(value).strip().lower()
    return {s, s.replace(" ", "_"), s.replace("_", " ")}


def banned_entities(driver):
    """Tham số của các bộ câu đã có, thực thể của câu pilot và tên mẫu trong prompt của (A) (chữ thường)."""
    banned = set()
    for split in ("dev", "dev_para", "test"):
        path = OUT_DIR / f"{split}.json"
        if path.exists():
            for q in json.loads(path.read_text(encoding="utf-8")):
                for k, v in q.get("params", {}).items():
                    if k not in NOT_ENTITY and isinstance(v, str):
                        banned |= variants(v)
    for v in pilot_entities():
        banned |= variants(v)
    for v in re.findall(r"'([^']+)'", sample_names(driver)):
        banned |= variants(v)
    return banned


def feminine_surname(last):
    """Họ dạng giống cái (Makarova, Nováková, Kowalska…): không ghép với tên của người dùng họ dạng giống đực."""
    return last.lower().endswith(("ova", "eva", "ová", "ská", "ska", "cka", "aya"))


def made_up_people(session):
    """Ghép tên của một người với họ của một người khác cùng quốc gia; giữ cặp không trùng ai trong DB.

    Để tên nghe tự nhiên: tên chỉ một chữ và dạng giống đực/cái của hai họ phải như nhau."""
    rows = run(session, "MATCH (p:Person)-[:IS_LOCATED_IN]->(:City)-[:IS_PART_OF]->(k:Country) "
                        "RETURN k.name, p.firstName, p.lastName ORDER BY k.name, p.id")
    existing = {(f, l) for _, f, l in rows}
    full_names = {f"{f} {l}".lower() for _, f, l in rows}
    by_country = defaultdict(list)
    for k, f, l in rows:
        by_country[k].append((f, l))
    out = []
    for k in sorted(by_country):
        people = by_country[k]
        for i, (f, l) in enumerate(people):
            f2, l2 = people[(i * 7 + 13) % len(people)]
            if " " in f or feminine_surname(l) != feminine_surname(l2):
                continue
            if f2 != f and l2 != l and (f, l2) not in existing and f"{f} {l2}".lower() not in full_names:
                out.append({"firstName": f, "lastName": l2})
    return out


def outside_months(session, rng):
    """Các tháng không có tài khoản nào được tạo: năm 2009 và 10–12/2012, xen kẽ hai nhóm."""
    present = {tuple(r) for r in run(session, "MATCH (p:Person) "
                                              "RETURN DISTINCT p.creationDate.year, p.creationDate.month")}
    groups = [[(y, m) for m in months if (y, m) not in present] for y, months in ((2009, range(1, 13)),
                                                                              (2012, range(10, 13)))]
    for g in groups:
        rng.shuffle(g)
    order = [c for pair in zip_longest(*groups) for c in pair if c]
    return [{"year": y, "month": m, "monthName": MONTHS[m - 1]} for y, m in order]


def candidates(session, source, rng):
    if source == MADE_UP:
        out = made_up_people(session)
    elif source == OUTSIDE_MONTHS:
        return outside_months(session, rng)
    else:
        out = [dict(zip(r.keys(), r.values())) for r in session.run(source)]
    rng.shuffle(out)
    return out


def people_ok(session, source, params):
    if source != MADE_UP:
        return unique_person(session, params)
    rows = run(session, "MATCH (p:Person) WHERE (p.firstName = $f AND p.lastName = $l) "
                        "OR toLower(p.firstName + ' ' + p.lastName) = toLower($f + ' ' + $l) RETURN count(p)",
               {"f": params["firstName"], "l": params["lastName"]})
    return rows[0][0] == 0


def make(session, tpl, note, source, banned, used):
    rng = random.Random(SEED + zlib.crc32((tpl["template_id"] + "-zero").encode()))
    cands = candidates(session, source, rng)
    kept, stats = [], defaultdict(int)
    for params in cands:
        if len(kept) >= PER_TEMPLATE:
            break
        entities = [v for k, v in params.items() if k not in NOT_ENTITY and isinstance(v, str)]
        if any(variants(v) & banned for v in entities):
            stats["banned"] += 1
            continue
        if any(variants(v) & used for v in entities):
            stats["used"] += 1
            continue
        if not people_ok(session, source, params):
            stats["person_check"] += 1
            continue
        try:
            rows = run(session, tpl["gold"], params)
        except Exception as e:  # timeout hoặc lỗi Cypher
            stats["error_or_timeout"] += 1
            print(f"  {tpl['template_id']} lỗi: {str(e).splitlines()[0][:120]}")
            continue
        if reject_reason(rows) not in ("empty", "zero"):
            stats["not_zero"] += 1
            continue
        phrasing = tpl["questions"][len(kept) % len(tpl["questions"])]
        kept.append({
            "id": f"{tpl['template_id']}-Z{len(kept) + 1:02d}",
            "template_id": tpl["template_id"],
            "type": tpl["type"],
            "question": phrasing.format(**{k: display(v) for k, v in params.items()}),
            "gold": inline(tpl["gold"], params),
            "params": params,
            "answer_preview": [[str(v) for v in row] for row in rows[:5]],
            "author": AUTHOR,
            "checked_by": "",
            "note": note,
            "subset": "zero",
        })
        for v in entities:
            used |= variants(v)
    return kept, dict(stats), len(cands)


def main():
    split_info = json.loads((OUT_DIR / "split_info.json").read_text(encoding="utf-8"))
    dev_tids = [t for tids in split_info["dev_templates"].values() for t in tids]
    templates = {t["template_id"]: t for f in sorted(TEMPLATE_DIR.glob("*.json"))
                 for t in json.loads(f.read_text(encoding="utf-8"))}
    assert sorted(dev_tids) == sorted(ZERO), "ZERO phải có đúng các template dev trong split_info.json"
    questions, used = [], set()
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver:
        banned = banned_entities(driver)
        with driver.session() as session:
            for tid in dev_tids:
                note, source = ZERO[tid]
                kept, stats, n_cand = make(session, templates[tid], note, source, banned, used)
                if len(kept) < PER_TEMPLATE:
                    raise SystemExit(f"{tid}: chỉ tìm được {len(kept)}/{PER_TEMPLATE} câu (loại {stats})")
                questions += kept
                print(f"{tid}: giữ {len(kept)}/{PER_TEMPLATE} (ứng viên {n_cand}), loại {stats or '-'}")
    out = OUT_DIR / "dev_zero.json"
    out.write_text(json.dumps(questions, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nĐã ghi {out.relative_to(OUT_DIR.parent.parent)}: {len(questions)} câu, "
          f"sha256 (chuẩn hóa) {canonical_hash(questions)}")
    for q in questions:
        print(f"  {q['id']:<10} {q['answer_preview']!s:<8} {q['question']}")


if __name__ == "__main__":
    main()
