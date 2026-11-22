# BaThanh Harness — bộ khung kỷ luật cho agent lập trình Claude Code

**Agent = Model + Harness.** Model giỏi đến đâu cũng cần một lớp vỏ quy định nó được làm gì, phải kiểm chứng ra sao,
nhớ gì giữa các phiên và tốn bao nhiêu. Repo này là lớp vỏ đó, viết cho Claude Code và dùng hằng ngày trên các dự án
thật của tác giả.

- **Một tệp Python duy nhất** (`harness.py`, ~950 dòng), chỉ dùng thư viện chuẩn, không phụ thuộc ngoài.
- **Gắn vào Claude Code qua hook** (`SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`).
- **Hợp đồng bằng văn bản** (`codevstdio/CLAUDE.md` + 16 luật trong `codevstdio/.claude/rules/`) nói agent *phải* làm gì;
  harness **cưỡng chế** những điều văn bản không tự làm được.
- **Fail-open:** lỗi nội bộ của hook được ghi vào log và thoát mã 0. Harness hỏng không bao giờ làm hỏng phiên làm việc.

## Vấn đề cần giải quyết

Số đo từ 45 phiên làm việc thật (09–10/2026), đọc trực tiếp từ transcript của Claude Code:

| Quan sát | Số đo |
| --- | --- |
| Phần nạp cố định mỗi lượt gọi (luật, mô tả skill, plugin) | trung vị **~90K token** trước khi agent làm gì |
| Một phiên dài điển hình | 156 lượt gọi, 285K token mỗi lượt, **44,5 triệu token** cho ~150K token nội dung thật (300:1) |
| Phần chi phí đến từ việc gửi lại ngữ cảnh cũ | **~57%** (quy theo giá tương đối của API) |
| Skill thực sự được gọi | 6 lần / 45 phiên, trong khi ~150 mô tả skill nạp lại ở mọi lượt |
| Kết quả công cụ > 20K ký tự | 46 lần — mỗi lần nằm lại trong ngữ cảnh đến hết phiên |

Ngoài chi phí còn ba rủi ro: agent **quên** việc dở giữa các phiên, **báo xong mà chưa kiểm chứng**, và chạy **lệnh phá huỷ**
(`git reset --hard`, `rm -rf`) hoặc đụng vào tệp bí mật.

## Kiến trúc 6 tầng

| Tầng | Harness làm gì | Cơ chế |
| --- | --- | --- |
| 1. Hướng dẫn | Nạp hợp đồng + bản nhắc rút gọn đầu phiên, bảng «việc X → skill nào» | `SessionStart` chèn ngữ cảnh, chỉ khi hợp đồng chưa tự nạp |
| 2. Cảm biến | Sau mỗi lần ghi tệp: biên dịch `.py`, parse `.json`/`.ipynb` (bắt cả BOM) | `PostToolUse` trả lỗi thẳng về agent |
| 3. Vòng lặp | Dây ngắt: 5 lượt gọi giống hệt liền nhau (kể cả thành công), cùng một lệnh hỏng ≥ 2 lần, mốc 60/120/200 lượt gọi, ngữ cảnh 150K, sang tệp thứ 13 | Nhắc mềm; ngữ cảnh vượt 170K → hộp duyệt cho người dùng; trước khi nén ghi trạng thái, sau nén chèn lại |
| 4. Bộ nhớ | Đầu phiên chèn mục «Tiếp theo» của `trang_thai.md` + tóm tắt phiên trước; cuối phiên đòi ghi bàn giao | `SessionStart` + `Stop` giữ lượt một lần; lệnh `tim` tra xuyên dự án |
| 5. Quyền | Lệnh phá huỷ → hỏi; sửa tệp bí mật → chặn; đọc trọn tệp > 200 KB → chặn | `PreToolUse` + `permissions.deny`/`ask` native làm lớp chắn thứ hai |
| 6. Quan sát | Vết từng lượt gọi, tổng kết token mỗi phiên | `vet/phien/*.jsonl`, `vet/tong-ket/*.json`, lệnh `bao-cao`, `do-ton` |

Thêm một cổng quy trình: agent không được ghi tệp dự án trước khi gọi một skill quy trình (`superpowers:*`), và `Stop` giữ lượt lại nếu đã
sửa tệp mà chưa chạy bước kiểm chứng (`superpowers:verification-before-completion`).

## Quyết định thiết kế đáng chú ý

- **Bộ nhớ bằng tệp, không bằng LLM.** Đã thử plugin `claude-mem` (nén quan sát bằng Haiku, lưu SQLite + Chroma):
  việc nén ăn chung quota với phiên chính, hết quota sau 5 ngày, 88% lượt gọi công cụ không được nén, agent tra cứu
  0 lần, mỗi đầu phiên chèn tới ~10K token. Thay bằng tệp Markdown trong từng repo (`AGENTS.md`,
  `docs/knowledge/trang_thai.md`, `nhat_ky/`) do harness nhắc ghi và tự chèn lại — chi phí gần như bằng 0.
- **Hỏi thay vì chặn cứng ngân sách.** Chặn giữa chừng để lại việc dở dang; nhắc mềm thì bị bỏ qua ở cả 5 phiên đo.
  Nên ở mốc 170K token (trước khi tự nén ở 200K), quyết định được đưa cho người dùng — người nhìn thấy chi phí.
- **Hai lớp quyền.** Cổng regex trong hook có thể sót lệnh ngụy trang, nên các quy tắc quan trọng được lặp lại trong
  hệ thống quyền native của Claude Code — lớp này vẫn chắn khi hook lỗi.

## Cấu trúc repo

```
harness.py                  engine: 4 lệnh hook + lệnh chạy tay
NHAC-DINH-TUYEN.md          bản nhắc chèn đầu phiên (giữ ngắn — nó tốn ngữ cảnh)
DINH-TUYEN.md               bảng «việc X → skill nào», kèm căn cứ giữ / bỏ từng plugin
INVENTORY.md                danh mục skill/plugin, sinh bởi `harness.py quet`
VAN-HANH.md                 ghi chú vận hành: số đo quota, lịch sử thay đổi, cách khôi phục
codevstdio/CLAUDE.md        hợp đồng 16 mục (bản chép)
codevstdio/.claude/rules/   16 luật chi tiết: vòng đời tác vụ, ngắt mạch, quyền, bí mật, ngân sách ngữ cảnh…
dot-claude/settings.json    cấu hình Claude Code: đăng ký hook, quyền, biến môi trường (bản chép)
dot-claude/skills/          skill tự cài (bỏ skills/synced — Anthropic tự đồng bộ theo tài khoản)
dot-claude/plugins/         danh sách plugin + marketplace đã cài, để cài lại
dot-claude/dev-mods/        mod Claude Code tự viết
dot-claude/mcp-servers.json máy chủ MCP theo dự án, trích từ ~/.claude.json, đã che env/headers
githooks/pre-commit         trước mỗi commit tự chép CLAUDE.md, settings.json, skill, plugin, mod, MCP vào repo
```

## Cài đặt

Cần Windows, Claude Code và Python 3 (đang chạy trên 3.14). Đường dẫn mặc định theo máy tác giả
(`D:\codevstdio` cho hợp đồng và repo); muốn dùng chỗ khác thì sửa hằng `HOP_DONG` ở đầu `harness.py`.

Repo nằm ở `D:\codevstdio\BaThanh-harness` cho dễ thấy, dễ sửa; `~/.claude/harness` chỉ là junction trỏ về đây.
Máy mới (PowerShell):

```powershell
git clone https://github.com/BaThanhHuynh/BaThanh-harness.git D:\codevstdio\BaThanh-harness
powershell -ExecutionPolicy Bypass -File D:\codevstdio\BaThanh-harness\cai-dat.ps1
```

`cai-dat.ps1` (chạy lại vô hại; thứ đã có thì bỏ qua) làm: junction `~/.claude/harness` và
`D:\codevstdio\.claude\rules`, chép `CLAUDE.md`, bật git hook, chép skill tự cài, chép `settings.json`
(đổi đường dẫn sang HOME máy mới), rồi tự kiểm. Còn làm tay:

- `settings.json` đã có sẵn → gộp tay khối `hooks`/`permissions` từ `dot-claude/settings.json`.
- Plugin: chạy trong Claude Code các lệnh `/plugin marketplace add …` và `/plugin install …` mà script in ra.
- MCP: thêm bằng `claude mcp add` theo `dot-claude/mcp-servers.json`, điền lại các giá trị `<dien-tay>`.
- Mod: chép `dot-claude/dev-mods/*` vào `~/.claude/dev-mods/<id>/` nếu cần.

## Lệnh chạy tay

| Lệnh | Việc |
| --- | --- |
| `harness.py bao-cao [n]` | Tổng kết n phiên gần nhất: lượt gọi, tệp đã ghi, lệnh hỏng, token |
| `harness.py do-cong` | Mỗi cổng: số lần bắn, số phiên bị bắn, số lần tắt, số lần sau đó chạy được, trung vị lượt vòng |
| `harness.py do-ton` | Đo chi phí ngữ cảnh của phiên đang chạy |
| `harness.py tim <từ khoá…>` | Tra xuyên mọi dự án trong `docs/knowledge/` và tổng kết phiên |
| `harness.py quet` | Quét skill/plugin đang cài, sinh `INVENTORY.md` |
| `harness.py tu-kiem-bat-buoc` | Tự kiểm các cổng bắt buộc |

## Giới hạn đã biết

- Cảm biến chỉ kiểm cú pháp; kiểm chứng ngữ nghĩa (test, chạy lại số liệu) vẫn theo `AGENTS.md` của từng dự án.
- Cổng lệnh phá huỷ tách lệnh bằng `shlex` (bỏ tuỳ chọn toàn cục của git, bỏ qua tham số của `echo`/`grep` trừ khi
  cả lệnh có trình thông dịch như `| sh`, `iex`, phân tích lại chuỗi trong `bash -c`); ngoặc không đóng thì quay về
  regex trên chuỗi thô. Chưa xử lý `env`/`sudo` đứng trước lệnh, `cmd /c"…"` viết dính, `. script` của shell; lồng
  `bash -c` quá sâu thì hook lỗi và để lệnh qua (fail-open). Lệnh ngụy trang kỹ hơn vẫn có thể lọt — lớp
  `permissions` native là lớp chắn thứ hai.
- Chi phí chỉ đếm bằng token, không quy ra tiền (bảng giá thay đổi nên không ghi cứng).
- Tệp ghi qua lệnh shell không được theo dõi như tệp ghi qua công cụ Edit/Write.
- Hợp đồng và luật viết bằng tiếng Việt.

## Tác giả

[BaThanhHuynh](https://github.com/BaThanhHuynh) — thiết kế, đo đạc và vận hành harness trên các dự án cá nhân;
dựng cùng Claude Code.
