## 5. Vòng đời tác vụ

`LOAD_CONTEXT → PLAN → IMPLEMENT → VERIFY → REVIEW_DIFF → REPORT → DONE`; VERIFY hỏng → `DIAGNOSE → FIX → VERIFY` hoặc
`STOP` (§7). Chưa thoả điều kiện ra thì không sang bước sau.

| Trạng thái | Làm gì · ra khi | Skill bắt buộc (người dùng chốt 15/11/2026) |
| --- | --- | --- |
| LOAD_CONTEXT | Đọc `AGENTS.md` (+ `docs/knowledge/trang_thai.md` nếu có), khoanh đúng tệp liên quan (§11) · biết ràng buộc và tập tệp | — |
| PLAN | Giả định (§1), cách kiểm từng bước (§4), `Sẽ sửa: … · Có thể ảnh hưởng: … · Không đụng tới: …` · phạm vi tường minh, tiêu chí đo được | mơ hồ / tính năng mới → `superpowers:brainstorming`; nhiều bước, đã rõ → `superpowers:writing-plans` |
| IMPLEMENT | Chỉ sửa tệp «Sẽ sửa» · xong, trong phạm vi | `superpowers:test-driven-development`; có kế hoạch → `superpowers:executing-plans` / `superpowers:subagent-driven-development` |
| DIAGNOSE | Lỗi, test hỏng, hành vi lạ — trước khi sửa | `superpowers:systematic-debugging` |
| VERIFY | Kiểm phần liên quan trước (test module, linter, build); toàn bộ khi thay đổi lan rộng hoặc `AGENTS.md` đòi. Không có test tự động: nói đã kiểm bằng cách nào — «không có test» không phải lý do bỏ kiểm · pass, hoặc hỏng đã báo theo §7 | `superpowers:verification-before-completion` |
| REVIEW_DIFF | §6, không ngoại lệ | `ponytail:ponytail-review` + `code-review` hoặc `superpowers:requesting-code-review` |
| REPORT | §8 | — |

- Skill gọi bằng `Skill` thật, khai báo `[ACTION]`, nêu ở REPORT. Harness quyết *được làm gì, dừng ở đâu, báo cáo ra
  sao*; superpowers quyết *đi qua bước nào*; ponytail (`full`, plugin tự nạp mỗi phiên và subagent) quyết *viết bao
  nhiêu*. Mâu thuẫn: harness > superpowers > ponytail. TDD + ponytail: test viết trước, là kiểm nhỏ nhất fail được
  khi logic hỏng. Commit / push / worktree trong skill chỉ khi người dùng hoặc `AGENTS.md` cho phép.
- Sửa tệp dự án bằng `Edit` / `Write`, không `sed -i` / heredoc. Hook từ chối ghi tệp dự án khi phiên chưa gọi skill
  `superpowers:*`, và giữ lượt một lần nếu đã ghi mà chưa gọi `superpowers:verification-before-completion` sau lần
  ghi cuối.
- **Leo thang phạm vi:** cần sửa tệp ngoài phạm vi → dừng, nêu tệp và vì sao bắt buộc, xin xác nhận **trước khi**
  sửa. Không âm thầm mở rộng rồi báo sau.
