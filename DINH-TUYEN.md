# DINH-TUYEN — đang làm việc X thì gọi cái gì

> Bảng **chung** cho mọi repo; việc riêng của repo nằm ở `<repo>/AGENTS.md` — đọc **trước** bảng này.
> Tên dưới đây là ảnh chụp 11/10/2026; muốn gọi thì lấy tên từ danh sách skill của **phiên này**.
> **`superpowers` + `ponytail` bắt buộc khi làm dự án** (15/11/2026, bảng ở §5): ô «Gọi» có `superpowers:` / `ponytail:`
> là PHẢI gọi, luật «1%» áp dụng cho hai plugin này. Skill khác: chỉ gọi khi khớp đúng việc (§11).
> Skill cấp quy trình, không cấp quyền (§12). Đừng đọc `INVENTORY.md` để chọn skill — danh sách đã có trong ngữ cảnh.

## Bộ đang bật — chốt 11/10/2026

Căn cứ: số lần dùng thật trong transcript từ 01/09 (45 phiên) và chi phí nạp mỗi lượt — `VAN-HANH.md` mục «Quota».

| Nguồn | Dùng thật | Giữ vì |
| --- | --- | --- |
| Công cụ lõi (Bash, Edit, Read, Write, Grep, Glob, PowerShell) | ~4.800 lượt | Gần hết công việc |
| MCP `claude-in-chrome` | 123 lượt | Chrome thật, có phiên đăng nhập của người dùng; chỉ nạp tên công cụ |
| Connector Google Drive | 40 lượt | Tìm / tải tài liệu; chỉ nạp tên công cụ |
| `superpowers` | **Bắt buộc** (§5) | Skill quy trình theo trạng thái; hook chặn ghi tệp dự án khi chưa gọi |
| `ponytail` | **Bắt buộc** (§5) | Chế độ `full` tự nạp mỗi phiên / subagent; `ponytail:ponytail-review` ở REVIEW_DIFF |
| `anthropic-skills` (tài khoản) | 2 lần | `docx` / `xlsx` / `pdf` / `pptx` — bài báo `.docx`, phiếu gán nhãn `.xlsx` |
| Skill có sẵn của app | — | `code-review`, `run`, `dataviz`, `security-review`, `simplify` |

## Chọn model / subagent (§11 — agent tự quyết, người dùng cho phép 11/10/2026)

| Loại việc | Làm ở đâu | Vì sao |
| --- | --- | --- |
| Quyết định, thiết kế, gỡ lỗi khó, viết báo cáo | Phiên chính (Opus, effort `high`) | Cần toàn bộ ngữ cảnh và suy luận mạnh |
| Tìm rộng / đọc nhiều tệp để rút một kết luận | `Agent` · `subagent_type: "Explore"` · `model: "haiku"` | Tệp đọc nằm trong ngữ cảnh của subagent; phiên chính chỉ nhận kết luận + `tệp:dòng` |
| Sửa cơ học nhiều tệp theo kế hoạch đã rõ | `Agent` · `model: "sonnet"` + phạm vi «Sẽ sửa» | Rẻ hơn Opus; phiên chính vẫn rà diff (§6) |
| Việc dưới ~5 lượt gọi | Tự làm | Subagent khởi động lạnh với ~sàn ngữ cảnh, không rẻ hơn |
| Gỡ lỗi nhiều tầng, thiết kế, số liệu bài báo | Một dòng đề nghị người dùng nâng `xhigh` | Phiên không tự đổi effort của chính nó |

## Theo việc

| Trạng thái / loại việc | Gọi | Dự phòng |
| --- | --- | --- |
| PLAN — yêu cầu mơ hồ, tính năng mới | `superpowers:brainstorming` | — |
| PLAN — việc nhiều bước, yêu cầu đã rõ | `superpowers:writing-plans` | — |
| IMPLEMENT — thực thi kế hoạch đã viết | `superpowers:executing-plans` / `superpowers:subagent-driven-development` | `Agent` + `model: "sonnet"` |
| IMPLEMENT — mọi thay đổi hành vi | `superpowers:test-driven-development` (test = kiểm nhỏ nhất, ponytail) | — |
| VERIFY / FAIL — lỗi, test hỏng, hành vi lạ — **trước khi sửa** | `superpowers:systematic-debugging` | — |
| VERIFY — trước khi báo xong | `superpowers:verification-before-completion` | — |
| REVIEW_DIFF — tìm lỗi | `code-review` *(built-in)* | `superpowers:requesting-code-review` |
| REVIEW_DIFF — làm thừa / quá phức tạp | `ponytail:ponytail-review` | `simplify` *(built-in — tự SỬA, chỉ khi phạm vi cho phép)* |
| REVIEW_DIFF — bảo mật | `security-review` *(built-in)* | — |
| Nhận góp ý (phiếu của thầy, review) | `superpowers:receiving-code-review` | — |
| DONE | ⚠️ CredX: **không commit / push** (AGENTS §5) | — |
| Tạo / sửa `.docx` `.xlsx` `.pdf` `.pptx` | `anthropic-skills:docx` / `xlsx` / `pdf` / `pptx` | python-docx trong venv của repo |
| Biểu đồ cho bài | `dataviz` | matplotlib trong venv |
| Chạy demo web (Flask: CredX `app.py`, gemini demo, IT-Law-Chatbot) | `run` *(built-in)* | `python app.py` + trình duyệt tích hợp |
| Web cần phiên đăng nhập của người dùng | `mcp__claude-in-chrome__*` (nạp bộ lõi bằng **một** lượt `ToolSearch`) | Trình duyệt tích hợp |
| Web không cần đăng nhập | Trình duyệt tích hợp (`mcp__Claude_Browser__*`) | Chrome headless `--screenshot` khi cần ảnh ra tệp |
| Tài liệu trên Google Drive | Connector Google Drive | — |
| §13: quy trình lặp lại thành skill | `superpowers:writing-skills` | `anthropic-skills:skill-creator` |
| Xem token / lượt gọi | Phiên đang chạy: `harness.py do-ton` · các phiên gần đây: `harness.py bao-cao` | `claude plugin details <plugin>` (chi phí dự kiến của một plugin) |

## Đã TẮT / GỠ — đừng gọi

- `mattpocock-skills` (tắt 15/11): 0 lần gọi trong mọi transcript; trùng superpowers (`tdd`, `code-review`, `diagnosing-bugs`).
- `claude-mem` (tắt 11/10): gọi Claude bằng **quota gói của người dùng**, hết hạn mức từ 28/09 nên ngừng ghi; 0 lần
  agent tra cứu nó trong 45 phiên; trùng vai với `AGENTS.md` + `docs/knowledge/`. Dữ liệu cũ ở `~/.claude-mem/`.
- `caveman` (tắt 11/10): 0 lần gọi skill, 0 subagent từ 01/09; 41 mục (~2,5K token) + lời nhắc đầu phiên và mỗi lượt
  hỏi; chế độ trả lời nén trái §15; 6 skill gắn dịch vụ Caveman Cloud bên ngoài (§10).
- `ecc` (gỡ hẳn 11/10): 1.539 mục, ~58K token mỗi lượt nếu lỡ bật lại.
- MCP `playwright`: không còn trong `~/.claude.json` (11/10).
- Plugin đồng bộ từ claude.ai — `legal`, `finance`, `productivity`, `cowork-plugin-management`, `data`, `engineering`
  (17 MCP chờ đăng nhập, `definite` hỏng) — và connector Claude Docs: 0–4 lần dùng; người dùng tắt trong claude.ai →
  Cài đặt. Còn hiện trong phiên thì vẫn **đừng gọi**.

Bật lại một plugin: `claude plugin enable <tên@marketplace>` rồi mở phiên mới; sửa bảng này cho khớp.
