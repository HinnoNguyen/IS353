"""A + B + C (tắt D) – cấu hình đề xuất không dùng vòng tự sửa lỗi (D) (Ân - T64).

Được dùng để đo lường đóng góp độc lập của (D) so với proposed đầy đủ (A + B + C + D).
Chạy theo phân công mục 3.3 (Ai chạy gì - T64):
    python eval/run_eval.py --baseline proposed_abc --model openai/gpt-oss-20b --split test2 --run <k> --interleave
"""
from baselines.proposed import build as build_proposed


def build(model):
    return build_proposed(model, off={"D"})
