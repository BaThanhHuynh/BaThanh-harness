# Gói 1 — đo cổng, tắt từng cổng, bắt vòng lặp, tách lệnh shell

Ngày 16/11/2026 · nguồn ý tưởng: `D:\codevstdio\docs\knowledge\tham-khao-ecc.md` · cỡ: thay đổi nhỏ, một tệp `harness.py`.

## Vì sao

- Cổng chặn lệnh phá huỷ dò regex trên chuỗi thô. Đã kiểm 16/11: lọt `git -C repo push`, `git --no-pager push`,
  `git -c x=1 reset --hard`; hỏi thừa `echo "rm -rf …"`, `grep -n "git push" …`.
- Cổng quy trình (`superpowers`, giữ lượt ở `Stop`) chưa từng được đo. ECC đo cổng cùng dạng: tốn thêm 37–45% lượt,
  lợi ích chưa chứng minh (p = 0,21). Muốn biết cổng của mình đáng giữ không thì phải có số.
- Vòng lặp chỉ bắt khi lệnh **thất bại** lặp lại; lặp lệnh thành công (đọc lại cùng đoạn, chạy lại cùng lệnh) lọt.

## Mục tiêu · không làm · phản mục tiêu

- Mục tiêu: 5 ca lỗi ở trên cho kết quả đúng; mỗi lần cổng bắn có một dòng vết; một lệnh tay in bảng số lần bắn;
  tắt được từng cổng quy trình mà vẫn ghi «lẽ ra đã bắn»; bắt 5 lượt gọi giống hệt liền nhau.
- Không làm: đo **lợi ích** của cổng (cần nhiều phiên nhánh tắt/bật — để sau khi có số); đếm lượt vòng cho cổng `Stop`;
  bắt đọc lại tệp không liền nhau; port bộ quét 1.800 dòng của ECC.
- Phản mục tiêu: lệnh phá huỷ nào hôm nay bị hỏi mà sau thay đổi lọt; tắt được cổng an ninh bằng biến môi trường;
  hook lỗi làm hỏng phiên (vẫn fail-open).

## Các cách đã cân nhắc

| Cách | Được | Mất | Chọn |
| --- | --- | --- | --- |
| Gói 1: cả bốn phần dưới | vá lỗ + có số để quyết giữ/bỏ cổng | ~100 dòng | ✅ người dùng chọn 16/11 |
| Gói 2: chỉ tách lệnh + vòng lặp | nhỏ nhất | vẫn không biết cổng tốn bao nhiêu | |
| Gói 3: Gói 1 + `thang-cap` + khoá tệp chốt | thêm hỗ trợ §13 | thêm ~55 dòng chưa ai đòi | |

## Thiết kế

**(D) Tách lệnh shell** — hàm mới `phan_tich_lenh(lenh)`, thư viện chuẩn `shlex`:
- Thay xuống dòng bằng `;`, tách từ bằng `shlex` (`punctuation_chars=";&|"`, tắt thoát `\` để giữ đường dẫn Windows).
  Token chỉ gồm `; & |` là ranh giới đoạn.
- Mỗi đoạn: gặp token `git`/`git.exe` thì bỏ các tuỳ chọn toàn cục ngay sau nó (`-C`, `-c`, `--git-dir`, `--work-tree`,
  `--namespace` ăn thêm một token; tuỳ chọn khác bắt đầu bằng `-` ăn một). Dò `LENH_PHA_HUY` trên đoạn đã chuẩn hoá.
- Đoạn mở đầu bằng lệnh dữ liệu (`echo`, `printf`, `grep`, `rg`, `findstr`, `Select-String`, `Write-Output`, `Write-Host`)
  thì bỏ qua — **trừ khi** có token chứa `(` hoặc `` ` `` (thay lệnh `$(…)`, nhóm lệnh PowerShell).
- `bash|sh|cmd|powershell|pwsh -c|-Command|/c "<lệnh>"`: phân tích đệ quy chuỗi lệnh bên trong.
- `shlex` báo lỗi (ngoặc không đóng) → quay về regex trên chuỗi thô như hôm nay (thận trọng: thà hỏi thừa).
- Hai luật về `.env` và luật `pip install` vẫn dò trên chuỗi thô: chúng nói về tệp đích, hỏi thừa còn hơn sót.

**(A) Ghi vết cổng + lệnh `do-cong`**:
- Hàm mới `ghi_cong(vao, cong, quyet)` ghi `{"loai": "cong", "cong": <tên>, "quyet": ask|deny|block|tat, "tom_tat": …}`.
  `quyet_dinh` nhận thêm `vao` và tên cổng, gọi `ghi_cong` trước khi in. Hai chỗ giữ lượt ở `ket_phien` cũng gọi.
- Tên cổng: `bi-mat-doc`, `bi-mat-ghi`, `pha-huy`, `superpowers`, `doc-lon`, `ngu-canh`, `xac-minh`, `ban-giao`.
- `harness.py do-cong`: quét `vet/phien/*.jsonl`, mỗi cổng một dòng: số lần bắn · số phiên bị bắn / tổng phiên ·
  số lần ghi «tắt» · số lần sau đó chính lệnh/tệp ấy chạy được · trung vị số lượt gọi từ lúc bắn đến lúc chạy được.
  Cổng `ask` chạy được ngay = người dùng duyệt. Cổng `Stop` không có `tom_tat` → hai cột cuối để «—».
- Vết cũ (164 phiên) không có dòng cổng → số bắt đầu từ 0, tích luỹ từ ngày triển khai.

**(H) Tắt từng cổng** — biến môi trường `HARNESS_TAT=superpowers,doc-lon` (đặt ở khối `env` của
`~/.claude/settings.json`, mở phiên mới):
- Chỉ tắt được cổng quy trình: `superpowers`, `doc-lon`, `ngu-canh`, `xac-minh`, `ban-giao`. Ba cổng an ninh
  (`bi-mat-*`, `pha-huy`) bỏ qua biến này.
- Cổng tắt vẫn ghi vết `quyet: "tat"` rồi cho qua, và trả `False` để cổng sau trong chuỗi `canh_cong` vẫn được xét.

**(B) Dây ngắt vòng lặp**:
- Mỗi dòng vết `goi` thêm `ky` = 12 ký tự đầu SHA-1 của tên công cụ + tham số (JSON sắp khoá) — đọc cùng tệp khác
  `offset` là hai chữ ký khác nhau, không báo nhầm.
- 5 lượt liền nhau cùng `ky` (`NGUONG_LAP = 5`, ngưỡng ECC sau khi 3 báo nhầm) → nhắc mềm §7/§11, mỗi chữ ký một lần.

## Kiểm chứng (thêm vào `tu-kiem-bat-buoc`, viết trước khi sửa mã)

- Tách lệnh: 5 ca lỗi trên; `git push`, `git reset --hard`, `rm -rf x` vẫn hỏi; `git -C repo status` không hỏi;
  `bash -c "git -C r push"` hỏi; `echo $(git push)` hỏi; `cat .env` và `echo x > .env` vẫn hỏi; ngoặc không đóng → regex cũ.
- Hook thật: cổng `superpowers` bắn → vết có dòng `cong`; `HARNESS_TAT=superpowers` → không in gì, vết có `tat`;
  `HARNESS_TAT=pha-huy` → `git push` vẫn hỏi.
- Vòng lặp: 5 lượt `sau-cong-cu` giống hệt → lượt 5 có cảnh báo; 5 lượt khác `offset` → không.
- `do-cong` chạy, in dòng `superpowers` cho phiên giả.
- Chạy `tu-kiem-bat-buoc` toàn bộ trước và sau: phần cũ vẫn đạt.

## Sẽ sửa · có thể ảnh hưởng · không đụng tới

- Sẽ sửa: `~/.claude/harness/harness.py`; `README.md` (bảng lệnh, giới hạn đã biết); `VAN-HANH.md` (lịch sử thay đổi).
- Có thể ảnh hưởng: mọi phiên đang chạy (hook đọc `harness.py` mỗi lượt gọi) — lỗi cú pháp thì fail-open, nhưng cổng
  ngừng chắn đến khi sửa; nên sửa xong chạy `tu-kiem-bat-buoc` ngay.
- Không đụng tới: `settings.json` (lớp quyền native — xem dưới), hợp đồng `CLAUDE.md` và rules, không commit.

## Để người làm tự quyết

- Tên biến, vị trí hàm trong tệp, định dạng bảng `do-cong`.
- **Tách riêng, cần duyệt riêng:** thêm dạng `git -C * push` vào `permissions.ask` native. Chưa biết native có khớp
  `*` ở giữa không; kiểm cần chạy thật `git -C <repo tạm không remote> push` và bạn bấm duyệt. Làm sau, nếu bạn muốn.
