# Báo cáo Đánh giá Module (B) Entity Linking trên tập Dev (T32 - Ân)

- **Ngày chạy:** 2026-11-23 18:39:22
- **Tập đánh giá:** `eval/questions/dev.json` (92 câu hỏi)
- **Tình trạng:** Đã sửa lỗi gán quốc gia thành Tag (10/10 câu AG-01). Khi thực thể khớp chính xác nhiều loại trong DB, Module (B) liệt kê đầy đủ ứng viên để downstream LLM lựa chọn.

## 1. Kết quả Precision / Recall

| Chỉ số | Trước khi sửa (19/11) | Sau khi sửa (23/11) | Chênh lệch |
|---|:---:|:---:|:---:|
| **True Positives (TP)** | 88 | **98** | +10 |
| **False Negatives (FN)** | 10 | **0** | -10 (0 câu bỏ sót) |
| **False Positives (FP)** | 10 | **10** | 0 |
| **Precision** | 89.80% | **90.74%** | +0.94% |
| **Recall** | 89.80% | **100.00%** | **+10.20% (Đạt 100%)** |
| **F1-Score** | 89.80% | **95.15%** | **+5.35%** |
| **Question Coverage** | 82 / 92 (89.13%) | **92 / 92 (100.0%)** | **+10.87%** |

## 2. Chi tiết 10 câu AG-01 (Quốc gia vừa là Country vừa là Tag)

Trước đây, thứ tự ưu tiên gán nhầm sang `Tag` do tra Tag trước Place. Sau khi sửa, cả hai nhãn ứng viên đều được sinh ra:

| Mã câu | Câu hỏi | Thực thể | Các loại ứng viên được sinh | Gold mong đợi |
|---|---|---|---|---|
| `AG-01-01` | How many people live in Hong Kong? | **Hong_Kong** | `Country, Tag` | `Country` |
| `AG-01-02` | What is the number of people living in France? | **France** | `Country, Tag` | `Country` |
| `AG-01-03` | How many residents of Bolivia are there in the network? | **Bolivia** | `Country, Tag` | `Country` |
| `AG-01-04` | How many people live in Cuba? | **Cuba** | `Country, Tag` | `Country` |
| `AG-01-05` | What is the number of people living in New Zealand? | **New_Zealand** | `Country, Tag` | `Country` |
| `AG-01-06` | How many residents of Cameroon are there in the network? | **Cameroon** | `Country, Tag` | `Country` |
| `AG-01-07` | How many people live in Niger? | **Niger** | `Country, Tag` | `Country` |
| `AG-01-08` | What is the number of people living in Ethiopia? | **Ethiopia** | `Country, Tag` | `Country` |
| `AG-01-09` | How many residents of Ukraine are there in the network? | **Ukraine** | `Country, Tag` | `Country` |
| `AG-01-10` | How many people live in Cambodia? | **Cambodia** | `Country, Tag` | `Country` |

## 3. Định dạng gợi ý đưa vào Prompt (`format_hints`)

Ví dụ với câu `AG-01-02` (*"What is the number of people living in France?"*):
```text
Relevant entities in the graph:
- Country: name='France'
- Tag: name='France'
```
Downstream LLM dựa vào ngữ cảnh câu hỏi (*"people living in France"*) để chọn chính xác nhãn `Country` thay vì bị ép dùng `Tag`.
