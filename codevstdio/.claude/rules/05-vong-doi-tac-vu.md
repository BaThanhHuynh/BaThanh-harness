## 5. Vòng đời tác vụ

`LOAD_CONTEXT → PLAN → IMPLEMENT → VERIFY → REVIEW_DIFF → REPORT → DONE`; VERIFY hỏng → `DIAGNOSE → FIX → VERIFY` hoặc
`STOP` (§7). Chưa thoả điều kiện ra thì không sang bước sau.

| Bước | Làm gì · ra khi | Skill bắt buộc (chốt 15/11/2026) |
| --- | --- | --- |
| LOAD_CONTEXT | Đọc `AGENTS.md` (+ `docs/knowledge/trang_thai.md`), khoanh tệp liên quan · biết ràng buộc | — |
| PLAN | Giả định (§1), cách kiểm (§4), `Sẽ sửa · Có thể ảnh hưởng · Không đụng tới` · tiêu chí đo được | mơ hồ / mới → `superpowers:brainstorming`; đã rõ → `superpowers:writing-plans` |
| IMPLEMENT | Chỉ sửa tệp «Sẽ sửa» | `superpowers:test-driven-development`; có kế hoạch → `superpowers:executing-plans` / `superpowers:subagent-driven-development` |
| DIAGNOSE | Lỗi, test hỏng, hành vi lạ — trước khi sửa | `superpowers:systematic-debugging` |
| VERIFY | Kiểm phần liên quan trước, toàn bộ khi thay đổi lan rộng. Không có test: nói đã kiểm bằng cách nào · pass, hoặc hỏng đã báo (§7) | `superpowers:verification-before-completion` |
| REVIEW_DIFF | §6 | `ponytail:ponytail-review` + `code-review` hoặc `superpowers:requesting-code-review` |
| REPORT | §8 | — |

- Mâu thuẫn: harness (*được làm gì, dừng ở đâu, báo cáo*) > superpowers (*đi bước nào*) > ponytail (*viết bao nhiêu*).
  TDD + ponytail: test là kiểm nhỏ nhất fail được khi logic hỏng. Commit / push / worktree chỉ khi người dùng hoặc
  `AGENTS.md` cho phép. Sửa tệp dự án bằng `Edit` / `Write`, không `sed -i` / heredoc.
- **Leo thang phạm vi:** cần sửa tệp ngoài phạm vi → dừng, nêu tệp và lý do, xin xác nhận **trước khi** sửa.
