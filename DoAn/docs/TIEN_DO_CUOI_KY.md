# Tiến độ giai đoạn cuối kỳ – Nhóm 13

Bảng theo dõi các việc trong `GIAO_VIEC_CUOI_KY.md` (file giao việc của Bảo, gửi riêng, chưa có trong repo).

**Cách cập nhật:** làm xong việc nào thì sửa dòng của mình **trong cùng PR với việc đó**: đổi trạng thái, ghi bằng chứng
(số PR, commit, file, số liệu). Không ghi số liệu nào không có file trong `results/`.

Cập nhật lần cuối: **19/11/2026** (Bằng). Trạng thái dưới đây được kiểm trực tiếp trên `main` (`e20382e`) và PR #16:
đọc file, chạy lại script và test, đối chiếu số liệu, không dựa vào tiêu đề PR.

Ký hiệu: ✅ xong · ⚠️ xong nhưng còn vấn đề · 🔄 đang làm · ⏳ chưa đến hạn · ❌ quá hạn, chưa làm · ❓ không kiểm được qua repo

## Mốc

| Ngày | Mốc |
|---|---|
| 15/11 | (A), (B), (C), (D) hoàn chỉnh trên dev; `dev_zero`; sửa báo cáo audit (T62a, T62b) |
| 19/11 | Tích hợp xong; mỗi cấu hình mục 3.2 chạy 1 lượt trên dev; tỉ lệ sửa nhầm trên `dev_zero` |
| **22/11** | **Khóa pipeline** (tag `freeze-cuoi-ky` trên `main`), không lùi được |
| 23–25/11 | Ân, Vũ đọc mù test2; Khôi kiểm tra rò rỉ; 25/11 Bảo commit `test2.json` kèm mã băm |
| 26/11–6/12 | Chạy test2 (T64): ưu tiên 1 trước 30/11, ưu tiên 2 trước 4/12 |
| 7–13/12 | Bảng kết quả (Khôi), E2 + E4 (Ân), phần báo cáo của từng người |
| 14–27/12 | Báo cáo, slide (Bảo, Hương) |

## Việc cần làm ngay (trước 22/11)

1. **Ân – sửa (B):** ✅ Đã sửa xong: khi tên khớp chính xác nhiều loại (như "France" vừa là Country vừa là Tag), liệt kê
   đầy đủ các loại ứng viên để model lựa chọn theo ngữ cảnh. 10/10 câu AG-01 trên dev và 2/2 câu AG-01 trên dev_zero đều
   được bao phủ 100%. Recall đạt 100,0% trên cả dev và dev_zero; đã lưu kết quả vào `results/entity_link_dev.json` và `results/entity_link_dev.md`.
2. **Bảo – review và merge PR #16 (T35)** rồi tạo tag khi Bằng báo cấu hình chạy được. Từ PR #10 đến #15, chưa PR nào
   có review trên GitHub (#12, #13 do chính tác giả merge; #11 vào `main` kèm PR #12).
3. **Cả nhóm – kết quả dev 1 lượt cho các cấu hình còn lại của mục 3.2**, chạy **sau khi (B) đã sửa** (các cấu hình có B
   đổi prompt). Mỗi lượt dev tốn khoảng 150K token (≈ 3/4 hạn mức ngày của 1 key). Đề xuất chia theo T64:

   | Người | Chạy trên dev | Model |
   |---|---|---|
   | Bằng | `proposed` (dev và dev_zero), `proposed_no_a` (dev và dev_zero) | gpt-oss-20b |
   | Khôi | `proposed_ab` | gpt-oss-20b |
   | Vũ | `b1_zeroshot` (B3), `proposed` | gpt-oss-120b |

   `proposed_a` và `proposed_abc` dùng cùng prompt sinh Cypher với `proposed_ad` và `proposed`, nên có thể lấy
   `first_cypher` của hai lượt đó thay vì chạy riêng (chờ Bảo đồng ý).

   ```bash
   python eval/run_eval.py --baseline <module> --model <model> --split dev --run 1 --interleave
   python eval/audit/misrepair.py results/runs/dev_zero/<module>__<model>__run1.json   # cấu hình có (D)
   ```

## Khi kéo code về

```bash
cd DoAn
git pull
python -m pip install pytest              # tests/test_judge.py cần pytest
python scripts/create_fulltext_index.py   # một lần: full-text index cho (B)
python -m unittest discover -s tests -v   # phải đạt hết (2 ca xfail của test_judge là cố ý)
```

Cài lại cả `requirements.txt` sẽ đổi phiên bản `groq` (đang ghim 0.37.1); bản này vẫn hỗ trợ `reasoning_effort` mà (D) dùng.

## Theo từng người

### Bảo

| Việc | Hạn | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|---|
| Merge kết quả giữa kỳ và 3 nhánh audit | tuần 9/11 | ✅ | PR #6–#9 merge ngày 9/11 |
| Điều phối, review PR | – | ⚠️ | PR #10 do Bảo mở và merge; #11 vào `main` kèm PR #12 (Ân merge); #12, #13 do tác giả tự merge; #15 do HinnoNguyen mở và merge; không PR nào có review |
| Tag `freeze-cuoi-ky` | 22/11 | ⏳ | chưa có tag nào trên GitHub |
| Commit `test2.json`, template, mã băm trong `split_info.json` | 25/11 | ⏳ | |
| Gửi `GIAO_VIEC_CHUNG.md` cho Bằng; key Groq cho mượn khi thiếu | – | ❓ | |
| Báo cáo, slide | 14–27/12 | ⏳ | |

### Khôi

| Việc | Hạn | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|---|
| T31 (A) schema sạch | 15/11 | ✅ | PR #10, `eval/proposed/schema_a.py` (~1.033 token, 7 quy ước có nguồn) |
| T25 kiểm thử `judge` | 15/11 | ✅ | PR #10 và #15, `tests/test_judge.py` (có 2 ca xfail ghi nhận hành vi `judge`) |
| T60 gold rỗng và split mới | 15/11 | ✅ | PR #10; oracle `dev_zero` 20/20 |
| T61 bảng kết quả cuối (`summarize.py --split test2`) | 13/12 | ⏳ | |
| Kiểm tra rò rỉ test2 | 23–25/11 | ⏳ | |

### Ân

| Việc | Hạn | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|---|
| T32 (B) liên kết thực thể | 15/11 (sửa 23/11) | ✅ | Đã sửa lỗi Country → Tag triệt để: liệt kê đủ các ứng viên (Country, City, Tag, Person) cho mọi thực thể đa hình. Kiểm thử 20/20 test đạt (87/87 toàn repo). Dev: P = 90,74%, R = 100,0%, F1 = 95,15%, phủ 92/92 câu (100%). Dev_zero: P = 90,0%, R = 100,0%, F1 = 94,74%, phủ 20/20 câu (100%). Người không có trong DB → 0 gợi ý (đúng). Đã lưu số liệu vào `results/entity_link_dev.json`, `results/entity_link_metrics.json`, `results/entity_link_dev.md` |
| T62a sửa báo cáo T57 | 15/11 | ✅ | `results/audit/chat_luong.md`: tách nhóm (i)/(ii), bỏ bảng "EX khi bỏ câu mơ hồ", ghi rõ "loại khỏi mẫu số", 0 câu/id test. Gửi Hương danh sách template: ✅ (đã lập `docs/DANH_SACH_LOI_NGON_NGU_TEMPLATES_GUI_HUONG.md` chi tiết 25 template cũ và 4 khuyến nghị Test2) |
| T63 đọc mù test2 | 23–25/11 | ⏳ | |
| E2 + E4 | 7–13/12 | ⏳ | |
| (thêm) module mỏng `proposed_ab`, `proposed_abc`, `proposed_abd` | – | ✅ | PR #12 |

### Vũ

| Việc | Hạn | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|---|
| T33 (C) few-shot | 15/11 | ✅ | PR #13: `eval/proposed/fewshot_c.py`, kho ví dụ chỉ từ `dev.json`, tự bỏ ví dụ cùng template (cả câu `dev_zero`, `dev_para`), test đạt |
| T24 sửa B2 | 15/11 | ✅ | dev: không ra Cypher 12/92 → 0/92, đúng 48 → 51; giữ cấu hình mặc định của chain; ghim phiên bản thư viện |
| T62b sửa báo cáo T55 | 15/11 | ✅ | `results/audit/do_kho.md`: bỏ "40–54%", "68–72%", Spider, "chứng minh"; Google-BLEU/Exact Match; CypherBench GPT-4o 60,18%, Claude 3.5 Sonnet 61,58% |
| T63 đọc mù test2 | 23–25/11 | ⏳ | |
| E3 (`proposed` trên 120b) | 26/11–6/12 | ⏳ | |

### Bằng

| Việc | Hạn | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|---|
| T34 (D) có xét rỗng/0 | 15/11 | ✅ | PR #11 (vào `main` qua PR #12) và PR #16: `eval/proposed/repair_d.py`; chi tiết `results/audit/repair_d/README.md` |
| T59 `dev_zero` | 15/11 | ✅ | `eval/questions/dev_zero.json`: 20 câu, 2 câu × 10 template dev, không trùng tham số test cũ; oracle 20/20 |
| T35 tích hợp, cấu hình bậc thang | 19/11 | 🔄 | PR #16: ghép (C), thêm `proposed_a`, `proposed_no_a`; 4 cấu hình chạy thử trên dev đều chạy được. Còn: kết quả dev các cấu hình (mục trên) |
| Review PR (A), (B), (C) | – | ❌ | chưa có review trên GitHub; kiểm code 19/11 tìm ra lỗi Country → Tag của (B) |
| Báo Bảo khóa pipeline | 22/11 | ⏳ | |
| T64 chạy test2: `proposed` (20b), `proposed_no_a` | 26/11–6/12 | ⏳ | |
| Phần báo cáo (D) và tích hợp | 13/12 | ⏳ | |

### Hương

| Việc | Hạn | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|---|
| T58 xây test2, giữ kín | bản nháp 22/11 | ❓ | làm trong `DoAn/private/`, không đưa lên repo (đúng quy tắc) |
| Tổ chức đọc mù, `results/audit/doc_mu_test2.md` | 23–25/11 | ⏳ | |
| Phần báo cáo về cách xây test2 | 13/12 | ⏳ | |

## Kết quả đã có (gpt-oss-20b, lượt 1; test cũ chỉ để chẩn đoán)

| Cấu hình | dev (92 câu) | dev_zero (20 câu) | Ghi chú |
|---|---|---|---|
| B0 rule-based | 92/92 | – | luật viết từ chính dev |
| B1 zero-shot | 53/92 | – | |
| B2 GraphCypherQAChain | 51/92 | – | sau T24 |
| Chỉ (A) (`first_cypher` của `proposed_ad`) | 84/92 | – | PR #16 |
| A + D (`proposed_ad`) | 87/92, sửa nhầm 0/84 | 19/20, sửa nhầm 0/19 | PR #16; `dev_zero` ở `results/audit/repair_d/` |
| A + B + C + D (`proposed`) | chưa chạy | 20/20, sửa nhầm 0/18 | PR #16; chạy trước khi sửa lỗi (B), cần chạy lại |
