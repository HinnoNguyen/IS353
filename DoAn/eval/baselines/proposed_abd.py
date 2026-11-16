"""A + B + D (tắt C) – cấu hình ghép Schema sạch (A) + Entity Linking (B) + Self-Repair (D) (T35).

Chờ Module (C) few-shot động từ Vũ (T33) để hoàn thiện toàn bộ A + B + C + D.
Chỉ dùng trên dev và dev_zero. KHÔNG chạy trên test2.
"""
from baselines.proposed import build as build_proposed


def build(model):
    return build_proposed(model, off={"C"})
