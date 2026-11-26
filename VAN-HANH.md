# Vận hành harness — ghi chú nội bộ (giới thiệu: `README.md`)

Dựng lại ngày 10/09/2026, sau khi `~/.claude/harness/` mất trong đợt chuyển máy từ user `adc` sang `dell`.
**Hợp đồng bằng văn bản** vẫn là `D:\codevstdio\CLAUDE.md` cùng `.claude/rules/01–14`. Thư mục này là
**phần runtime**: hook, vết phiên, bảng định tuyến — những thứ cưỡng chế được mà văn bản không tự làm được.

## Bản đồ 6 tầng

| Tầng | Trong kiến trúc gốc | Ở máy này | Cưỡng chế bằng |
| --- | --- | --- | --- |
| 1 Guides | AGENTS.md, rule files, constraints | `CLAUDE.md` + 16 rule · `<repo>/AGENTS.md` · `DINH-TUYEN.md` · `NHAC-DINH-TUYEN.md` | CLAUDE.md chỉ được nạp khi cwd nằm dưới `D:\codevstdio`; hook `SessionStart` chèn bản nhắc **chỉ khi cwd nằm ngoài** (11/10 — trước đó chèn trùng ở mọi phiên) |
| 2 Sensors | linters, tests, validators, LLM-as-judge | Cảm biến cú pháp `.py` (compile) và `.json`/`.ipynb` (parse, bắt cả BOM — §14) sau mỗi Edit/Write | `PostToolUse` → `decision: block`, lỗi đưa thẳng về agent |
| 3 Agentic loop | plan → execute → verify → fix, retry có giới hạn, trần ngân sách, leo thang | §5 vòng đời, §7 ngắt mạch, §11 trần phiên | Dây ngắt mềm: cùng một lệnh thất bại ≥ 2 lần · mốc **60/120/200** lượt gọi · ngữ cảnh 150K token mỗi lượt · sang tệp thứ 13. **Hộp duyệt** (`PreToolUse` → `ask`, một lần mỗi mốc): ngữ cảnh **170K** token mỗi lượt (bỏ 300K ngày 15/11, hạ 200K → 170K ngày 22/11: autoCompactWindow 200K nên nén trước khi chạm 200K). `PreCompact` ghi tổng kết, `bat-dau` sau nén chèn lại việc dở của chính phiên |
| 4 Memory | state files, artifacts, decision log | `<repo>/AGENTS.md`, `docs/knowledge/`, nhật ký phiên của repo · `vet/tong-ket/` | `SessionStart` chèn mục «Tiếp theo» của `trang_thai.md` + tóm tắt phiên trước ở cùng thư mục · `Stop` giữ lượt một lần đòi bàn giao §13 · `harness.py tim` |
| 5 Permissions | tool access, write limits, approval gates | §9 danh sách cấm cứng · §10 bí mật | `PreToolUse`: lệnh phá huỷ → `ask` · sửa tệp bí mật → `deny` · đọc tệp bí mật → `ask` |
| 6 Observability | trace logs, cost tracking, trip wires | `vet/phien/<session>.jsonl` · `vet/tong-ket/<session>.json` (token đọc từ transcript) | `PostToolUse` / `PostToolUseFailure` / `Stop` · `harness.py bao-cao` |

## Đánh giá khả thi (10/09/2026, Claude Code 2.1.260)

**Khả thi.** Cả sáu tầng đều có cơ chế tương ứng trong Claude Code, và hook đã được kiểm chạy thật trong
phiên dựng lại. Những giới hạn đã chấp nhận:

- **LLM-as-judge không tự động.** Chạy mỗi lượt thì tốn token và ồn. Chỉ gọi khi cần, qua skill review ở bước REVIEW_DIFF (`DINH-TUYEN.md`).
- **Cảm biến chỉ kiểm cú pháp.** Không có bộ test chung cho mọi repo. Kiểm chứng ngữ nghĩa vẫn theo `AGENTS.md`
  của từng repo (với CredX: chạy lại chuỗi dựng số).
- **Ngân sách không chặn cứng.** Chặn giữa chừng để lại việc dở dang. Từ 11/10 mốc 200K (300K bỏ 15/11, 200K → 170K ngày 22/11) chuyển thành hộp duyệt:
  nhắc mềm bị bỏ qua ở cả 5 phiên trước đó, nên quyết định được đưa cho người dùng — người thấy chi phí.
- **Chi phí chỉ đếm bằng token** (vào / cache ghi / cache đọc / ra), không quy ra tiền. Bảng giá thay đổi theo thời gian nên không hardcode.
- **Cổng quyền dựa trên regex.** Có thể hỏi thừa (ví dụ `echo "rm -rf"`) và bỏ sót lệnh được ngụy trang.
  Hệ thống quyền của chính Claude Code vẫn là lớp chắn chính.
- **Hook không đọc được phạm vi «Sẽ sửa» công bố ở bước PLAN** (đó là văn bản), nên dây ngắt phạm vi chỉ đếm số tệp.
- **Độ dễ hiểu của câu trả lời (§15) không có cảm biến tự động.** Máy khó đo «dễ hiểu» mà không báo nhầm,
  và bắt agent viết lại mỗi lượt thì tốn kém. Quy tắc nằm ở tầng Guides: luật 15 cộng một dòng trong bản nhắc đầu phiên.

## Tệp

| Tệp | Vai trò |
| --- | --- |
| `harness.py` | Engine. Hook: `bat-dau` · `canh-cong` · `sau-cong-cu` · `ket-phien` · `truoc-nen`. Chạy tay: `quet` · `bao-cao` · `chi-muc` · `do-ton` · `tim` · `tu-kiem-bat-buoc` |
| `NHAC-DINH-TUYEN.md` | Chèn vào ngữ cảnh mỗi đầu phiên và sau mỗi lần nén. **Giữ ngắn** — nó tốn ngữ cảnh |
| `DINH-TUYEN.md` | Việc X → skill nào (soạn tay) |
| `INVENTORY.md` | Sinh bởi `quet`, không sửa tay |
| `vet/` | Vết và tổng kết phiên. `loi.log` ghi lỗi nội bộ của hook (hook lỗi thì thoát 0, không làm hỏng phiên) |
| `sao-luu/2026-09-10/` | Bản gốc của các tệp đã sửa khi dựng lại |
| `codevstdio/.claude/rules/` | Bản thật của rules hợp đồng; `D:\codevstdio\.claude\rules` là junction trỏ về đây |
| `codevstdio/CLAUDE.md`, `dot-claude/settings.json` | Bản chép, `githooks/pre-commit` làm mới mỗi lần commit |

## Hook đăng ký trong `~/.claude/settings.json`

| Sự kiện | Matcher | Lệnh con |
| --- | --- | --- |
| `SessionStart` | `startup\|resume\|clear\|compact` | `bat-dau` |
| `PreToolUse` | `Bash\|PowerShell\|Read\|Edit\|Write\|MultiEdit\|NotebookEdit` | `canh-cong` |
| `PostToolUse`, `PostToolUseFailure` | `*` | `sau-cong-cu` |
| `Stop` | — | `ket-phien` |
| `PreCompact` | — | `truoc-nen` |

Mỗi hook là một lần khởi động `python` (~0,1 s mỗi lượt gọi công cụ).

## Quota — vì sao tốn và đòn bẩy (đo 11/10/2026)

Nguồn: transcript `~/.claude/projects/*/*.jsonl` từ 01/09 — 45 phiên chính (CredX 33, DART-ICD-10 12).

| Chỉ số | Số đo |
| --- | --- |
| CredX: lượt API · ngữ cảnh gửi lại · trung bình mỗi lượt · sinh ra | 2.808 · 642 triệu · **228.632** · 5,0 triệu token |
| Sàn lượt đầu (phần nạp cố định) | trung vị 90.297; các phiên tháng 10 ~97K token |
| Chuỗi luật tiếng Việt (CLAUDE.md + 16 rule + AGENTS.md CredX, 46 KB) | ~25K token mỗi lượt — tiếng Việt có dấu ≈ 1,9 byte/token (đo: rule 11+13, 9.628 byte ≈ 5.150 token) |
| Quy theo giá tương đối API (cache đọc 0,1× · cache ghi 1,25× · output 5×) | đọc lại ngữ cảnh ~57% · output gồm suy nghĩ ~23% · cache ghi ~20% |
| Skill được gọi | 6 lần / 45 phiên, trong khi ~150 mô tả skill nạp lại mỗi lượt |
| Kết quả công cụ > 20K ký tự | 46 lần, 5,7 triệu ký tự — nằm lại đến hết phiên |
| 5 phiên gần nhất | đều vượt 150K và 250K token mỗi lượt; phiên 07/10: 119 lượt, 3 tệp ghi, 32 triệu token cache đọc |

Bằng chứng cũ: phiên CredX 20/09 — 156 lượt, 285.133 token/lượt, 44,5 triệu token cho ~150K token nội dung thật
(300:1); nguyên nhân 43 `Edit` lẻ và một `Read` 183 KB. Phiên dài còn kém chính xác: Chroma Research «context rot»
(18 model) — độ chính xác tụt khi đầu vào dài ra, trước cả khi chạm giới hạn cửa sổ.

**Đòn bẩy, theo thứ tự hiệu quả:** (1) phiên ngắn + bàn giao bằng tệp — đánh vào phần 57%; (2) effort `high` mặc
định, subagent `haiku`/`sonnet` cho việc rẻ — đánh vào phần 23%; (3) gọn phần nạp cố định (luật, plugin, connector)
— đánh vào sàn ~97K. Đo phiên đang chạy: `harness.py do-ton`; các phiên gần đây: `harness.py bao-cao`.

**Bộ công cụ chốt 11/10** (giữ / bỏ và căn cứ): `DINH-TUYEN.md`. Tắt `claude-mem`, `caveman`, `ponytail`; gỡ `ecc` —
ước giảm ~10K token mỗi lượt. **Người dùng tự tắt trong claude.ai → Cài đặt:** 6 plugin đồng bộ (`legal`, `finance`,
`data`, `productivity`, `engineering`, `cowork-plugin-management`; 17 MCP chờ đăng nhập, `definite` hỏng) và connector
Claude Docs — thêm ~4,6K. Giữ Google Drive (40 lượt dùng). 15/11: `superpowers` + `ponytail` **bắt buộc** khi làm dự án — luật «1%» áp dụng lại cho hai plugin này (§5, §11).
Lưu ý: `claude plugin details` ghi hook là «không tốn ngữ cảnh» — sai với hook `SessionStart` có in `additionalContext`
(caveman, ponytail, superpowers, claude-mem đều in).

## MCP server dùng chung

- 11/10/2026: `~/.claude.json` → `mcpServers` **rỗng** — `playwright` (cài 13/09) không còn. Duyệt web dùng trình
  duyệt tích hợp của app. Cài lại: `cmd /c npx -y @playwright/mcp@latest --output-dir C:/Users/dell/AppData/Local/Temp/playwright-mcp`
  (cờ `--output-dir` để ảnh chụp khỏi rơi vào repo); MCP chỉ nạp ở phiên mới.

## Vận hành

- Xem các phiên gần đây: `python ~/.claude/harness/harness.py bao-cao [số phiên]`
- Tra xuyên dự án (mọi `D:\codevstdio\repo\*\docs\knowledge\**` + `vet/tong-ket/`): `python ~/.claude/harness/harness.py tim <từ khoá> [từ khoá …]`
  — dòng phải chứa mọi từ khoá, không phân biệt hoa thường, tối đa 30 dòng `tệp:dòng: đoạn`.
- Sau khi cài / gỡ plugin: `python ~/.claude/harness/harness.py quet`, rồi soát lại `DINH-TUYEN.md`.
- Chỉnh ngưỡng dây ngắt: sửa các hằng số ở đầu `harness.py`.
- Tắt tạm mọi hook: thêm `"disableAllHooks": true` vào `settings.json`.
- Tắt từng cổng quy trình (để có nhánh «tắt» khi đo): đặt `"HARNESS_TAT": "superpowers,doc-lon"` trong khối `env` của
  `~/.claude/settings.json`, mở phiên mới. Tắt được: `superpowers`, `doc-lon`, `ngu-canh`, `xac-minh`, `ban-giao`; ba
  cổng an ninh (`bi-mat-doc`, `bi-mat-ghi`, `pha-huy`) bỏ qua biến này. Cổng tắt vẫn ghi vết `quyet: "tat"`.
- Xem cổng tốn bao nhiêu: `python ~/.claude/harness/harness.py do-cong`.

## Khôi phục — những gì đã mất và cách lấy lại

- **Sao lưu git (16/11/2026).** Thư mục này là repo git private. Repo public, nên ngoài git: `vet/`, `__pycache__/`,
  `sao-luu/` (bản cũ, có tài liệu dự án khác — chỉ giữ trên máy). Sao lưu: `git -C ~/.claude/harness add -A`, rồi `commit`, rồi `push`.
  Máy mới, theo thứ tự:
  1. `git clone <url repo> ~/.claude/harness` rồi `git -C ~/.claude/harness config core.hooksPath githooks`.
  2. PowerShell: `New-Item -ItemType Junction -Path D:\codevstdio\.claude\rules -Target $HOME\.claude\harness\codevstdio\.claude\rules`.
  3. Chép `codevstdio/CLAUDE.md` sang `D:\codevstdio\`.
  4. Gộp khối `hooks`, `permissions`, `autoMode` từ `dot-claude/settings.json` vào `~/.claude/settings.json`.
  5. `python ~/.claude/harness/harness.py tu-kiem-bat-buoc`.
- **Đường dẫn plugin.** `plugins/installed_plugins.json` và `known_marketplaces.json` từng trỏ vào
  `C:\Users\adc`; đã đổi sang `dell` (bản gốc nằm ở `sao-luu/`). Nếu chuyển máy lần nữa thì làm lại phép thay
  này. `SessionStart` sẽ tự cảnh báo khi một plugin đang bật bị hỏng đường dẫn.
- **13/09: Node.js v24.21.0 đã cài; `ecc` và `claude-mem` đã bật lại** (bản `settings.json` trước khi bật:
  `sao-luu/2026-09-13/settings.json`). Đã chạy THẬT từng hook qua bash với stdin mẫu: `ecc` 12/12 hook mã 0.
  `claude-mem`: người dùng duyệt `npx claude-mem@latest install --provider claude` (chạy không tương tác thì BẮT
  BUỘC có `--provider`, không thì trình cài dừng). Nó cài bun 1.4.2 vào `~/.bun/bin` (không vào PATH của shell — plugin
  tự tìm ở đó), nâng plugin lên v13.24.23, cloud sync TẮT, dữ liệu ở `~/.claude-mem`. Chạy thử lại: hook mã 0, worker
  `http://127.0.0.1:37777` trả 200. Nếu worker không lên: `npx claude-mem start`. Soát tĩnh (đọc chuỗi lệnh) báo nhầm «thiếu tệp» vì hook
  của cả hai tự dò đường dẫn lúc chạy — muốn kết luận phải chạy thử, đừng tin soát tĩnh.
- **16/11: Gói 1 học từ ECC** (`D:\codevstdio\docs\knowledge\tham-khao-ecc.md`; spec + plan ở `docs/superpowers/`).
  Cổng lệnh phá huỷ tách lệnh bằng `shlex` — regex cũ lọt `git -C repo push`, `git --no-pager push`,
  `git -c x=1 reset --hard`, hỏi thừa `echo "rm -rf …"`. Mọi cổng ghi vết `{"loai": "cong"}`; lệnh `do-cong`;
  `HARNESS_TAT` tắt từng cổng quy trình. Dây ngắt vòng lặp: 5 lượt liền cùng `ky` (SHA-1 tên công cụ + tham số).
- **15/11: `superpowers` + `ponytail` bắt buộc khi làm dự án** (người dùng chốt); bật lại `ponytail`. Cổng mới trong
  `harness.py`: `canh-cong` từ chối ghi tệp dự án khi phiên chưa gọi skill `superpowers:*`; `ket-phien` giữ lượt lại một
  lần nếu đã ghi tệp dự án mà chưa gọi `superpowers:verification-before-completion` sau lần ghi cuối; `bat-dau` cảnh báo
  khi plugin bắt buộc bị tắt. Tự kiểm: `harness.py tu-kiem-bat-buoc`. Cùng ngày (quota): Opus effort `xhigh` → `high`,
  `autoCompactWindow` 400K → 200K, `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`. Bản trước khi sửa: `sao-luu/2026-11-15/`.
- **15/11 (quota, đợt 2):** `canh-cong` từ chối `Read` trọn tệp >200 KB không kèm offset/limit; `env`:
  `BASH_MAX_OUTPUT_LENGTH=15000`, `MAX_MCP_OUTPUT_TOKENS=10000`; tắt `mattpocock-skills` (0 lần dùng, trùng superpowers).
  Căn cứ (mọi transcript): Bash ~65%, Read ~23% kết quả công cụ đưa vào ngữ cảnh. Bản trước: `sao-luu/2026-11-15/`.
- **22/11 (rút gọn luật, đợt 1):** phần nạp sẵn `CLAUDE.md` + 13 rule 14.513 → 11.499 byte (~7,6K → ~6,0K token).
  Bỏ chỗ trùng: §2 (ponytail tự nạp), câu mô tả hook ở §5 (hook tự báo), bảng model §11 rút một dòng, BOM /
  `Set-Content` / here-string ở §14 (system prompt + cảm biến BOM), §15 phần output style Concise đã lo; §11 sửa
  trần 200K → 170K. Giữ số §1–16. Kế hoạch `docs/2026-11-22-rut-gon-luat.md`; bản trước
  `sao-luu/2026-11-22/truoc-rut-gon-luat/`. Đợt 2 (`AGENTS.md` từng repo) chưa làm.
- **22/11 (ý từ ECC `context-gate` / `pre-compact`):** hộp duyệt ngữ cảnh 200K → **170K** (vết thật: 200K không bao giờ
  chạm vì autoCompactWindow 200K nén trước); lời nhắc thành mệnh lệnh checkpoint (điểm dừng sạch → «Tiếp theo» của
  `trang_thai.md` → câu lệnh mở phiên mới). Hook mới `PreCompact` → `truoc-nen`: ghi `vet/tong-ket/<session>.json`
  (không gọi LLM, không giữ lượt); `bat-dau` với `source=compact` chèn lại tệp đã ghi, lệnh hỏng, yêu cầu cuối của
  CHÍNH phiên. Tóm tắt phiên trước thêm 3 lệnh hỏng gần nhất. Tự kiểm thêm 2 ca.
- **22/11 (3 sửa tối ưu nạp):** (1) §12 thêm `paths:` (`**/AGENTS.md`, `**/CLAUDE.md`, `**/settings*.json`), §13 thêm
  `paths:` (`**/docs/knowledge/**`) để chỉ nạp khi Claude đọc/ghi tệp khớp; §16 chuyển khỏi `rules/` sang
  `docs/16-hoc-tu-ma-nguon-mo.md` (`CLAUDE.md` trỏ `~/.claude/harness/docs/…`, +23 byte). Tự nạp đầu phiên
  16.207 → 11.522 byte (−4.685, ~−2,5K token) — **chưa kiểm ở phiên mới**. (2) `harness.py`: `traceback` (~95 ms) và
  `statistics` (~29 ms) nạp ngay trong `main()` / `do_cong()`; `canh-cong` trung vị 10 lần **318 → 209 ms** (−109 ms),
  `loi.log` không thêm dòng. (3) `NHAC-DINH-TUYEN.md`: «200K» → 170K cho khớp `MOC_CONG_NGU_CANH`. Ghi chú: ngân sách mặc
  định 11.000 của `kiem_luat.py` đã vượt 499 byte từ đợt rút gọn (số chốt 11.499), nay 522.
- **22/11 (đợt 2, MedicalGraph):** `AGENTS.md` 8.881 → 7.915 byte (−966): bỏ câu trùng §9/§11/§12 và dòng lịch sử;
  dãy «số nhớ sẵn» chuyển nguyên văn sang `docs/knowledge/bai_hoc_du_an.md` §5.5 (số đã có ở `so_lieu_chot.json`).
  `AGENTS.md` bị `.gitignore` nên bản sao lưu là bản cũ duy nhất: `sao-luu/2026-11-22/truoc-rut-gon-agents/MedicalGraph/`.
- **22/11 (đợt 2, DART-ICD-10):** `AGENTS.md` 9.059 → 7.710 byte (−1.349): bỏ câu trùng §5/§12/§13 và dãy tra nhanh §0
  trùng con trỏ ở thân; giữ số mục §0–§11, không chuyển thêm tệp. Bản cũ duy nhất (`.gitignore`): `sao-luu/2026-11-22/truoc-rut-gon-agents/DART-ICD-10/`.
- **22/11 (đợt 2, CredX):** `AGENTS.md` 8.937 → 7.576 byte (−1.361): bỏ câu trùng §1/§5/§8/§9/§11/§13, lịch sử gói tuần 6/7
  (đã ở `quy_trinh_lam_viec.md`), số làm bằng chứng ở §3/§5 (nguyên văn còn ở `luat_cung_bay_du_lieu.md`); giữ số mục §1–§7
  và mọi số quyết định. Bản cũ duy nhất (`.gitignore`): `sao-luu/2026-11-22/truoc-rut-gon-agents/CredX/`.
- **26/11 (sửa hạn chế sau đợt deepseek):** (1) cổng `xac-minh` đòi cả skill verification lẫn một lệnh Bash/PowerShell
  chạy thành công, cả hai sau lần ghi cuối — vẫn không biết lệnh đó có kiểm đúng chỗ. (2) sửa `CLAUDE.md` / `AGENTS.md`
  không kéo cổng `superpowers` / `xac-minh` / `ban-giao` / `bao-cao`. (3) `MAU_SANDBOX` thêm `Permission denied`,
  `EACCES`, `EROFS`, `Read-only file system` (lỗi thật trong transcript + mã của backend sandbox). (4) Khuôn tóm tắt 8 mục
  chuyển từ `CLAUDE.md` sang `HUONG_DAN_NEN`; `truoc-nen` in ra stdout — tài liệu hook: stdout của PreCompact là hướng dẫn
  cho bản tóm tắt (bản nén 26/11 bỏ qua khuôn khi nó nằm trong `CLAUDE.md`). Luật nạp sẵn 1.914 → 1.832 từ, trần 1.925.
  (5) `bat-dau` cảnh báo khi `D:\codevstdio\CLAUDE.md` thiếu hoặc lệch bản gốc.
- **15/11 (đợt 3, 5 sửa):** `permissions.deny`/`ask` native trong `settings.json` (chặn sửa `.env`/khoá, hỏi trước
  `git push`/`reset --hard`/`clean`/`rebase`/`branch -D`/`rm -r`, đọc `.env`) — lớp chắn không phụ thuộc hook fail-open;
  `autoMode.environment` tin mọi repo dưới `D:\codevstdio\repo\`; `NHAC-DINH-TUYEN.md` thêm dòng phân định định dạng;
  bỏ mốc 300K (không bao giờ chạm vì autoCompactWindow 200K); `main()` ép stdout/stderr UTF-8 (trước đó lệnh chạy tay
  im lặng do cp1252). Bản trước: `sao-luu/2026-11-15/truoc-5-sua/`.
- **15/11 (bộ nhớ dài hạn, không gọi LLM, chỉ stdlib — `claude-mem` vẫn TẮT):** `ket-phien` giữ lượt một lần khi phiên đã
  ghi tệp dưới `D:\codevstdio\repo\<repo>\` mà sau lần ghi cuối chưa ghi `docs/knowledge/trang_thai.md` hoặc `nhat_ky/`
  (gộp chung một khối với cổng verification; đã giữ thì thôi lời nhắc §13 cũ; phiên chỉ đọc không bị chặn).
  `vet/tong-ket/<session>.json` thêm `lenh_that_bai`, `prompt_cuoi` (≤200 ký tự, đã che bí mật), `ban_giao_luc`.
  `bat-dau` ở trong repo chèn ≤ ~15 dòng: mục «Tiếp theo/Next» của `trang_thai.md` (không có thì 1,5 KB đầu), cảnh báo
  khi `trang_thai.md` > 6 KB hoặc thiếu `AGENTS.md`/`trang_thai.md`, đường dẫn đọc thêm; tóm tắt phiên trước thêm yêu cầu
  cuối và tệp đã ghi. Lệnh mới `tim`. Hạn chế: tệp ghi qua Bash không được theo dõi. Bản trước: `sao-luu/2026-11-15/truoc-bo-nho/`.
- **11/10: tắt `claude-mem`, `caveman`, `ponytail`; gỡ hẳn `ecc`** (lý do: `DINH-TUYEN.md` mục «Đã TẮT / GỠ»);
  effort mặc định Opus `xhigh` → `high`.
  Bản trước khi sửa: `sao-luu/2026-10-11/`.
- **CodeGraph.** CLI đã mất, nên hook `codegraph prompt-hook` bị gỡ khỏi `UserPromptSubmit` (trước đó nó lỗi
  ở mỗi lượt). Cài lại CLI thì thêm lại một nhóm `UserPromptSubmit` gọi `codegraph prompt-hook`.
- **Không khôi phục được:** nội dung cũ của `DINH-TUYEN.md` / `INVENTORY.md` (343 mục) và các script `.ps1`
  cũ. Bộ hiện tại được soạn lại từ đặc tả trong rule 11 và từ bộ plugin đang có.
