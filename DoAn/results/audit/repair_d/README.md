# Chỉnh (D) trên `dev_zero` (T34 – Bằng)

Mục tiêu (GIAO_VIEC_CUOI_KY.md mục 5.2): (D) không được coi kết quả rỗng/0 luôn là lỗi, và không được "sửa nhầm"
câu vốn đúng. Chỉ chỉnh trên dev và `dev_zero`; không đụng test cũ, không xem test2.

- **Bộ câu:** `eval/questions/dev_zero.json`, 20 câu (2 câu × 10 template dev), đáp án đúng là rỗng (12 câu) hoặc 0
  (8 câu). SHA-256 chuẩn hóa `e607128eb1767c64e0cac059fa317169b910fff514ab1a728d5f5b243ecce8e4`. Oracle 20/20.
- **Cấu hình:** `proposed_ad` = (A) `schema_a` của Khôi + (D), `openai/gpt-oss-20b`, temperature 0; chưa có (B), (C).
- **Chỉ số:** EX trước sửa (chấm lại `first_cypher`), EX sau sửa, *sửa nhầm* = câu có `first_cypher` đúng nhưng
  (D) đổi thành sai; tỉ lệ sửa nhầm = sửa nhầm / số câu `first_cypher` đúng.

## Kết quả

| Phiên bản (D) | EX trước sửa | EX sau sửa | Sửa nhầm | LLM/câu | Lần gọi (D) bị cắt | Token của (D) | Token sinh/lần gọi (D) |
|---|---|---|---|---|---|---|---|
| v1: rỗng/0 → LLM xem lại, được giữ nguyên; suy luận mức mặc định | 19/20 | 19/20 | 0/19 (0%) | 2,20 | 7/24 | 64.964 | 1.289 |
| v2: v1 + `reasoning_effort="low"` + dừng khi bản viết lại vẫn rỗng/0 | 19/20 | 19/20 | 0/19 (0%) | 1,95 | 0/19 | 30.187 | 173 |

v2 được đo bằng `eval/audit/replay_d.py` trên **cùng** 20 truy vấn đầu của v1 (không sinh lại Cypher), nên hai phiên bản
được so theo cặp. Lần sinh Cypher đầu (dùng chung) tốn 33.282 token cho 20 câu. Token đếm từ `results/cache/groq_log.jsonl`
(gồm cả phần prompt Groq có thể đã cache). Ở v2, (D) giữ nguyên 9 truy vấn và dừng `same_result` ở 10 truy vấn, nên truy
vấn cuối của cả 20 câu đúng bằng truy vấn đầu. Câu sai duy nhất (TM-04-Z02) sai ngay từ lần sinh đầu: kết quả khác 0
nên không đi qua (D).

### Trên dev (tạm: 46/92 câu, v2)

Lượt `proposed_ad` trên dev dừng ở 46/92 câu vì hết hạn mức token theo ngày của Groq (16/11). Nhờ `--interleave`, 46
câu này trải đều 5 loại (9–10 câu mỗi loại). Chấm bằng `run_eval.py --cached-only` (file `.partial.json`).

| | EX chỉ (A) (`first_cypher`) | EX (A) + (D) | Được cứu | Sửa nhầm | Gửi (D) | LLM/câu |
|---|---|---|---|---|---|---|
| dev, 46/92 câu | 42/46 | 43/46 | 1 (PA-01-07) | 0 | 4 | 1,09 |

Ba câu còn sai không do (D) gây ra:

- **PA-01-05, PA-01-08:** họ tên nhiều chữ bị tách sai (`lastName: 'Bajić_Mikulic'` thay vì `firstName: 'Nedeljko Bajić'`,
  model còn áp dấu `_` của tên địa danh cho tên người). (D) xem lại nhưng giữ nguyên. Đây là phần việc của (B): tra
  tên trong DB thay vì viết thêm quy ước.
- **AG-01-01:** "Hong Kong" vừa là City vừa là Country trong DB. Model đếm theo City (0 người), gold đếm theo Country
  (2 người). (D) viết lại vẫn theo City nên dừng `same_result`.

46 câu còn lại: chạy lại đúng lệnh `run_eval.py --baseline proposed_ad --model openai/gpt-oss-20b --split dev --run 1
--interleave` khi Groq hồi hạn mức (cache giữ tiến độ), rồi chạy lại `misrepair.py` trên file kết quả đầy đủ.

### Vì sao có v2

Ở v1, 7/24 lần gọi của (D) kết thúc với `finish_reason = length`: gpt-oss-20b lặp suy luận ("But maybe the issue is…
That is fine.") đến hết 2.048 token mà không trả lời. Kết quả cuối không tệ đi (không có câu trả lời thì (D) giữ truy vấn
cũ), nhưng mỗi lần như vậy tốn 2.048 token và khoảng 30 s. Thử lại đúng 10 prompt xem lại với `reasoning_effort="low"`:
cả 10 lần kết thúc bình thường, mỗi lần 64–306 token sinh. 5/10 lần model "viết lại" truy vấn theo cách tương đương (so
khớp họ tên đầy đủ thay cho `{firstName, lastName}`, thêm nhãn `:Place`) và vẫn ra rỗng, nên v2 dừng ngay khi bản viết
lại cho cùng loại kết quả (`same_result`) và giữ truy vấn cũ.

## File

- `dev_zero_v1.json`: số liệu từng câu của v1 (`misrepair.py --json`); `dev_zero_v1_run.json`: file kết quả của lượt v1.
- `dev_zero_v2.json`: số liệu từng câu của v2 (`replay_d.py --tag v2`).
- `dev_partial46.json`: số liệu từng câu của 46 câu dev đã chạy (`misrepair.py --json`); file kết quả tương ứng là
  `results/runs/dev/proposed_ad__openai-gpt-oss-20b__run1.partial.json`.

## Tái lập

```bash
python eval/make_dev_zero.py                                  # ra đúng mã băm ở trên
python eval/run_eval.py --baseline oracle --split dev_zero    # 20/20
python eval/audit/misrepair.py results/audit/repair_d/dev_zero_v1_run.json
python eval/audit/replay_d.py results/audit/repair_d/dev_zero_v1_run.json --tag v2
```

Lượt v1 chạy bằng `run_eval.py --baseline proposed_ad ... --split dev_zero --run 1 --interleave` với
`repair_d.D_OPTIONS = {}` và `repair_d.STOP_ON_SAME_RESULT = False`; muốn chạy lại v1 thì đặt hai giá trị đó.
