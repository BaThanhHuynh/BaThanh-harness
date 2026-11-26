# Học từ DeepSeek Harness — phân tích và đề xuất (26/11/2026)

Nguồn: `github.com/deepseek-ai/deepseek-harness`, commit `4b399c39` (22/11/2026, bản `dsh-0.2.3-alpha.2`).
Đọc bản sao trong scratchpad, không chạy mã của repo.

## 1. Nó là gì — và khác harness của mình ở đâu

- Một **ứng dụng agent hoàn chỉnh** (CLI, web, desktop) viết bằng TypeScript, khoảng 23.000 tệp, 50 gói. Kiến trúc
  «mọi thứ là plugin» trên nền Cordis: nén ngữ cảnh, sandbox, goal, subagent… đều là plugin cắm vào vòng lặp agent.
- Harness của mình là **lớp hook bọc quanh Claude Code** (`harness.py` + luật markdown). Vì vậy nhiều thứ của DSH
  Claude Code đã tự làm (nén, cất output lớn ra tệp, nạp CLAUDE.md lồng nhau) — **không chép lại**.
- Thứ đáng lấy nằm ở ba chỗ: khuôn tóm tắt khi nén, cách giữ tri thức/quyết định, và vài cảm biến nhỏ.

## 2. Thuật toán chính đã đọc

### 2.1 Quản lý ngữ cảnh (`packages/compaction`, `context`, `spill`, `llm/token-meter`)

| Cơ chế | Cách làm | Số liệu / chỗ |
| --- | --- | --- |
| Đếm token | lấy số token nhà cung cấp báo ở lượt trước làm mốc, cộng phần chênh ước lượng `ký tự/4` (+4 mỗi khối, +4 mỗi vai) | `token-meter/src/estimate.ts:13-19` |
| Mốc nén | `min(0,8 × cửa sổ, cửa sổ − max_tokens − 65.536)` | `compaction-basic/src/config.ts:20,75` |
| Giữ đuôi | giữ nguyên văn ~16% ngân sách tin nhắn cuối; lùi điểm cắt cho tới khi không cắt giữa cặp gọi công cụ/kết quả | `DEFAULT_RETAIN_RATIO=0.16`, `region.ts` |
| Trước khi gọi model tóm tắt | cắt giữa mọi kết quả công cụ > 8.192 ký tự (giữ 4.096 đầu + 1.024 cuối), đo lại; đã dưới mốc thì thôi | `compaction-tool-result-pruner/src/config.ts:11-13` |
| Gọi tóm tắt | phát lại **đúng** system prompt + công cụ + lịch sử của lượt trước, thêm chỉ dẫn ở cuối → tận dụng bộ đệm tiền tố (prefix cache) | `summarizer.ts:35-75` |
| Khuôn tóm tắt | 8 mục bắt buộc, mục trống ghi «(none)»: Yêu cầu & ý định · Khái niệm kỹ thuật · Tệp & mã · Lỗi & cách sửa · Việc đang chờ · Việc đang làm · Bước tiếp · Ngữ cảnh then chốt. Giữ nguyên văn đường dẫn, lệnh, chuỗi lỗi, con số; ghi đúng lời người dùng sửa; có bản tóm tắt cũ thì **gộp**, bỏ điều đã cũ | `summarizer.ts:40-61` |
| Chốt an toàn | bản tóm tắt phải nhỏ hơn đoạn nó thay; khoá `start…end` chống nén chồng; thất bại thì thử lại 1 lần | `region.ts:~423` |
| Output lớn | (tuỳ chọn) quá N token thì cất cả ra tệp quyền 0600; model thấy đầu + cuối + đường dẫn + gợi ý `read`/`grep`; công cụ `read` được miễn để không cất lại | `spill-policy/src/index.ts:44-135` |
| Nạp AGENTS.md | chuỗi từ gốc repo xuống cwd; gộp tệp trùng nội dung (SHA-1); trần 64 KB mỗi chuỗi, vượt thì bỏ tệp rộng trước; chạm thư mục sâu hơn thì nạp thêm tệp của thư mục đó | `context/agent-instructions` |

### 2.2 An toàn và vòng lặp (`packages/sandbox`, `guard`, `goal`, `subagent`)

- **Không có bộ tách/phân loại lệnh shell.** An toàn dựa vào sandbox của hệ điều hành (bwrap/landlock, seatbelt,
  ACL Windows) theo 3 mức `read-only < workspace-write < danger-full-access`; muốn lên mức cao hơn thì model phải xin,
  người dùng duyệt **từng lần**, không nhớ. Không tìm được sandbox thì báo lỗi, **không bao giờ** chạy trần.
- Nhận biết «bị sandbox chặn» sau khi chạy: so stderr với mẫu (`Access is denied`, `operation not permitted`…), rồi
  nhắc model «chạy lại đúng lệnh này một lần kèm xin quyền», tách bạch với lỗi thật của tác vụ.
- **Cảm biến lặp:** khoá = tên công cụ + tham số JSON đã sắp khoá; đếm lượt giống hệt liên tiếp; ngưỡng `[3, 5, 8]`,
  lần đầu nhắc nhẹ, các lần sau nhắc chi tiết; **xoá đếm khi người dùng nhắn tin mới**; chỉ nhắc, không chặn
  (`guard/repeat-tool-reminder/src/index.ts:53`).
- **Goal:** không có trọng tài kiểm «xong». Model tự báo xong, nhưng bị rào: chỉ được báo «bế tắc» sau ≥ 3 vòng
  (`blockedAfterConsecutiveRounds`) — «khó, chưa chắc, còn việc» không phải bế tắc; báo xong thì phải viết một lời kết
  «chỉ nói điều mà kết quả công cụ đã chứng minh», không gọi thêm công cụ.
- **Subagent:** sâu tối đa 1 tầng, 8 cái chạy cùng lúc; thao tác cần duyệt bị tự từ chối; con được dặn «cha không
  thấy transcript của con — đưa kết quả và bằng chứng vào câu trả lời cuối».

### 2.3 Quy trình tri thức (`AGENTS.md`, `.agents/`, `docs/`)

- `AGENTS.md` gốc là **trạm trỏ**: mỗi luật một câu mệnh lệnh + liên kết tới nơi giữ lý do. `CLAUDE.md` là symlink
  tới `AGENTS.md` — một nguồn duy nhất. Có **cổng đếm từ** (`doc-budgets.manifest.json`, trần ~2.080 từ): ngắn là
  thuộc tính được kiểm, không phải mong muốn.
- **Agent Notes** — sổ quyết định: thư mục mã hoá trạng thái (`proposed/implemented/rejected/archived`), dòng
  `Status: … — lý do`, mục **«Alternatives considered» bắt buộc** để không ai đề xuất lại cái đã bị loại. Ghi chú
  bác bỏ chỉ giữ khi ý tưởng đó vẫn còn hấp dẫn; ghi chú lưu trữ bị khoá bằng hash.
- **Postmortem:** chỉ viết khi lỗi tinh vi, có tính hệ thống, tốn công tìm lại; có mục **«Vì sao mọi kiểm tra đều
  sót»** và **«Rào chắn đã thêm»** (test/cảm biến được chứng minh là fail khi lỗi quay lại). Bài học → trang
  defensive-patterns (lớp lỗi + «điều kiện phán xét» mà người duyệt kiểm được) → một dòng trỏ trong AGENTS.md →
  script kiểm nếu máy làm được.
- Skill đáng chú ý: `dsh-trim-cot-leakage` (phép thử: «người đọc ở HEAD, không có transcript, có hiểu mọi tham chiếu
  và kiểm được mọi khẳng định không?»), `dsh-ci-test-reliability` (danh sách cấm che lỗi test chập chờn: tăng timeout,
  thêm retry, sleep, nuốt lỗi), `dsh-pre-push-checks` (chọn kiểm hẹp nhất cho từng phần đã đổi; không chạy lại kiểm
  đã pass chỉ vì sắp commit; chỉ báo lệnh đã thật sự chạy).

## 3. Đối chiếu

| Chủ đề | DSH | Harness hiện tại | Kết luận |
| --- | --- | --- | --- |
| Lệnh phá huỷ | không tách lệnh, dựa sandbox OS | `phan_tich_lenh` tách bằng shlex, đệ quy `bash -c`, bắt `\| sh` | **mình hơn** — giữ |
| Đọc lại tệp chưa đổi | không có | cổng `doc-lai` theo mtime, đếm lại sau nén | **mình hơn** — giữ |
| Ngắt mạch thất bại | không có (chỉ cảm biến lặp) | §7 dừng ở lần 2 | **mình chặt hơn** — giữ |
| Mốc ngữ cảnh | ≈160K/200K, tự nén | 170K, hỏi người dùng | tương đương — giữ |
| Cất output lớn ra tệp | plugin spill | Claude Code tự làm | **bỏ** |
| Khuôn tóm tắt khi nén | 8 mục, gộp bản cũ | không có (dựa mặc định Claude Code) | **lấy** (A) |
| Cảm biến lặp | 3/5/8, xoá khi người dùng nhắn | 5, một lần mỗi khoá mỗi phiên | lấy một phần (H) |
| Nhận biết sandbox chặn | có | không (§14 chỉ ghi bẫy bằng chữ) | **lấy** (G) |
| Rào «báo xong» | chỉ nói điều công cụ chứng minh | cổng Stop đòi skill xác minh | thêm cổng khuôn báo cáo (F) |
| Sổ quyết định | Agent Notes + «phương án đã cân nhắc» | «đã chốt» trong nhật ký | **lấy** bản gọn (B) |
| Bài học → luật | postmortem → pattern → trỏ → script | thang thăng cấp §13 | đã có; thêm 2 trường (C) |
| Độ dài luật | cổng đếm từ | rút gọn tay (22/11) | **lấy** (E) |

Không lấy: token meter (mình đọc số thật từ transcript), sandbox ACL tự viết, thang chế độ quyền (Claude Code đã có
permission mode), vòng goal tự lái, i18n yaml (không song ngữ), hệ điểm duyệt PR.

## 4. Đề xuất chỉnh sửa (xếp theo giá trị / chi phí)

### Nhóm 1 — chỉ sửa chữ trong luật (rẻ, không rủi ro)

**A. Khuôn tóm tắt khi nén** — thêm vào `codevstdio/CLAUDE.md` một mục ngắn (~60 từ):

```
## Khi nén ngữ cảnh
Tóm tắt đủ 8 mục, mục trống ghi «(không)»: Yêu cầu & ý định · Khái niệm kỹ thuật · Tệp & mã (đường dẫn: vì sao,
đã đổi gì) · Lỗi & cách sửa · Việc đang chờ · Việc đang làm · Bước tiếp · Ngữ cảnh then chốt. Giữ nguyên văn
đường dẫn, lệnh, chuỗi lỗi, con số; ghi đúng lời người dùng sửa; có bản tóm tắt cũ thì gộp, bỏ điều đã cũ.
```

Để làm gì: sau nén hay mất đúng những thứ đắt nhất (chuỗi lỗi nguyên văn, lời người dùng sửa, bước tiếp).
Kiểm: chạy `/compact` một phiên thử, xem bản tóm tắt có đủ 8 mục. **Chưa kiểm chứng** Claude Code có đọc mục này
khi tự nén hay chỉ khi `/compact` — phải thử trước khi tin.

**B. Sổ quyết định bản gọn** — §13 (`13-vong-lap-tu-hoc.md`), dòng «Khuôn»: đổi «đã chốt gì» thành «đã chốt gì
**+ phương án đã loại và vì sao**». Thêm một câu: quyết định còn hiệu lực lâu dài → `docs/knowledge/quyet_dinh/
<YYYY-MM-DD>-<chu-de>.md`, dòng đầu `Trạng thái: đề xuất | đã làm | bác bỏ — <lý do một dòng>`, các mục Vấn đề ·
Quyết định · Phương án đã cân nhắc · Hệ quả. Một thư mục + dòng trạng thái thay cho 4 thư mục của DSH. Ghi chú bác bỏ
chỉ giữ khi ý tưởng còn hấp dẫn. Để làm gì: phiên sau không đề xuất lại cái đã bị loại (§13 đã nêu đúng nỗi đau
này nhưng chưa có chỗ chứa).

**C. Khuôn lỗi có rào chắn** — §13 dòng «Khuôn»: «triệu chứng → nguyên nhân → cách sửa → vì sao đúng» thêm
«**→ vì sao kiểm tra không bắt được → rào chắn đã thêm**» (test fail khi lỗi quay lại, hoặc cảm biến). Để làm gì:
nối thẳng vào bậc «kiểm được bằng máy → đề xuất cảm biến» của thang thăng cấp.

**D. Phép thử bàn giao «không có transcript»** — thêm vào §13 một dòng: trước khi ghi `nhat_ky/` / `trang_thai.md`,
hỏi: người mở phiên mới, không có lịch sử chat, có hiểu mọi tham chiếu và kiểm được mọi khẳng định không? Bỏ «như đã
bàn», «cách trên», «bản cũ», lời kể «đã thử X rồi Y» — viết lại thành sự thật hiện tại. Để làm gì: bàn giao là thứ
duy nhất sống qua phiên; câu trỏ vào chat cũ là câu vô nghĩa.

**I. Ba nửa dòng nhỏ:**
- §7: thêm «không che lỗi test chập chờn bằng tăng timeout, thêm retry, `sleep`, nuốt lỗi».
- §5 hàng VERIFY: «chọn kiểm hẹp nhất cho phần đã đổi; không chạy lại kiểm vừa pass chỉ vì sắp commit; báo đúng lệnh
  đã chạy».
- §11 gạch «Model»: brief giao subagent luôn có «cha không thấy transcript của con — trả kết quả kèm bằng chứng
  (tệp:dòng, lệnh, số liệu) trong câu trả lời cuối; thao tác bị từ chối thì không thử lại, nêu giới hạn».

### Nhóm 2 — sửa `harness.py` (TDD, thêm ca vào `tu-kiem-bat-buoc`)

**E. Cổng trần từ cho luật nạp sẵn** — trong `tu_kiem_bat_buoc`: đếm từ của `CLAUDE.md` + các tệp luật được `@`
nạp (bỏ §12, §13 nạp theo đường dẫn); vượt `TRAN_TU_LUAT` thì báo hỏng. Đặt trần = số đo hôm nay + 5%. Muốn nâng trần
phải sửa hằng số kèm lý do. ~10 dòng. Để làm gì: giữ thành quả rút gọn 22/11, luật không phình lại âm thầm.

**F. Cổng Stop kiểm khuôn báo cáo §8** — trong `ket_phien`: phiên đã ghi tệp dự án mà tin nhắn cuối của agent không
có nhãn nào trong 6 nhãn §8 (`ĐÃ KIỂM CHỨNG`, `CHƯA KIỂM CHỨNG`, …) → giữ lượt **một lần**. Đọc tin nhắn cuối giống
cách `prompt_cuoi` đọc transcript. ~15 dòng, thêm `"bao-cao"` vào `CONG_TAT_DUOC`. Để làm gì: tương tự lời kết bắt
buộc của DSH — «xong» phải đi kèm phân loại đã kiểm / chưa kiểm.

**G. Cảm biến «bị sandbox chặn»** — trong `sau_cong_cu`, sự kiện `PostToolUseFailure` của Bash/PowerShell: lỗi khớp
`Access is denied|Operation not permitted|EPERM|sandbox` → chèn nhắc: «nhiều khả năng sandbox chặn, không phải lỗi
mã: đừng đổi lệnh vòng vèo; báo người dùng hoặc xin chạy ngoài sandbox kèm lý do», và **không tính** lượt này vào
ngắt mạch §7. ~10 dòng. Để làm gì: §14 ghi bẫy sandbox bằng chữ; đây là bậc «kiểm được bằng máy → cảm biến» của chính
thang §13. Cần kiểm trước: đầu vào `PostToolUseFailure` có trường chứa stderr không.

**H. Cảm biến lặp hai bậc** — giữ ngưỡng 5 (đã đo: 3 báo nhầm), thêm bậc 8 với thông điệp chi tiết (tên công cụ,
số lần, 200 ký tự tham số, «đừng gọi lại đúng tham số này»). Bỏ phần «xoá đếm khi người dùng nhắn» vì harness chưa
ghi sự kiện prompt vào vết — thêm khi có hook `UserPromptSubmit`. ~5 dòng. Giá trị thấp nhất nhóm.

### Không cần mã

**J. Một nguồn cho AGENTS.md** — trong mỗi repo dưới `D:\codevstdio\repo\`, tạo `CLAUDE.md` chỉ chứa `@AGENTS.md`.
Claude Code sẽ tự nạp AGENTS.md (cả tệp lồng nhau khi chạm thư mục con) thay vì phải tự đọc ở bước LOAD_CONTEXT; dòng
nhắc «có AGENTS.md — đọc trước» trong `bat_dau` khi đó có thể bỏ. Chi phí token không đổi (đằng nào cũng đọc), bớt
một lượt gọi mỗi phiên. Đụng nhiều repo → cần người dùng duyệt từng repo.

## 5. Thứ tự đề nghị

1. Nhóm 1 (A–D, I) — một lần sửa chữ, rà diff, một commit.
2. E, F — có ca tự kiểm.
3. G — sau khi xác nhận trường stderr trong đầu vào hook.
4. J, H — tuỳ người dùng.
