"""A + B + D (tắt C) – cấu hình ghép Schema sạch (A) + Entity Linking (B) + Self-Repair (D) (T35).

Không thuộc mục 3.2; so với proposed đầy đủ để thấy đóng góp của (C) trên dev.
Chỉ dùng trên dev và dev_zero. KHÔNG chạy trên test2.
"""
from baselines.proposed import build as build_proposed


def build(model):
    return build_proposed(model, off={"C"})
