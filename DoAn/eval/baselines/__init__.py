"""Các baseline sinh Cypher cho eval/run_eval.py.

Mỗi module có đúng một hàm build(model) trả về hàm: câu hỏi (tiếng Anh) -> MỘT câu Cypher ("" nếu không sinh được).
Hàm đó được phép raise khi gọi LLM lỗi (run_eval ghi nhận là llm_error). Baseline chỉ sinh Cypher;
chạy truy vấn, timeout và chấm điểm do run_eval làm.
Nếu hàm trả về có thuộc tính `meta` (dict, vd. prompt và schema), run_eval ghi nó vào meta của lượt chạy.
"""
