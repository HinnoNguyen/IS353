"""T34 – Module (D): tự sửa lỗi truy vấn có xét đáp án rỗng/0, và sinh câu trả lời (Bằng).

Interface (GIAO_VIEC_CUOI_KY.md mục 5.2):
    check(session, cypher)                -> None nếu truy vấn ổn, ngược lại Problem(kind, message)
    repair(model, session, head, cypher)  -> (cypher cuối, info): vòng sửa, tối đa MAX_FIXES lần gọi LLM
    answer(model, question, rows)         -> câu trả lời 1–2 câu từ tối đa 20 dòng kết quả

Khác vòng sửa của bản v0 (eval/baselines/proposed_v0.py):
1. Rỗng/0 KHÔNG còn luôn là lỗi. Không có truy vấn, lỗi cú pháp/khi chạy, quá thời gian và trả về nguyên
   node/quan hệ/đường đi là lỗi chắc chắn: bắt sửa. Kết quả rỗng hoặc chỉ có 0/null là "đáng ngờ": LLM xem lại
   và được giữ nguyên truy vấn nếu nó đúng và đáp án thật là rỗng/0.
2. LLM trả lại đúng truy vấn cũ thì dừng (temperature 0 nên hỏi lại cũng ra như cũ).
3. Không trả về truy vấn tệ hơn truy vấn đã có: trong các truy vấn đã thử, chọn truy vấn có kết quả kiểm tra tốt
   nhất (ổn > rỗng/0 > lỗi chắc chắn); bằng nhau thì lấy truy vấn sau cùng.
4. Prompt sửa = phần đầu prompt sinh Cypher (hướng dẫn + schema + câu hỏi) + FIX_TAIL. Lần sinh và lần sửa của
   cùng một câu dùng chung tiền tố, gọi liền nhau nên Groq cache được phần đó (không tính vào hạn mức token).
5. (v2, chỉnh trên dev_zero) Các lần gọi của (D) dùng reasoning_effort="low" với gpt-oss: ở mức mặc định, 7/24 lần
   xem lại bị lặp suy luận tới hết 2.048 token và không trả lời (results/audit/repair_d/). Bản viết lại của một
   truy vấn rỗng/0 mà vẫn ra đúng loại kết quả đó (rỗng -> rỗng, 0 -> 0) thì dừng và giữ truy vấn cũ
   (quyết định same_result): đáp án không đổi, hỏi tiếp chỉ tốn hạn mức và dễ sửa nhầm.
Không bao giờ dùng gold: chỉ dựa vào kết quả chạy thử truy vấn trên Neo4j (session chỉ đọc, timeout 30 s).
"""
import json
import re
from typing import NamedTuple

from neo4j import Query
from neo4j.exceptions import Neo4jError
from neo4j.graph import Node, Path, Relationship

from llm import groq_chat
from pilot_text2cypher import extract_cypher

MAX_FIXES = 2            # tối đa 2 lần sửa (proposal)
TIMEOUT_S = 30           # giống run_eval
ANSWER_MAX_ROWS = 20
D_OPTIONS = {"reasoning_effort": "low"}   # chỉ cho model suy luận gpt-oss, xem llm_options()
STOP_ON_SAME_RESULT = True                # v2; v1 = D_OPTIONS {} và STOP_ON_SAME_RESULT False

MUST_FIX = ("no_query", "error", "timeout", "graph_object")
SUSPICIOUS = ("empty", "zero")


class Problem(NamedTuple):
    kind: str       # một trong MUST_FIX hoặc SUSPICIOUS
    message: str    # mô tả gửi cho LLM, nối sau "Result of running it: "


FIX_TAIL = """
Previous query:
{cypher}
Result of running it: {message}
{instruction}
Return only the Cypher query, with no explanation.
Cypher:"""

INSTRUCTIONS = {
    "fix": "Write a corrected query.",
    "review": ("An empty or zero result can be the true answer, or a sign of a mistake such as a name, label, "
               "property or relationship direction that does not match the schema. Check the query against the "
               "question and the schema above. If the query is correct and the true answer is empty or zero, "
               "return the same query unchanged. Otherwise, return a corrected query."),
}

# Câu đầu nói rõ kết quả CHÍNH LÀ đáp án: thiếu câu này, model coi 1 dòng tên bạn bè là "không có thông tin thành phố"
# và trả lời "không có ai" (thử trên MH-03-02, 16/11).
ANSWER_PROMPT = """A database query was written for the question below and run on the graph. Its results are the answer to the question.
Write the answer as one or two complete English sentences that restate what was asked, using only these results and no other facts.
If the results are only 0 or null, say that there are none.

Question: {question}
Query results ({shown}):
{rows}
Answer:"""
NOT_FOUND = "No matching result was found in the graph for this question."


def is_graph_object(v):
    if isinstance(v, (Node, Relationship, Path)):
        return True
    if isinstance(v, (list, tuple)):
        return any(is_graph_object(x) for x in v)
    if isinstance(v, dict):
        return any(is_graph_object(x) for x in v.values())
    return False


def is_zero(v):
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool) and v == 0)


def check(session, cypher):
    """None nếu truy vấn chạy được và ra giá trị; ngược lại là vấn đề gặp phải (không dùng gold)."""
    if not (cypher or "").strip():
        return Problem("no_query", "no query was produced.")
    try:
        result = session.run(Query(cypher, timeout=TIMEOUT_S))
        records = result.fetch(2)
        result.consume()
    except Neo4jError as e:
        if "TransactionTimedOut" in (e.code or ""):
            return Problem("timeout", f"it did not finish within {TIMEOUT_S} seconds.")
        lines = (e.message or "").strip().splitlines()
        return Problem("error", f"it failed with this error: {lines[0][:300] if lines else e.code}")
    if not records:
        return Problem("empty", "it returned no rows.")
    if any(is_graph_object(v) for r in records for v in r.values()):
        return Problem("graph_object", "it returns whole nodes, relationships or paths instead of property values.")
    if len(records) == 1 and all(is_zero(v) for v in records[0].values()):
        return Problem("zero", "it returned only 0 or null.")
    return None


def severity(problem):
    if problem is None:
        return 0
    return 1 if problem.kind in SUSPICIOUS else 2


def same_query(a, b):
    def norm(s):
        return re.sub(r"\s+", " ", (s or "").strip().rstrip(";")).strip()
    return norm(a) == norm(b)


def llm_options(model):
    """Tham số thêm cho các lần gọi LLM của (D): reasoning_effort chỉ áp dụng cho gpt-oss trên Groq."""
    return dict(D_OPTIONS) if str(model).startswith("openai/gpt-oss") else {}


def repair(model, session, head, cypher, chat=groq_chat):
    """Vòng sửa của (D). head: prompt sinh Cypher bỏ chữ "Cypher:" cuối (hướng dẫn + schema + câu hỏi).

    Trả về (cypher được chọn, info). info gồm first_cypher, fix_calls (số lần gọi LLM để sửa), problems (vấn đề
    của từng truy vấn đã gửi đi sửa), decisions (changed | kept | same_result | unchanged | no_output), chosen (chỉ
    số truy vấn được chọn, 0 = truy vấn đầu) và final_problem (vấn đề còn lại của truy vấn được chọn, None nếu ổn).
    """
    tried = [(cypher, check(session, cypher))]
    info = {"first_cypher": cypher, "fix_calls": 0, "problems": [], "decisions": []}
    while tried[-1][1] is not None and info["fix_calls"] < MAX_FIXES:
        current, problem = tried[-1]
        mode = "review" if problem.kind in SUSPICIOUS else "fix"
        prompt = head + FIX_TAIL.format(cypher=current or "(none)", message=problem.message,
                                        instruction=INSTRUCTIONS[mode])
        new = extract_cypher(chat(model, prompt, **llm_options(model)))
        info["fix_calls"] += 1
        info["problems"].append(problem.kind)
        if not new.strip():
            info["decisions"].append("no_output")
            break
        if same_query(new, current):
            info["decisions"].append("kept" if mode == "review" else "unchanged")
            break
        new_problem = check(session, new)
        if STOP_ON_SAME_RESULT and mode == "review" and new_problem is not None and new_problem.kind == problem.kind:
            info["decisions"].append("same_result")   # viết lại nhưng vẫn rỗng/0: giữ truy vấn cũ
            break
        info["decisions"].append("changed")
        tried.append((new, new_problem))
    chosen = min(range(len(tried)), key=lambda i: (severity(tried[i][1]), -i))
    final_problem = tried[chosen][1]
    info["chosen"] = chosen
    info["final_problem"] = final_problem.kind if final_problem else None
    return tried[chosen][0], info


def plain(v):
    """Giá trị Neo4j -> giá trị ghi được ra JSON."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (Node, Relationship)):
        return {k: plain(x) for k, x in v.items()}
    if isinstance(v, Path):
        return [plain(n) for n in v.nodes]
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    return str(v)   # ngày giờ của Neo4j…


def row_text(row):
    data = {k: plain(v) for k, v in row.items()} if hasattr(row, "items") else plain(list(row))
    return json.dumps(data, ensure_ascii=False)


def answer(model, question, rows, chat=groq_chat):
    """Câu trả lời 1–2 câu từ tối đa ANSWER_MAX_ROWS dòng kết quả (neo4j.Record, dict hoặc list).

    Kết quả rỗng: trả NOT_FOUND, không gọi LLM, để không có gì bị bịa ra."""
    rows = list(rows or [])
    if not rows:
        return NOT_FOUND
    shown = rows[:ANSWER_MAX_ROWS]
    count = (f"{len(rows)} row" + ("s" if len(rows) > 1 else "")) if len(shown) == len(rows) \
        else f"first {len(shown)} of {len(rows)} rows"
    text = "\n".join(row_text(r) for r in shown)
    reply = chat(model, ANSWER_PROMPT.format(question=question, shown=count, rows=text), **llm_options(model)).strip()
    reply = re.sub(r"^answer:\s*", "", reply, flags=re.I)
    return reply or "Query results: " + "; ".join(row_text(r) for r in shown[:5])
