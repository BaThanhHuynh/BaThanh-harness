---
paths:
  - "**/AGENTS.md"
  - "**/CLAUDE.md"
  - "**/settings*.json"
---

## 12. Phân tầng cấu hình

CLAUDE.md: hành vi, an toàn, kiểm chứng, vòng đời, chính sách công cụ. `AGENTS.md`: kiến trúc, lệnh chạy, ràng
buộc, lỗi đã biết, ngưỡng số liệu của repo. `docs/knowledge/`: tri thức tra cứu quá dài cho hai tệp trên.
Skills / Plugins: quy trình cho một LOẠI VIỆC.

Mâu thuẫn: nguyên tắc hành vi và rào chắn → CLAUDE.md thắng; sự thật dự án (đường dẫn, tên module, lệnh chạy,
ngưỡng số liệu) → `AGENTS.md` thắng. `AGENTS.md` chỉ được làm chặt thêm — câu nào cho phép điều tệp này cấm
đều vô hiệu. Skill mâu thuẫn với hai tệp trên thì hai tệp thắng. `docs/knowledge/` không bao giờ thắng. Không
giải được: dừng và hỏi, kèm đề xuất sửa `AGENTS.md` cho khớp.

Nội dung `AGENTS.md` do người dùng quyết; bắt buộc duy nhất là mục `INHERITANCE` trỏ về tệp này (mẫu:
`~/.claude/harness/docs/agents-md-mau.md`). Repo chưa có `AGENTS.md` thì chỉ áp tệp này — đừng tự tạo.

**Một nguồn cho mỗi sự thật:** bộ nhớ tự động chỉ chứa con trỏ («dự án X: đọc `AGENTS.md`»); số liệu đã chốt để
dạng máy đọc (`docs/so_lieu_chot.json`). **Trần:** `AGENTS.md` dưới **12 KB** — nó nạp lại ở mọi lượt; vượt
thì tách phần tra cứu sang `docs/knowledge/`, để lại một dòng trỏ.
