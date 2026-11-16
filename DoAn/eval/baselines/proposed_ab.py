"""A + B (tắt C, D) – đánh giá tác động của (A) Schema sạch + (B) Entity Linking trên dev (T32 - Ân).

Không chạy trên test2.
"""
from baselines.proposed import build as build_proposed


def build(model):
    return build_proposed(model, off={"C", "D"})
