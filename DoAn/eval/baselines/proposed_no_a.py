"""B + C + D, không có (A) (tắt A) – đo pipeline khi chỉ có schema cơ bản của B1 (GIAO_VIEC_CUOI_KY.md mục 3.2).

Chạy trên test2 theo mục 3.3 (Bằng):
    python eval/run_eval.py --baseline proposed_no_a --model openai/gpt-oss-20b --split test2 --run <k> --interleave
"""
from baselines.proposed import build as build_proposed


def build(model):
    return build_proposed(model, off={"A"})
