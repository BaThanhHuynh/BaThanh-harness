---
paths:
  - "**/docs/knowledge/**"
---

## 13. Vòng lặp tự học — chạy tới đâu, ghi tới đó

Ghi ngay khi xong một việc đáng ghi, đừng đợi cuối phiên — ngữ cảnh có thể mất bất cứ lúc nào.

**Ghi khi:** (1) vấp lỗi rồi sửa được — ở mã, công cụ hay môi trường; ghi chỗ mất thời gian, không phải chỗ
làm được việc; (2) người dùng bảo ghi — ghi, không hỏi lại; (3) gặp lại lỗi đã có — mở đúng mục cũ, thêm dấu
hiệu nhận biết hoặc nâng mức cảnh báo, **không tạo mục mới**. **Không ghi:** việc chạy trơn; điều mã, `git log`
hay `AGENTS.md` đã tự nói; điều chỉ đúng trong phiên này.

**Ghi vào đâu:** thuộc một dự án → `<repo>/AGENTS.md`; quá dài → `docs/knowledge/` + một dòng trỏ ở
`AGENTS.md`. Diễn biến phiên → `docs/knowledge/nhat_ky/` (chỉ thêm). Trạng thái «mục nào xong, mục nào còn» →
**một** tệp `docs/knowledge/trang_thai.md` (ghi đè cuối phiên; chứa con trỏ và tình trạng, không chép số liệu).

**Báo ngay:** mỗi lần ghi tri thức (`AGENTS.md`, `docs/knowledge/` trừ `nhat_ky/` và `trang_thai.md`), viết trong
chat một dòng `Tri thức mới: <tệp> — <điều học được>` — thiếu thì harness giữ lượt một lần.

**Thang thăng cấp — để agent khôn dần mà luật không phình:** lỗi gặp lần đầu → nhật ký · gặp lại → một dòng
bẫy trong `AGENTS.md` · gặp ở ≥ 2 repo → **đề xuất** thêm vào CLAUDE.md (không tự sửa khi chưa được lệnh) ·
kiểm được bằng máy → **đề xuất** thành cảm biến / dây ngắt trong `~/.claude/harness/harness.py`, rồi rút câu
chữ khỏi luật · lặp lại thành quy trình → đề xuất viết skill. Lỗi đã có bản vá vĩnh viễn trong mã → **xoá**
khỏi tri thức: đó là lịch sử.

**Nhật ký:** nối vào tệp của hôm nay, trần 200 dòng mỗi tệp. Kiểm mã mục trùng bằng chỉ mục trước khi đặt
(phiên khác có thể đang ghi). Quá 20 tệp thì chuyển tệp cũ hơn 30 ngày sang `nhat_ky/luu/`, sau khi rút phần
còn dùng lên `AGENTS.md` / `docs/knowledge/`. Thêm xong thì dựng lại chỉ mục và đọc dòng cảnh báo trùng:
`python ~/.claude/harness/harness.py chi-muc <thư mục nhật ký> <tệp chỉ mục> --ghi-de`

**Khuôn:** lỗi = triệu chứng → nguyên nhân → cách sửa → vì sao đúng → vì sao kiểm tra không bắt được → rào
chắn đã thêm (test fail khi lỗi quay lại, hoặc cảm biến). Phiên = đã làm gì · đã chốt gì + phương án đã loại
và vì sao · còn nợ gì (thiếu trường giữa thì phiên sau đề xuất lại đúng cái đã bị loại). Cả hai kèm bằng chứng
đo được (mã trả về, kích thước tệp, con số). Trước khi bắt tay việc mới, đọc tri thức của repo.

**Quyết định lâu dài** → `docs/knowledge/quyet_dinh/<YYYY-MM-DD>-<chu-de>.md`, dòng đầu `Trạng thái: đề xuất |
đã làm | bác bỏ — <lý do một dòng>`, các mục Vấn đề · Quyết định · Phương án đã cân nhắc · Hệ quả. Ghi chú bác
bỏ chỉ giữ khi ý tưởng đó còn hấp dẫn.

**Phép thử bàn giao:** trước khi ghi `nhat_ky/` / `trang_thai.md`, hỏi: người mở phiên mới, không có lịch sử
chat, có hiểu mọi tham chiếu và kiểm được mọi khẳng định không? Bỏ «như đã bàn», «cách trên», «bản cũ», lời kể
«đã thử X rồi Y» — viết lại thành sự thật hiện tại.
