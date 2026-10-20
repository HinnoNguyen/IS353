# Đồ án A.22 – Building a Simple Graph-Based Question Answering Tool

Nhóm 13 · IS353.R11 · GVHD: ThS. Trần Hưng Nghiệp

Công cụ hỏi đáp trên đồ thị mạng xã hội **LDBC SNB (SF0.1)** lưu trong **Neo4j**: câu hỏi tiếng Anh được LLM mã nguồn mở chuyển thành truy vấn **Cypher**, chạy trên đồ thị và trả lời bằng văn bản. Bài toán được đánh giá như Text-to-Cypher (execution accuracy) với baseline từ đơn giản đến mạnh.

Chi tiết: [proposal v2](docs/SNA-Group13-A.22-GraphQA-Proposal-v2.docx)

## Cấu trúc thư mục

```
DoAn/
├── scripts/
│   ├── load_ldbc.py        # nạp LDBC SNB SF0.1 (CSV) vào Neo4j
│   └── stats.py            # thống kê đồ thị -> results/graph_stats.md
├── eval/
│   ├── QA_GUIDELINE.md     # quy ước xây bộ câu hỏi QA (bắt buộc đọc trước khi viết câu hỏi)
│   ├── pilot_questions.json# 10 câu hỏi thử nghiệm kèm Cypher gold
│   ├── pilot_text2cypher.py# baseline B1 (LLM zero-shot) + chấm execution accuracy
│   ├── questions/          # bộ câu hỏi: dev.json, test.json (đã đóng băng), split_info.json
│   ├── baselines/          # oracle (kiểm tra khung), b1_zeroshot (B1/B3)
│   ├── llm.py              # gọi LLM qua Groq
│   ├── run_eval.py         # sinh Cypher -> chạy trên Neo4j -> chấm -> results/runs/
│   └── summarize.py        # tổng hợp các lượt chạy -> results/midterm/
├── results/
│   ├── graph_stats.md      # thống kê đồ thị đã đếm trong Neo4j
│   ├── runs/               # kết quả từng lượt chạy (dev/test)
│   └── midterm/            # gói kết quả giữa kỳ (RESULTS.md, errors_B1.md, biểu đồ)
├── docs/                   # proposal, file phân công
├── requirements.txt
└── .env.example            # mẫu biến môi trường (copy thành .env)
```

`data/` (dữ liệu LDBC, ~89 MB) và `.env` (API key) **không** được đưa lên git.

## Chạy lại từ đầu

**1. Cài thư viện**

```bash
cd DoAn
python -m pip install -r requirements.txt
```

**2. Tải dữ liệu.** Vào <https://ldbcouncil.org/benchmarks/snb/datasets/>, mục *SNB Interactive v1 → Initial datasets*, tải ô **hàng `CsvComposite & LongDateFormatter`, cột `0.1`**. Giải nén vào `DoAn/data/` để có thư mục:

```
DoAn/data/social_network-sf0.1-CsvComposite-LongDateFormatter/{static,dynamic}/*.csv
```

File là `.tar.zst`; có thể giải nén bằng Python (`pip install zstandard`):

```python
import tarfile, zstandard
with open("social_network-sf0.1-CsvComposite-LongDateFormatter.tar.zst", "rb") as f, \
     zstandard.ZstdDecompressor().stream_reader(f) as r, tarfile.open(fileobj=r, mode="r|") as t:
    t.extractall("data", filter="data")
```

**3. Chạy Neo4j bằng Docker**

```bash
docker run -d --name graphqa-neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/graphqa123 -v graphqa-neo4j-data:/data neo4j:5-community
```

Mật khẩu `graphqa123` chỉ là mặc định cho máy cá nhân; đổi được qua `NEO4J_PASSWORD` trong `.env`.

**4. Nạp dữ liệu và kiểm tra** (khoảng 1 phút)

```bash
python scripts/load_ldbc.py
python scripts/stats.py      # phải ra 327.588 node và 1.477.965 cạnh
```

Xem đồ thị: <http://localhost:7474> (user `neo4j`).

**5. Sinh bộ câu hỏi từ template**

```bash
python eval/generate_questions.py                 # mọi loại trong eval/templates/
python eval/generate_questions.py --type lookup   # chỉ một loại
```

Template của từng loại nằm trong `eval/templates/<loại>.json` (khuôn mẫu: `lookup.json`). Kết quả ghi vào `eval/questions/<loại>.json`, 10 câu mỗi template, seed cố định nên chạy lại ra đúng bộ câu cũ. Câu bị loại tự động: đáp án rỗng/0, quá 20 dòng, chạy quá 10 s, người trùng họ tên, đồng hạng ở vị trí đầu (trường `check` của template), câu trùng, thực thể đã dùng trong `pilot_questions.json`.

**Chia dev/test**

```bash
python eval/split_dev_test.py
```

Chia theo template (mỗi loại 2 template dev, 3 template test) và bỏ câu dev có thực thể trùng với test. Kết quả: `eval/questions/dev.json`, `test.json` và `split_info.json` (danh sách template mỗi phía, số câu, mã SHA-256 của test). Dev dùng để viết luật B0, chỉnh prompt, lấy ví dụ few-shot; test chỉ dùng để chấm.

**6. Chạy thử baseline B1**

```bash
cp .env.example .env         # rồi điền key của bạn vào .env
python eval/pilot_text2cypher.py
```

Kết quả lưu trong `results/pilot_<thời gian>.md|json`. Chọn LLM bằng `LLM_BACKEND` trong `.env` (`ollama` hoặc `gemini`). Đánh giá chính thức dùng Groq qua `eval/run_eval.py` (mục dưới).

## Chạy đánh giá

Cần Neo4j đang chạy (đã nạp dữ liệu) và `GROQ_API_KEY` trong `.env` (oracle không cần). Tạo key ở <https://console.groq.com/keys>.

**1. Kiểm tra khung chấm bằng oracle** (trả về đúng Cypher gold, phải ra 100% `correct`):

```bash
python eval/run_eval.py --baseline oracle --split dev
python eval/run_eval.py --baseline oracle --split test
```

**2. Chạy baseline.** Thử và gỡ lỗi trên `--split dev`; chỉ chạy `--split test` sau khi prompt đã được commit (đóng băng).

```bash
python eval/run_eval.py --baseline b1_zeroshot --model llama-3.1-8b-instant --split test --run 1 --answers  # B1
python eval/run_eval.py --baseline b1_zeroshot --model llama-3.3-70b-versatile --split test --run 1         # B3a
python eval/run_eval.py --baseline b1_zeroshot --model openai/gpt-oss-120b --split test --run 1             # B3b
```

Lần 2, 3: đổi thành `--run 2`, `--run 3` (không cần `--answers`). `--limit N` chạy thử N câu đầu, không ghi kết quả.

- Cypher sinh ra được cache ngay sau mỗi câu ở `results/cache/` (không commit). Bị dừng giữa chừng (hết hạn mức ngày của Groq, mất mạng) thì chạy lại đúng lệnh cũ là làm tiếp.
- Mỗi câu Cypher chạy ở chế độ chỉ đọc, timeout 30 s, chấm bằng `judge` của `pilot_text2cypher.py`. Nhãn: `correct`, `wrong_result`, `empty_result`, `execution_error`, `timeout`, `no_cypher`, `llm_error`.
- Kết quả: `results/runs/<split>/<baseline>__<model>__run<k>.json` (meta: model, giờ chạy, SHA-256 bộ câu hỏi, prompt, schema; từng câu: Cypher, nhãn, kết quả).

**3. Tổng hợp** thành gói kết quả `results/midterm/` (`RESULTS.md`, `errors_B1.md`, `ex_by_type.png`, `verdicts.png`):

```bash
python eval/summarize.py --split test
```

Phần viết tay (hạn mức Groq, ví dụ lỗi chọn tay kèm giải thích, ghi chú việc chưa làm) nằm trong `results/midterm/manual.json`; chạy lại `summarize.py` sau khi sửa file này.

## Số liệu đồ thị (LDBC SNB SF0.1)

| | Số lượng |
|---|---|
| Node / cạnh | 327.588 / 1.477.965 |
| Person / KNOWS | 1.528 / 14.073 |
| Post / Comment | 135.701 / 151.043 |
| Loại node / kiểu quan hệ | 8 / 15 |

Lưu ý khi viết Cypher: mỗi cặp bạn bè chỉ lưu **một cạnh KNOWS theo một chiều** → luôn viết `-[:KNOWS]-` (không chiều). Xem thêm [eval/QA_GUIDELINE.md](eval/QA_GUIDELINE.md).
