"""B1 + (A) (tắt B, C, D) – đối chứng thầy yêu cầu: chỉ khác B1 ở khối schema (A) (GIAO_VIEC_CUOI_KY.md mục 3.2).

Chạy trên test2 theo mục 3.3 (Khôi):
    python eval/run_eval.py --baseline proposed_a --model openai/gpt-oss-20b --split test2 --run <k> --interleave
"""
from baselines.proposed import build as build_proposed


def build(model):
    return build_proposed(model, off={"B", "C", "D"})
