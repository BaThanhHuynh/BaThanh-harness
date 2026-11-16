# Gói 1 — đo cổng, tắt từng cổng, bắt vòng lặp, tách lệnh — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vá lỗ cổng lệnh phá huỷ, ghi vết + đo mọi cổng, tắt được từng cổng quy trình, bắt 5 lượt gọi giống hệt.

**Architecture:** Mọi thay đổi trong `harness.py` (một tệp stdlib). Test là `tu_kiem_bat_buoc()` trong chính tệp, chạy hook
thật bằng subprocess. Viết assert trước, chạy thấy hỏng, rồi mới sửa mã.

**Tech Stack:** Python 3.14 stdlib (`shlex`, `hashlib`, `statistics`).

**Spec:** `docs/superpowers/specs/2026-11-16-goi-1-do-cong-tach-lenh-design.md`

## Global Constraints

- Fail-open giữ nguyên: lỗi trong hook vào `vet/loi.log`, thoát 0. Lệnh chạy tay (`do-cong`) thì raise.
- Không phụ thuộc ngoài. Không commit (người dùng chưa cho phép). Không sửa `settings.json`.
- Cổng an ninh `bi-mat-doc`, `bi-mat-ghi`, `pha-huy` không tắt được bằng `HARNESS_TAT`.
- Lệnh kiểm mọi task: `python ~/.claude/harness/harness.py tu-kiem-bat-buoc` → in `tự kiểm bắt buộc: đạt.`

## Review Focus

- Đường dẫn Windows có `\` trong lệnh PowerShell (`Remove-Item -Recurse D:\x\y`) vẫn phải hỏi — test ở Task 1.
- `git.exe` gọi bằng đường dẫn đầy đủ trong ngoặc kép kèm `-C` vẫn phải hỏi — test ở Task 1.
- `2>&1` cắt đoạn ở `&`; `git -C r push 2>&1` vẫn phải hỏi — test ở Task 1.
- `HARNESS_TAT` có dấu cách (`"doc-lon, superpowers"`) vẫn tắt đúng — test ở Task 2.
- 164 tệp vết cũ không có dòng `cong` / trường `ky`: `do-cong` chạy qua không lỗi — test ở Task 3 (chạy trên vết thật).

---

### Task 1: Tách lệnh shell (D)

**Files:** Modify `harness.py:54-70` (hằng), `harness.py:223-230` (`cong_quyen`), `harness.py:846+` (test).

**Interfaces:** Produces `phan_tich_lenh(lenh: str) -> list[str]` — nhãn `LENH_PHA_HUY` khớp, không trùng, giữ thứ tự.

- [ ] **Step 1: Viết test** ở đầu khối «Hàm thuần» của `tu_kiem_bat_buoc`:

```python
hoi = ["git -C repo push", "git --no-pager push origin main", "git -c core.x=1 reset --hard", "git push",
       "rm -rf x", 'bash -c "git -C r push"', "echo $(git push)", 'echo "a" && git -C r push 2>&1',
       r"Remove-Item -Recurse D:\x\y", '"C:/Program Files/Git/cmd/git.exe" -C r push', "git add .\ngit push",
       'git push "x']  # ca cuối: ngoặc không đóng -> regex cũ
for s in hoi:
    assert phan_tich_lenh(s), f"lọt lệnh phá huỷ: {s!r}"
for s in ['echo "rm -rf la lenh nguy hiem"', 'grep -n "git push" README.md', "git -C repo status"]:
    assert not phan_tich_lenh(s), f"hỏi thừa: {s!r}"
```

  và ở **đầu** khối «Cổng qua hook thật» (Task 2 dùng lại `lenh`, nên phải định nghĩa trước dòng 884):

```python
lenh = lambda c: {"tool_name": "Bash", "tool_input": {"command": c}}
assert "ghi vào .env" in chay("canh-cong", **lenh("echo x > .env")), "sót ghi .env"
assert "in .env" in chay("canh-cong", **lenh("cat .env")), "sót in .env"
```

- [ ] **Step 2: Chạy** lệnh kiểm → hỏng với `NameError: phan_tich_lenh`.
- [ ] **Step 3: Sửa mã.** Tách hai luật `.env` khỏi `LENH_PHA_HUY` thành `LENH_TEP_ENV` (dò chuỗi thô). Thêm `LENH_DU_LIEU`
  (`echo printf grep rg findstr select-string write-output write-host`, so chữ thường, bỏ `.exe`), `GIT_AN_THAM_SO`
  (`-C -c --git-dir --work-tree --namespace`), vỏ shell `bash sh cmd powershell pwsh` với cờ `-c -command /c`.
  `phan_tich_lenh` theo đúng mục (D) của spec; `shlex.shlex(..., posix=True, punctuation_chars=";&|")`,
  `whitespace_split=True`, `escape=""`; `ValueError` → `[n for m, n in LENH_PHA_HUY if m.search(lenh)]`.
  `cong_quyen`: `ly_do = phan_tich_lenh(lenh) + [n for m, n in LENH_TEP_ENV if m.search(lenh)]`, luật pip giữ nguyên.
- [ ] **Step 4: Chạy** lệnh kiểm → `đạt`.

### Task 2: Ghi vết cổng + tắt từng cổng (A, H)

**Files:** Modify `harness.py:200-272` (cổng), `harness.py:470-490` (`ket_phien`), test.

**Interfaces:** Produces `CONG_TAT_DUOC = ("superpowers", "doc-lon", "ngu-canh", "xac-minh", "ban-giao")`,
`ghi_cong(vao: dict, cong: str, quyet: str) -> bool` (False = cổng đang tắt), `quyet_dinh(vao, cong, loai, ly_do) -> bool`.
Dòng vết: `{"t", "loai": "cong", "cong", "quyet": "ask"|"deny"|"block"|"tat", "tom_tat"}`.

- [ ] **Step 1: Viết test.** `chay` nhận thêm `_env: dict | None = None`, gộp vào `os.environ` cho subprocess. Ngay sau
  assert «chưa gọi superpowers mà ghi tệp dự án vẫn lọt»:

```python
cong = lambda ten, q: any(b.get("loai") == "cong" and b.get("cong") == ten and b.get("quyet") == q for b in doc_vet(sid))
assert cong("superpowers", "deny"), "cổng bắn mà không ghi vết"
assert chay("canh-cong", _env={"HARNESS_TAT": "doc-lon, superpowers"}, **ghi(du_an)) == "", "tắt cổng mà vẫn chặn"
assert cong("superpowers", "tat"), "cổng tắt mà không ghi «lẽ ra đã bắn»"
assert '"ask"' in chay("canh-cong", _env={"HARNESS_TAT": "pha-huy"}, **lenh("git push")), "tắt được cổng an ninh"
```

  và sau assert «thiếu verification + bàn giao mà không giữ gộp một lần»:
  `assert cong("xac-minh", "block") and cong("ban-giao", "block"), "giữ lượt ở Stop mà không ghi vết"`.
- [ ] **Step 2: Chạy** → hỏng ở `cổng bắn mà không ghi vết`.
- [ ] **Step 3: Sửa mã.** `HARNESS_TAT` tách theo `,`, bỏ khoảng trắng. Sáu chỗ gọi `quyet_dinh` thêm `vao` + tên cổng
  (spec mục A) và `return quyet_dinh(...)` để cổng tắt trả False. `ket_phien`: sau khi tính `chan` → `if chan and not
  ghi_cong(vao, "xac-minh", "block"): chan = 0`; sau khi cập nhật `ban_giao_luc` → tương tự cho `repo_no` / `ban-giao`.
- [ ] **Step 4: Chạy** → `đạt`.

### Task 3: Lệnh `do-cong` (A)

**Files:** Modify `harness.py` — thêm `do_cong()` cạnh `bao_cao`, đăng ký `"do-cong"` trong `LENH` và danh sách raise ở `main`.

**Interfaces:** Consumes dòng vết `cong` của Task 2.

- [ ] **Step 1: Viết test** cuối khối hook: `assert "superpowers" in chay("do-cong"), "do-cong không thấy cổng của phiên giả"`.
- [ ] **Step 2: Chạy** → hỏng (`chay` raise vì lệnh không tồn tại, mã 1).
- [ ] **Step 3: Sửa mã.** Mỗi tệp `vet/phien/*.jsonl`, theo thứ tự dòng: mỗi dòng `cong` có `quyet != "tat"` và `tom_tat`
  khác rỗng → tìm dòng `goi` đầu tiên sau nó cùng `tom_tat`, `ok` → «qua», số dòng `goi` ở giữa = lượt vòng.
  In mỗi cổng: bắn · phiên bị bắn/tổng phiên · tắt · qua · trung vị lượt vòng (`statistics.median`, không có → `—`).
- [ ] **Step 4: Chạy** → `đạt` (đồng thời chạy qua 164 tệp vết thật không lỗi).

### Task 4: Dây ngắt vòng lặp (B)

**Files:** Modify `harness.py:303-361` (`sau_cong_cu`), hằng `NGUONG_LAP = 5` cạnh `NGUONG_THAT_BAI`, test.

- [ ] **Step 1: Viết test** cuối khối hook:

```python
doc_lai = lambda **ts: {"tool_name": "Read", "tool_input": {"file_path": du_an, **ts}}
o = [chay("sau-cong-cu", **doc_lai()) for _ in range(5)]
assert "vòng lặp" not in o[3] and "vòng lặp" in o[4], "5 lượt giống hệt mà không cảnh báo"
assert not any("vòng lặp" in chay("sau-cong-cu", **doc_lai(offset=i)) for i in range(5)), "khác offset mà báo lặp"
```

- [ ] **Step 2: Chạy** → hỏng ở `5 lượt giống hệt mà không cảnh báo`.
- [ ] **Step 3: Sửa mã.** `ban_ghi["ky"]` = `sha1(ten + json.dumps(tham_so, sort_keys=True, ensure_ascii=False, default=str))[:12]`.
  Đưa `da_ban` ra trước các dây ngắt. 5 `ky` cuối (kể cả lượt này) giống nhau và `f"lap-{ky}"` chưa bắn → cảnh báo
  chứa «vòng lặp», nhắc §7 (đổi cách hoặc báo người dùng) và §11 (đừng đọc lại tệp chưa đổi).
- [ ] **Step 4: Chạy** → `đạt`.

### Task 5: Tài liệu

**Files:** Modify `README.md` (bảng lệnh: `do-cong`; hàng «3. Vòng lặp»: thêm 5 lượt giống hệt; «Giới hạn đã biết»: cổng
tách lệnh bằng `shlex`, ngoặc không đóng thì quay về regex), `VAN-HANH.md` (một mục lịch sử 16/11/2026 + cách dùng `HARNESS_TAT`).

- [ ] **Step 1:** Sửa hai tệp. **Step 2:** chạy lệnh kiểm lần cuối → `đạt`; `git -C ~/.claude/harness diff --stat` chỉ có
  `harness.py`, `README.md`, `VAN-HANH.md` + hai tệp `docs/superpowers/`.
