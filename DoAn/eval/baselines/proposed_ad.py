"""A + D (tắt B, C) – chỉ dùng trên dev và dev_zero để chỉnh (D) khi (B), (C) chưa có (T34).

Không thuộc các cấu hình ở GIAO_VIEC_CUOI_KY.md mục 3.2. KHÔNG chạy trên test2.
"""
from baselines.proposed import build as build_proposed


def build(model):
    return build_proposed(model, off={"B", "C"})
