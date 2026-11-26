"""Harness runtime cho Claude Code — một tệp, nhiều lệnh con, gọi từ hook trong ~/.claude/settings.json.

Ánh xạ vào kiến trúc 6 tầng (chi tiết: VAN-HANH.md cùng thư mục):
  bat-dau      SessionStart           tầng 1 Guides + 4 Memory: nhắc định tuyến, phiên trước, soát plugin;
                                      cwd trong repo -> «Tiếp theo» của trang_thai.md + cảnh báo thiếu/phình
  canh-cong    PreToolUse             tầng 5 Permissions: lệnh phá huỷ -> hỏi người dùng, tệp bí mật -> chặn,
                                      ngữ cảnh vượt mốc 200K -> hộp duyệt một lần
  sau-cong-cu  PostToolUse(+Failure)  tầng 2 Sensors + 6 Observability + 3 Loop: vết, cảm biến cú pháp, dây ngắt
  ket-phien    Stop                   tầng 6 + 4: tổng kết tất định (lượt gọi, tệp, lệnh hỏng, prompt cuối, token);
                                      giữ lượt một lần nếu chưa verification / chưa ghi bàn giao §13
  quet         chạy tay               sinh INVENTORY.md
  chi-muc      chạy tay               sinh bảng tra «mã mục -> tệp» cho một thư mục tài liệu
  bao-cao      chạy tay               in tổng kết các phiên gần đây
  tim          chạy tay               tra xuyên dự án trong <repo>/docs/knowledge/** và vet/tong-ket/

Lỗi nội bộ của hook bị nuốt (ghi vet/loi.log) và thoát 0 — harness hỏng không được làm hỏng phiên.
"""
import hashlib
import json
import os
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent
CLAUDE_DIR = Path.home() / ".claude"  # không suy từ GOC: repo có thể nằm ngoài ~/.claude (nối bằng junction)
VET_PHIEN = GOC / "vet" / "phien"        # vết từng lượt gọi công cụ, một tệp JSONL mỗi phiên
VET_TONG_KET = GOC / "vet" / "tong-ket"  # tổng kết mỗi phiên, ghi đè ở mỗi Stop
LOG_LOI = GOC / "vet" / "loi.log"

NGUONG_THAT_BAI = 2        # §7: cùng một lệnh thất bại từ lần thứ 2 -> DỪNG
NGUONG_LAP = (5, 8)        # §7/§11: 5 / 8 lượt liền giống hệt (kể cả thành công) -> nhắc / nhắc chi tiết; 3 báo nhầm (ECC)
MOC_LUOT_GOI = (60, 120, 200)   # mốc ngân sách lượt gọi công cụ mỗi phiên
MOC_NGU_CANH = (150_000,)  # mốc nhắc mềm: token gửi lại MỖI lượt
# Mốc hộp duyệt. Nhắc mềm 150K/250K/350K bị bỏ qua ở cả 5 phiên trước 11/10 => chuyển quyết định sang người dùng.
# 15/11: bỏ mốc 300K — autoCompactWindow của Opus là 200K nên ngữ cảnh không bao giờ chạm 300K.
# 22/11: 200K cũng không bao giờ chạm (nén trước đó) -> 170K ≈ 85% cửa sổ, kịp checkpoint trước khi nén (ý từ ECC context-gate).
MOC_CONG_NGU_CANH = (170_000,)
HOP_DONG = Path("D:/codevstdio")  # cwd nằm dưới đây thì CLAUDE.md đã nạp, khỏi chèn bản nhắc trùng
GOC_REPO = HOP_DONG / "repo"      # mỗi thư mục con là một repo có bộ nhớ docs/knowledge/ riêng (§13)
NGUONG_TRANG_THAI = 6_000  # byte. trang_thai.md lớn hơn -> cảnh báo đầu phiên (CredX 15/11: 20 KB ≈ 10K token)
# Lỗi quyền thật trong transcript 26/11 (Permission denied, Errno 13, Access is denied) + mã của backend sandbox
# (Seatbelt EPERM, Landlock EACCES, bwrap EROFS). Khớp nhầm lỗi quyền thường: lời nhắc sandbox thay
# cho đếm ngắt mạch §7 ở lệnh đó (ponytail: đoán theo chữ, cần phân biệt chắc thì đọc mã thoát của sandbox).
MAU_SANDBOX = re.compile(r"Access is denied|Operation not permitted|Permission denied|EPERM|EACCES|EROFS"
                         r"|Read-only file system|sandbox", re.I)
HUONG_DAN_NEN = ("Tóm tắt đủ 8 mục, mục trống ghi «(không)»: Yêu cầu & ý định · Khái niệm kỹ thuật · Tệp & mã "
                 "(đường dẫn: vì sao, đã đổi gì) · Lỗi & cách sửa · Việc đang chờ · Việc đang làm · Bước tiếp · Ngữ "
                 "cảnh then chốt. Giữ nguyên văn đường dẫn, lệnh, chuỗi lỗi, con số; ghi đúng lời người dùng sửa; có "
                 "bản tóm tắt cũ thì gộp, bỏ điều đã cũ.")  # PreCompact in ra -> Claude Code dùng làm hướng dẫn tóm tắt
TEP_HUONG_DAN = {"claude.md", "agents.md"}  # sửa tệp hướng dẫn không kéo cổng xác minh / bàn giao / báo cáo
MAU_BAN_GIAO = re.compile(r"docs/knowledge/(trang_thai\.md$|nhat_ky/)")  # đường dẫn con trong repo, đã chuẩn hoá
MAU_MUC_TIEP = re.compile(r"^(#+)[^\n]*\b(tiếp theo|next)\b[^\n]*$", re.I | re.M)
TRAN_TU_LUAT = 1_925  # từ (str.split) của codevstdio/CLAUDE.md + luật `@`. Đo 26/11: 1.832 (+5%) sau khi chuyển khuôn
#                       nén sang HUONG_DAN_NEN. Nâng trần phải ghi lý do
NGUONG_SO_TEP = 12         # ghi sang tệp thứ 13 khác nhau -> soát lại phạm vi §5
CONG_CU_GHI = ("Edit", "Write", "MultiEdit", "NotebookEdit")
CONG_CU_LENH = ("Bash", "PowerShell")
PLUGIN_BAT_BUOC = ("superpowers@claude-plugins-official", "ponytail@ponytail")  # người dùng chốt 15/11/2026
SKILL_XAC_MINH = "superpowers:verification-before-completion"
NGUONG_DOC_LON = 200_000  # byte. Đo 15/11: Read ~23% kết quả công cụ đưa vào ngữ cảnh
DUOI_NHI_PHAN = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")  # Read tự thu nhỏ. PDF không: đo 25/11 một lần đọc ~70K token
NGUONG_DOC_LAI = 2  # Read cùng tham số, tệp chưa đổi, đã 2 lần từ lần nén cuối -> chặn lần 3 (đo 25/11: một tệp đọc 130 lần)

_I = re.IGNORECASE
# §9 — danh sách cấm cứng: không chặn hẳn mà chuyển thành hộp thoại duyệt, để người dùng
# ra lệnh đích danh cho đúng lần đó.
LENH_PHA_HUY = [
    (re.compile(r"\bgit\s+reset\s+--hard\b", _I), "git reset --hard"),
    (re.compile(r"\bgit\s+checkout\b[^;&|\n]*\s--(\s|$)", _I), "git checkout -- <tệp>"),
    (re.compile(r"\bgit\s+restore\b(?![^;&|\n]*--staged)", _I), "git restore"),
    (re.compile(r"\bgit\s+clean\s+-\w*f", _I), "git clean -f"),
    (re.compile(r"\bgit\s+push\b", _I), "git push"),
    (re.compile(r"\bgit\s+rebase\b", _I), "git rebase"),
    (re.compile(r"\bgit\s+commit\b[^;&|\n]*--amend", _I), "git commit --amend"),
    (re.compile(r"\bgit\s+branch\s+-D\b"), "git branch -D"),
    (re.compile(r"\brm\s+-\w*r", _I), "rm -r"),
    (re.compile(r"\bRemove-Item\b[^;|\n]*-Recurse", _I), "Remove-Item -Recurse"),
    (re.compile(r"\b(rmdir|rd)\s+/s\b", _I), "rmdir /s"),
    (re.compile(r"\bnpm\s+(install|i)\b[^;&|\n]*\s(-g|--global)\b", _I), "npm install -g"),
    (re.compile(r"\b(setx|Set-ExecutionPolicy|reg\s+(add|delete))\b", _I), "đổi cấu hình hệ thống"),
]
# Hai luật về tệp đích .env dò trên chuỗi thô (không tách lệnh): hỏi thừa còn hơn sót.
LENH_TEP_ENV = [
    (re.compile(r"(>|Out-File|Set-Content|Add-Content)[^;|\n]*\.env(?![\w.])", _I), "ghi vào .env"),
    (re.compile(r"\b(cat|type|Get-Content|gc|head|tail|less|more)\s[^;|\n]*\.env(?![\w.])", _I), "in .env ra output"),
]
LENH_DU_LIEU = {"echo", "printf", "grep", "rg", "findstr", "select-string", "write-output", "write-host"}
GIT_AN_THAM_SO = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}  # tuỳ chọn toàn cục ăn thêm một token
VO_SHELL = {"bash", "sh", "cmd", "powershell", "pwsh"}
CO_VO_SHELL = {"-c", "-command", "/c"}
THONG_DICH = VO_SHELL | {"iex", "invoke-expression", "eval", "source", "xargs"}  # có mặt -> tham số lệnh dữ liệu cũng là lệnh
# Cổng quy trình tắt được bằng HARNESS_TAT=a,b (để có nhánh «off» khi đo); bi-mat-*, pha-huy thì không.
CONG_TAT_DUOC = ("superpowers", "doc-lon", "doc-lai", "ngu-canh", "xac-minh", "ban-giao", "bao-cao")
NHAN_BAO_CAO = ("ĐÃ KIỂM CHỨNG", "CHƯA KIỂM CHỨNG", "THẤT BẠI", "ĐÃ BỎ QUA", "GIẢ ĐỊNH", "CÔNG CỤ ĐÃ DÙNG")
MAU_PIP = re.compile(r"\bpip3?(\.exe)?\s+install\b|-m\s+pip\s+install\b", _I)
MAU_CO_VENV = re.compile(r"venv|conda|virtualenv|\buv\s+pip\b", _I)
MAU_BI_MAT = (
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd|bearer)(\s*[:=]\s*|\s+)['\"]?[^\s'\"]+"),
    re.compile(r"\b(sk-[\w-]{16,}|ghp_\w{20,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16}|xox[bp]-[\w-]{10,})"),
)


# ---------------------------------------------------------------- tiện ích chung

def doc_dau_vao():
    du_lieu = sys.stdin.buffer.read().decode("utf-8", errors="replace").strip()
    return json.loads(du_lieu) if du_lieu else {}


def xuat(d):
    sys.stdout.buffer.write(json.dumps(d, ensure_ascii=False).encode("utf-8"))


def bay_gio():
    return datetime.now().isoformat(timespec="seconds")


def doc_json(p, mac_dinh=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return mac_dinh


def chuan_hoa(p):
    return os.path.normcase(os.path.normpath(p)) if p else ""


def che_bi_mat(s):
    s = MAU_BI_MAT[0].sub(lambda m: m.group(1) + m.group(2) + "***", s)
    return MAU_BI_MAT[1].sub("***", s)


def duong_dan_tep(tham_so):
    return tham_so.get("file_path") or tham_so.get("notebook_path") or ""


def tom_tat(ten, tham_so):
    if ten in CONG_CU_LENH:
        s = tham_so.get("command", "")
    else:
        s = (duong_dan_tep(tham_so) or tham_so.get("pattern") or tham_so.get("url")
             or tham_so.get("skill") or tham_so.get("description") or "")
    return che_bi_mat(" ".join(str(s).split()))[:200]


def la_tep_bi_mat(p):
    ten = Path(p).name.lower()
    if ten in (".env.example", ".env.sample", ".env.template"):
        return False
    return (ten == ".env" or ten.startswith(".env.") or ten in (".credentials.json", "credentials.json")
            or ten.endswith((".pem", ".key", ".pfx", ".p12")) or ten.startswith(("id_rsa", "id_ed25519")))


def tep_vet(sid):
    return VET_PHIEN / f"{sid or 'khong-ro'}.jsonl"


def doc_vet(sid):
    p = tep_vet(sid)
    if not p.is_file():
        return []
    ds = []
    for dong in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ds.append(json.loads(dong))
        except ValueError:
            pass
    return ds


def ghi_vet(sid, ban_ghi):
    VET_PHIEN.mkdir(parents=True, exist_ok=True)
    with tep_vet(sid).open("a", encoding="utf-8") as f:
        f.write(json.dumps(ban_ghi, ensure_ascii=False) + "\n")


def la_tep_du_an(p):
    """Tệp dự án: dưới HOP_DONG hoặc trong một git work tree; trừ scratchpad, ~/.claude, mọi thư mục .claude và
    tệp hướng dẫn CLAUDE.md / AGENTS.md."""
    p = Path(p)
    s = chuan_hoa(str(p))
    if ("scratchpad" in s or s.startswith(chuan_hoa(str(CLAUDE_DIR))) or f"{os.sep}.claude{os.sep}" in s
            or p.name.lower() in TEP_HUONG_DAN):
        return False
    return s.startswith(chuan_hoa(str(HOP_DONG)) + os.sep) or any((d / ".git").exists() for d in p.parents)


def goi_skill(b, tien_to):
    return (b.get("loai") == "goi" and b.get("cong_cu") == "Skill" and b.get("ok")
            and b.get("tom_tat", "").startswith(tien_to))


def thieu_xac_minh(goi):
    """Số tệp dự án chưa được xác minh (0 = đủ): sau lần ghi cuối phải có cả skill verification-before-completion
    lẫn một lệnh Bash/PowerShell chạy thành công. Harness không biết lệnh đó có kiểm đúng chỗ không (§8 vẫn đòi nói)."""
    tep, skill, lenh = set(), False, False
    for b in goi:
        if b.get("tep") and la_tep_du_an(b["tep"]):
            tep.add(chuan_hoa(b["tep"]))
            skill = lenh = False
        elif goi_skill(b, SKILL_XAC_MINH):
            skill = True
        elif b.get("cong_cu") in CONG_CU_LENH and b.get("ok"):
            lenh = True
        if skill and lenh:
            tep.clear()
    return len(tep)


def repo_cua(p):
    """`D:\\codevstdio\\repo\\<repo>\\<con>` -> (<repo>, <con> dạng a/b), cả hai đã chuẩn hoá chữ thường; khác -> None."""
    g, s = chuan_hoa(str(GOC_REPO)) + os.sep, chuan_hoa(p)
    if not s.startswith(g):
        return None
    ten, _, con = s[len(g):].partition(os.sep)
    return ten, con.replace(os.sep, "/")


def thieu_ban_giao(goi):
    """Repo có tệp dự án ghi SAU lần ghi trang_thai.md / nhat_ky/ cuối cùng của chính repo đó (§13). Phiên chỉ đọc -> []."""
    no = set()
    for b in goi:
        r = b.get("tep") and la_tep_du_an(b["tep"]) and repo_cua(b["tep"])
        if r:
            (no.discard if MAU_BAN_GIAO.match(r[1]) else no.add)(r[0])
    return sorted(no)


# ---------------------------------------------------------------- tầng 5: cổng quyền

def ghi_cong(vao, cong, quyet):
    """Ghi vết một lần cổng bắn (đo bằng `do-cong`). Cổng quy trình nằm trong HARNESS_TAT -> ghi «tat», trả False."""
    tat = cong in CONG_TAT_DUOC and cong in {c.strip() for c in os.environ.get("HARNESS_TAT", "").split(",")}
    try:
        ghi_vet(vao.get("session_id", ""), {"t": bay_gio(), "loai": "cong", "cong": cong, "quyet": "tat" if tat else quyet,
                                             "cong_cu": vao.get("tool_name", ""),
                                             "tom_tat": tom_tat(vao.get("tool_name", ""), vao.get("tool_input") or {})})
    except OSError:
        pass  # vết hỏng không được làm câm cổng an ninh
    return not tat


def quyet_dinh(vao, cong, loai, ly_do):
    """Trả True nếu đã hỏi / chặn; False nếu cổng đang tắt (cổng sau trong chuỗi vẫn được xét)."""
    if not ghi_cong(vao, cong, loai):
        return False
    xuat({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": loai, "permissionDecisionReason": ly_do}})
    return True


def canh_cong():
    vao = doc_dau_vao()
    if not cong_quyen(vao) and not cong_superpowers(vao) and not cong_doc_lon(vao):
        cong_ngu_canh(vao)


def _ten(t):
    """Tên lệnh của một token: bỏ `$(`, thư mục, `.exe`, chữ thường."""
    return re.split(r"[\\/]", t.lstrip("$(`"))[-1].lower().removesuffix(".exe")


def phan_tich_lenh(lenh):
    """Nhãn LENH_PHA_HUY khớp, xét từng đoạn (; & |): bỏ tuỳ chọn toàn cục của git, bỏ qua tham số của lệnh
    dữ liệu (echo, grep…) trừ khi có `(`, `` ` `` hoặc cả lệnh có trình thông dịch (`| sh`, `iex`), đệ quy vào
    bash/cmd/powershell -c. Ngoặc không đóng -> regex thô."""
    try:
        lex = shlex.shlex(lenh.replace("\n", ";"), posix=True, punctuation_chars=";&|")
        lex.whitespace_split, lex.escape = True, ""  # giữ `\` của đường dẫn Windows
        lex.commenters = ""  # `\n` đã thành `;`: để `#` nuốt thì lọt cả các dòng sau
        tu = list(lex)
    except ValueError:
        return [n for m, n in LENH_PHA_HUY if m.search(lenh)]
    chay_chuoi = any(_ten(x) in THONG_DICH for x in tu)  # echo 'git push' | sh
    nhan, doan = [], []
    for t in tu + [";"]:
        if not t or t.strip(";&|"):
            doan.append(t)
            continue
        ten = [_ten(x) for x in doan]
        co = next((i for i, x in enumerate(doan) if x.lower() in CO_VO_SHELL), 0)
        if ten and ten[0] in VO_SHELL and co:
            nhan += phan_tich_lenh(" ".join(doan[co + 1:]))
        elif ten and (ten[0] not in LENH_DU_LIEU or chay_chuoi or any("(" in x or "`" in x for x in doan)):
            chuan, sau_git, an = [], False, 0
            for x, n in zip(doan, ten):
                if an:
                    an -= 1
                elif sau_git and x.startswith("-"):
                    an = 1 if x in GIT_AN_THAM_SO else 0
                else:
                    sau_git = n == "git"
                    chuan.append("git" if sau_git else x)
            s = " ".join(chuan)
            nhan += [n for m, n in LENH_PHA_HUY if m.search(s)]
        doan = []
    return list(dict.fromkeys(nhan))


def cong_quyen(vao):
    """Trả True nếu đã ra quyết định (hỏi / chặn)."""
    ten, tham_so = vao.get("tool_name", ""), vao.get("tool_input") or {}
    if ten in CONG_CU_GHI or ten == "Read":
        p = duong_dan_tep(tham_so)
        if not p or not la_tep_bi_mat(p):
            return False
        if ten == "Read":
            return quyet_dinh(vao, "bi-mat-doc", "ask", f"[HARNESS §10] `{Path(p).name}` là tệp bí mật — đọc vào là đưa khoá vào ngữ cảnh. Chỉ đọc khi người dùng duyệt.")
        return quyet_dinh(vao, "bi-mat-ghi", "deny", f"[HARNESS §10] `{Path(p).name}` là tệp bí mật — agent không sửa. Cần đổi thì báo người dùng tự đổi.")
    if ten in CONG_CU_LENH:
        lenh = tham_so.get("command", "")
        ly_do = phan_tich_lenh(lenh) + [nhan for mau, nhan in LENH_TEP_ENV if mau.search(lenh)]
        if MAU_PIP.search(lenh) and not MAU_CO_VENV.search(lenh):
            ly_do.append("pip install ngoài venv")
        if ly_do:
            return quyet_dinh(vao, "pha-huy", "ask", f"[HARNESS §9] Lệnh thuộc nhóm DESTRUCTIVE ({', '.join(ly_do)}) — chỉ chạy khi người dùng duyệt đích danh lần này.")
    return False


def cong_superpowers(vao):
    """Bắt buộc 15/11/2026: ghi tệp dự án khi phiên chưa gọi skill superpowers nào -> từ chối."""
    # ponytail: chỉ thấy Edit/Write; ghi bằng Bash (sed -i, heredoc) lọt cổng — §5 cấm cách đó; bắt cả lệnh nếu tái phạm.
    ten, tham_so = vao.get("tool_name", ""), vao.get("tool_input") or {}
    p = duong_dan_tep(tham_so) if ten in CONG_CU_GHI else ""
    if not p or not la_tep_du_an(p) or any(goi_skill(b, "superpowers:") for b in doc_vet(vao.get("session_id", ""))):
        return False
    return quyet_dinh(vao, "superpowers", "deny",
                      "[HARNESS §5] Phiên chưa gọi skill superpowers nào — bắt buộc trước khi ghi tệp dự án. Gọi `Skill` "
                      "khớp trạng thái: superpowers:brainstorming / writing-plans (PLAN), test-driven-development / "
                      "executing-plans (IMPLEMENT), systematic-debugging (lỗi) — rồi ghi lại.")


def ky_goi(ten, tham_so):
    return hashlib.sha1((ten + json.dumps(tham_so, sort_keys=True, ensure_ascii=False, default=str))
                        .encode("utf-8")).hexdigest()[:12]


def cong_doc_lon(vao):
    """§11: Read trọn tệp > NGUONG_DOC_LON không offset/limit/pages, hoặc đọc lại tệp chưa đổi -> từ chối."""
    tham_so = vao.get("tool_input") or {}
    p = Path(duong_dan_tep(tham_so) or ".")
    if vao.get("tool_name") != "Read" or not p.is_file():
        return False
    ky, mt = ky_goi("Read", tham_so), p.stat().st_mtime
    vet = doc_vet(vao.get("session_id", ""))
    nen = max((i for i, b in enumerate(vet) if b.get("loai") == "nen"), default=-1)
    lan = sum(1 for b in vet[nen + 1:] if b.get("loai") == "goi" and b.get("ok") and b.get("ky") == ky and b.get("mt") == mt)
    if lan >= NGUONG_DOC_LAI and quyet_dinh(vao, "doc-lai", "deny",
                                            f"[HARNESS §11] Chặn đọc lại: `{p.name}` đã đọc {lan} lần cùng tham số, tệp chưa đổi — nội dung "
                                            "vẫn trong ngữ cảnh, dùng lại. Cần đoạn khác thì đổi offset/limit."):
        return True
    if (any(k in tham_so for k in ("offset", "limit", "pages")) or p.suffix.lower() in DUOI_NHI_PHAN
            or p.stat().st_size <= NGUONG_DOC_LON):
        return False
    cach = ("kèm `pages` (vd \"1-5\"), hoặc `pdftotext` ra scratchpad rồi grep" if p.suffix.lower() == ".pdf"
            else "tìm vị trí bằng `grep -n` rồi Read có offset/limit; cần cả tệp thì gọi lại kèm limit tường minh")
    return quyet_dinh(vao, "doc-lon", "deny",
                      f"[HARNESS §11] `{p.name}` {p.stat().st_size // 1000} KB — đọc trọn sẽ nằm lại trong ngữ cảnh đến "
                      f"hết phiên. Đọc {cach}.")


def cong_ngu_canh(vao):
    """§11 luật 3: vượt mốc ngữ cảnh thì hỏi người dùng MỘT lần mỗi mốc — đi tiếp hay bàn giao sang phiên mới."""
    sid = vao.get("session_id", "")
    ctx = ngu_canh_gan_nhat(vao.get("transcript_path", ""))
    moc = next((m for m in reversed(MOC_CONG_NGU_CANH) if ctx >= m), 0)
    if not moc:
        return
    khoa = f"cong-{moc // 1000}k"
    if any(b.get("khoa") == khoa for b in doc_vet(sid) if b.get("loai") == "day-ngat"):
        return
    ghi_vet(sid, {"t": bay_gio(), "loai": "day-ngat", "khoa": khoa})
    quyet_dinh(vao, "ngu-canh", "ask", f"[HARNESS §11] Ngữ cảnh đã {ctx:,} token MỖI lượt gọi (mốc {moc // 1000}K) — mỗi lượt từ đây "
                      "tốn ít nhất ngần ấy, và sắp tự nén (mất chi tiết). Cho phép = làm tiếp phiên này. Từ chối = "
                      "agent PHẢI: đưa việc dở tới điểm dừng sạch → ghi mục «Tiếp theo» của trang_thai.md (+ "
                      "docs/knowledge/nhat_ky/) → đưa câu lệnh mở phiên mới, rồi dừng.")


# ---------------------------------------------------------------- tầng 2: cảm biến

def cam_bien(p):
    """Kiểm tệp vừa ghi. Trả về chuỗi lỗi, hoặc None nếu sạch / không thuộc loại kiểm được."""
    p = Path(p)
    duoi = p.suffix.lower()
    if duoi not in (".py", ".json", ".ipynb") or not p.is_file():
        return None
    raw = p.read_bytes()
    if duoi == ".py":
        try:
            compile(raw, str(p), "exec", dont_inherit=True)
        except SyntaxError as e:
            return f"{p.name}:{e.lineno}: SyntaxError — {e.msg}"
        except ValueError as e:
            return f"{p.name}: {e}"
        return None
    if raw.startswith(b"\xef\xbb\xbf"):
        return f"{p.name}: JSON có BOM UTF-8 — json.load sẽ báo 'Unexpected UTF-8 BOM' (§14). Ghi lại không BOM."
    try:
        json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        return f"{p.name}: JSON không hợp lệ — {e}"
    return None


# ---------------------------------------------------------------- tầng 6 + 3: vết và dây ngắt

def sau_cong_cu():
    vao = doc_dau_vao()
    su_kien = vao.get("hook_event_name") or "PostToolUse"
    sid = vao.get("session_id", "")
    ten, tham_so = vao.get("tool_name", ""), vao.get("tool_input") or {}
    ok = su_kien != "PostToolUseFailure"

    truoc = doc_vet(sid)
    goi = [b for b in truoc if b.get("loai") == "goi"]
    ban_ghi = {"t": bay_gio(), "loai": "goi", "cong_cu": ten, "ok": ok, "tom_tat": tom_tat(ten, tham_so),
               "ky": ky_goi(ten, tham_so)}
    if ten == "Read" and ok:
        try:
            ban_ghi["mt"] = Path(duong_dan_tep(tham_so)).stat().st_mtime  # cổng doc-lai: tệp đổi thì được đọc lại
        except (OSError, TypeError):
            pass
    if not truoc:
        ban_ghi["cwd"] = vao.get("cwd", "")
    tep = duong_dan_tep(tham_so) if ten in CONG_CU_GHI and ok else ""
    if tep:
        ban_ghi["tep"] = tep
    if not ok and ten in CONG_CU_LENH and MAU_SANDBOX.search(str(vao.get("error") or "")):
        ban_ghi["sandbox"] = True
    ghi_vet(sid, ban_ghi)

    canh_bao = []  # (khoá, thông điệp)
    da_ban = {b.get("khoa") for b in truoc if b.get("loai") == "day-ngat"}
    # Dây ngắt 0 — vòng lặp: NGUONG_LAP lượt liền cùng công cụ + tham số, kể cả lượt thành công.
    ky = ban_ghi["ky"]
    for n in NGUONG_LAP:
        if [b.get("ky") for b in goi[-(n - 1):]] == [ky] * (n - 1) and f"lap{n}-{ky}" not in da_ban:
            canh_bao.append((f"lap{n}-{ky}", f"Cùng một lượt gọi đã lặp {n} lần liền — có thể đang vòng lặp. "
                                             "§7: đổi cách tiếp cận hoặc báo người dùng; §11: đừng đọc lại tệp chưa đổi."
                             if n == NGUONG_LAP[0] else
                             f"Vẫn vòng lặp: {ten} lặp {n} lần liền với `{ban_ghi['tom_tat'][:200]}` — đừng gọi lại đúng "
                             "tham số này; nêu điều đã thấy, đổi hướng, hoặc dừng và hỏi người dùng."))
    # Sandbox chặn không phải lỗi mã: nhắc một lần, không tính vào ngắt mạch.
    if ban_ghi.get("sandbox") and "sandbox" not in da_ban:
        canh_bao.append(("sandbox", "Lệnh hỏng vì quyền truy cập — nhiều khả năng sandbox chặn, không phải lỗi mã. Đừng đổi "
                                    "lệnh vòng vèo; báo người dùng, hoặc xin chạy ngoài sandbox kèm lý do."))
    # Dây ngắt 1 — §7 ngắt mạch: cùng một lệnh thất bại lặp lại.
    if not ok and ten in CONG_CU_LENH and not ban_ghi.get("sandbox"):
        lan = 1 + sum(1 for b in goi if not b.get("ok") and not b.get("sandbox") and b.get("tom_tat") == ban_ghi["tom_tat"])
        if lan >= NGUONG_THAT_BAI:
            canh_bao.append(("that-bai-lap", f"Lệnh này đã thất bại {lan} lần trong phiên. §7 ngắt mạch: DỪNG sửa-thử, "
                                             "báo cáo lỗi kèm log nguyên văn, liệt kê giả thuyết đã loại, chờ người dùng."))
    # Dây ngắt 2 — ngân sách lượt gọi.
    so_luot = len(goi) + 1
    if so_luot in MOC_LUOT_GOI:
        canh_bao.append((f"ngan-sach-{so_luot}", f"Đã {so_luot} lượt gọi công cụ trong phiên. Soát lại: kế hoạch còn đúng không, "
                                                 "có đang thử-sai (§7) hay quét rộng (§11) không? Còn xa đích thì báo người dùng trước khi đi tiếp."))
    # Dây ngắt 2b — ngân sách NGỮ CẢNH. Mỗi lượt gọi gửi lại toàn bộ hội thoại, nên đây mới là
    # thước đo chi phí thật; đếm lượt gọi không phân biệt được phiên 50K với phiên 350K mỗi lượt.
    ctx = ngu_canh_gan_nhat(vao.get("transcript_path", ""))
    if ctx:
        for moc in MOC_NGU_CANH:
            khoa = f"ngu-canh-{moc // 1000}k"
            if ctx >= moc and khoa not in da_ban:
                canh_bao.append((khoa, f"Ngữ cảnh đã {ctx:,} token MỖI lượt gọi — 10 lượt nữa tốn ~{ctx * 10 // 1_000_000:.1f} triệu token. "
                                       "§11: gộp nhiều sửa vào một lần ghi thay vì nhiều lượt Edit lẻ; đừng đọc trọn tệp lớn vào ngữ cảnh; "
                                       "phần còn lại là thao tác lặp thì ghi bàn giao vào docs/knowledge/nhat_ky/ và đề nghị người dùng mở phiên mới."))
                break
    # Dây ngắt 3 — phạm vi: số tệp khác nhau đã ghi (bỏ qua scratchpad).
    if tep and "scratchpad" not in tep.lower():
        da_ghi = {chuan_hoa(b["tep"]) for b in goi if b.get("tep") and "scratchpad" not in b["tep"].lower()}
        if chuan_hoa(tep) not in da_ghi and len(da_ghi) == NGUONG_SO_TEP:
            canh_bao.append(("pham-vi", f"Đã ghi sang tệp thứ {NGUONG_SO_TEP + 1} khác nhau. §5: đối chiếu với nhóm «Sẽ sửa» đã công bố; "
                                        "tệp nào ngoài phạm vi thì dừng và xin xác nhận trước khi sửa tiếp."))

    loi = cam_bien(tep) if tep else None
    for khoa, _ in canh_bao:
        ghi_vet(sid, {"t": bay_gio(), "loai": "day-ngat", "khoa": khoa})
    if loi:
        ghi_vet(sid, {"t": bay_gio(), "loai": "cam-bien", "tep": tep, "loi": loi})

    thong_diep = " ".join(t for _, t in canh_bao)
    if loi and su_kien == "PostToolUse":
        xuat({"decision": "block", "reason": f"[HARNESS cảm biến] {loi} Sửa ngay trước khi làm tiếp. {thong_diep}".strip()})
    elif thong_diep:
        xuat({"hookSpecificOutput": {"hookEventName": su_kien, "additionalContext": f"[HARNESS] {thong_diep}"}})


def dong_cuoi(duong_dan, duoi=400_000):
    """Các dòng trong `duoi` byte cuối của transcript — tệp có thể vài chục MB. Lỗi / không có -> []."""
    p = Path(duong_dan) if duong_dan else None
    if not p or not p.is_file():
        return []
    try:
        with p.open("rb") as f:
            f.seek(max(0, p.stat().st_size - duoi))
            return f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []


def ngu_canh_gan_nhat(duong_dan, duoi=400_000):
    """Token đã gửi lại ở lượt API gần nhất."""
    for d in reversed(dong_cuoi(duong_dan, duoi)):
        if '"usage"' not in d:
            continue
        try:
            u = ((json.loads(d).get("message") or {}).get("usage")) or {}
        except ValueError:
            continue
        n = (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
        if n:
            return n
    return 0


# ---------------------------------------------------------------- tầng 6 + 4: tổng kết phiên

def dem_token(duong_dan):
    p = Path(duong_dan) if duong_dan else None
    if not p or not p.is_file():
        return {}
    theo_yeu_cau, mo_hinh = {}, ""
    with p.open(encoding="utf-8", errors="replace") as f:
        for dong in f:
            if '"usage"' not in dong:
                continue
            try:
                d = json.loads(dong)
            except ValueError:
                continue
            m = d.get("message") or {}
            if d.get("type") != "assistant" or not isinstance(m.get("usage"), dict):
                continue
            # Mỗi khối nội dung của cùng một yêu cầu lặp lại cùng usage -> gộp theo requestId.
            theo_yeu_cau[d.get("requestId") or d.get("uuid")] = m["usage"]
            mo_hinh = m.get("model") or mo_hinh
    tong = {"vao": 0, "cache_ghi": 0, "cache_doc": 0, "ra": 0}
    for u in theo_yeu_cau.values():
        tong["vao"] += u.get("input_tokens") or 0
        tong["cache_ghi"] += u.get("cache_creation_input_tokens") or 0
        tong["cache_doc"] += u.get("cache_read_input_tokens") or 0
        tong["ra"] += u.get("output_tokens") or 0
    tong["so_yeu_cau"] = len(theo_yeu_cau)
    tong["mo_hinh"] = mo_hinh
    return tong


def prompt_cuoi(duong_dan):
    """Prompt người dùng gõ gần nhất (≤200 ký tự, đã che bí mật). Bỏ tool_result, khối hệ thống chèn `<…>`, tóm tắt compact."""
    for d in reversed(dong_cuoi(duong_dan)):
        if '"user"' not in d:
            continue
        try:
            b = json.loads(d)
        except ValueError:
            continue
        if b.get("type") != "user" or b.get("isMeta") or b.get("isCompactSummary"):
            continue
        nd = (b.get("message") or {}).get("content")
        khoi = nd if isinstance(nd, list) else [{"type": "text", "text": nd}]
        s = " ".join(" ".join(str(k.get("text") or "").split()) for k in khoi
                     if isinstance(k, dict) and k.get("type") == "text" and not str(k.get("text") or "").lstrip().startswith("<"))
        if s.strip():
            return che_bi_mat(s.strip())[:200]
    return ""


def tin_cuoi(duong_dan):
    """Chữ của tin nhắn trợ lý cuối cùng trong transcript (dự phòng khi Stop thiếu `last_assistant_message`)."""
    for d in reversed(dong_cuoi(duong_dan)):
        if '"assistant"' not in d:
            continue
        try:
            nd = (json.loads(d).get("message") or {}).get("content")
        except ValueError:
            continue
        s = " ".join(k.get("text") or "" for k in nd if isinstance(k, dict) and k.get("type") == "text") \
            if isinstance(nd, list) else str(nd or "")
        if s.strip():
            return s
    return ""


def ket_phien(truoc_nen=False):
    """Stop: ghi tổng kết + giữ lượt khi thiếu xác minh/bàn giao. PreCompact (truoc_nen): chỉ ghi tổng kết."""
    vao = doc_dau_vao()
    sid = vao.get("session_id", "")
    vet = doc_vet(sid)
    if truoc_nen:
        ghi_vet(sid, {"t": bay_gio(), "loai": "nen"})  # sau nén, nội dung đã đọc mất khỏi ngữ cảnh -> cổng doc-lai đếm lại
        sys.stdout.buffer.write(HUONG_DAN_NEN.encode("utf-8"))  # PreCompact: stdout = hướng dẫn cho bản tóm tắt
    goi = [b for b in vet if b.get("loai") == "goi"]
    p_tk = VET_TONG_KET / f"{sid or 'khong-ro'}.json"
    cu = doc_json(p_tk, {})
    tep = sorted({b["tep"] for b in goi if b.get("tep") and "scratchpad" not in b["tep"].lower()})
    so_ghi_repo = sum(1 for b in goi if b.get("tep") and repo_cua(b["tep"]))
    tk = {
        "phien": sid,
        "cwd": vao.get("cwd", ""),
        "bat_dau": goi[0]["t"] if goi else cu.get("bat_dau", bay_gio()),
        "cap_nhat": bay_gio(),
        "luot_goi": len(goi),
        "that_bai": sum(1 for b in goi if not b.get("ok")),
        "tep_da_ghi": tep,
        "lenh_that_bai": list(dict.fromkeys(b["tom_tat"] for b in goi
                                            if not b.get("ok") and b.get("cong_cu") in CONG_CU_LENH))[-10:],
        "prompt_cuoi": prompt_cuoi(vao.get("transcript_path", "")) or cu.get("prompt_cuoi", ""),
        "day_ngat": [b["khoa"] for b in vet if b.get("loai") == "day-ngat"],
        "loi_cam_bien": sum(1 for b in vet if b.get("loai") == "cam-bien"),
        "token": dem_token(vao.get("transcript_path", "")),
        "so_tep_luc_nhac": cu.get("so_tep_luc_nhac", 0),
        "ban_giao_luc": cu.get("ban_giao_luc", 0),  # số lượt ghi repo lúc giữ lượt đòi bàn giao — mỗi trạng thái chỉ giữ một lần
    }
    dung = truoc_nen or vao.get("stop_hook_active")
    chan = 0 if dung else thieu_xac_minh(goi)
    if chan and not ghi_cong(vao, "xac-minh", "block"):
        chan = 0
    repo_no = [] if dung or so_ghi_repo <= tk["ban_giao_luc"] else thieu_ban_giao(goi)
    if repo_no:
        tk["ban_giao_luc"] = so_ghi_repo
    if repo_no and not ghi_cong(vao, "ban-giao", "block"):
        repo_no = []
    # §8: tin cuối không có nhãn phân loại sau một đợt ghi tệp dự án -> giữ lượt, mỗi đợt ghi một lần.
    so_ghi = sum(1 for b in goi if b.get("tep") and la_tep_du_an(b["tep"]))
    tk["bao_cao_luc"] = cu.get("bao_cao_luc", 0)
    thieu_nhan = False
    if not (chan or repo_no or dung) and so_ghi > tk["bao_cao_luc"]:
        tin = vao.get("last_assistant_message") or tin_cuoi(vao.get("transcript_path", ""))
        thieu_nhan = bool(tin.strip()) and not any(n in tin for n in NHAN_BAO_CAO)
        if thieu_nhan:
            tk["bao_cao_luc"] = so_ghi
            thieu_nhan = ghi_cong(vao, "bao-cao", "block")
    nhac = not (chan or repo_no or dung or thieu_nhan or tk["ban_giao_luc"]) and len(tep) > tk["so_tep_luc_nhac"]
    if nhac:
        tk["so_tep_luc_nhac"] = len(tep)
    VET_TONG_KET.mkdir(parents=True, exist_ok=True)
    p_tk.write_text(json.dumps(tk, ensure_ascii=False, indent=1), encoding="utf-8")
    ly_do = []
    if chan:
        ly_do.append(f"[HARNESS §5] {chan} tệp dự án đã ghi mà sau lần ghi cuối chưa có đủ: gọi `{SKILL_XAC_MINH}` "
                     "và chạy thành công một lệnh kiểm (test, build, chạy thử). Làm đủ hai việc rồi mới báo xong; không "
                     "có lệnh kiểm nào hợp thì chạy một lệnh đọc lại kết quả và ghi CHƯA KIỂM CHỨNG.")
    if repo_no:
        noi = ", ".join(str(GOC_REPO / r / "docs" / "knowledge") for r in repo_no)
        ly_do.append(f"[HARNESS §13] Đã sửa tệp dự án mà sau lần ghi cuối chưa ghi bàn giao ở: {noi}. Viết ngắn: nối "
                     "`nhat_ky/<YYYY-MM-DD>.md` (đã làm gì · đã chốt gì · còn nợ gì) hoặc sửa mục «Tiếp theo» của "
                     "`trang_thai.md`. Việc vặt không đáng ghi thì nói một câu rồi dừng — chỉ giữ một lần.")
    if thieu_nhan:
        ly_do.append("[HARNESS §8] Đã ghi tệp dự án mà tin nhắn cuối không có nhãn báo cáo (ĐÃ KIỂM CHỨNG / CHƯA KIỂM "
                     "CHỨNG / THẤT BẠI / ĐÃ BỎ QUA / GIẢ ĐỊNH / CÔNG CỤ ĐÃ DÙNG). Viết báo cáo phân loại; đang hỏi "
                     "người dùng giữa chừng thì nói một câu rồi dừng — chỉ giữ một lần.")
    if ly_do:
        xuat({"decision": "block", "reason": " ".join(ly_do)})
    elif nhac:
        xuat({"systemMessage": f"[HARNESS §13] Phiên đã ghi {len(tep)} tệp. Trước khi đóng: có tri thức mới "
                               "(lỗi khó, cách làm chuẩn) cần ghi vào <repo>/AGENTS.md hoặc docs/knowledge/ không?"})


# ---------------------------------------------------------------- tầng 1 + 4: đầu phiên

def phien_truoc(cwd, sid, vua_nen=False):
    """Tổng kết mới nhất cùng cwd của phiên KHÁC; vua_nen -> của CHÍNH phiên này (PreCompact vừa ghi)."""
    tot = None
    for p in VET_TONG_KET.glob("*.json"):
        tk = doc_json(p, {})
        if (tk.get("phien") == sid) == vua_nen and chuan_hoa(tk.get("cwd", "")) == chuan_hoa(cwd):
            if tot is None or tk.get("cap_nhat", "") > tot.get("cap_nhat", ""):
                tot = tk
    if not tot:
        return None
    tep = tot.get("tep_da_ghi", [])
    nhan = "Trước lần nén vừa rồi, phiên này" if vua_nen else "Phiên trước ở thư mục này"
    s = (f"- {nhan} ({tot.get('cap_nhat', '')[:16]}): {tot.get('luot_goi', 0)} lượt gọi, "
         f"{tot.get('that_bai', 0)} thất bại, {len(tep)} tệp đã ghi")
    if tot.get("day_ngat"):
        s += f", dây ngắt đã bật: {', '.join(tot['day_ngat'])}"
    s += "."
    if tot.get("prompt_cuoi"):
        s += f"\n  Yêu cầu cuối: «{tot['prompt_cuoi']}»"
    if tep:
        s += f"\n  Tệp đã ghi: {', '.join(Path(t).name for t in tep[:6])}" + (f" (+{len(tep) - 6})" if len(tep) > 6 else "")
    if tot.get("lenh_that_bai"):
        s += f"\n  Lệnh hỏng gần nhất: {' | '.join(tot['lenh_that_bai'][-3:])}"
    return s


def muc_tiep_theo(vb):
    """(thân mục «Tiếp theo»/«Next» của trang_thai.md ≤1,5 KB, True); không có mục -> (1,5 KB đầu, False)."""
    m = MAU_MUC_TIEP.search(vb)
    if not m:
        return vb[:1500], False
    sau = vb[m.end():]
    het = re.search(rf"^#{{1,{len(m.group(1))}}}\s", sau, re.M)  # tiêu đề cùng cấp hoặc cao hơn
    return sau[:het.start() if het else len(sau)].strip()[:1500], True


def bo_nho_repo(goc):
    """Bộ nhớ dài hạn của repo chèn đầu phiên: «Tiếp theo» của trang_thai.md, cảnh báo, con trỏ đọc thêm. ≤12 dòng."""
    kn = goc / "docs" / "knowledge"
    tt = kn / "trang_thai.md"
    dong, canh_bao = [], []
    if tt.is_file():
        than, co_muc = muc_tiep_theo(tt.read_text(encoding="utf-8", errors="replace"))
        dong.append("- trang_thai.md, " + ("mục «Tiếp theo»:" if co_muc else "không có mục «Tiếp theo» — 1,5 KB đầu:"))
        dong += ["  " + d.strip()[:160] for d in than.splitlines() if d.strip()][:8]
        kb = tt.stat().st_size
        if kb > NGUONG_TRANG_THAI:
            canh_bao.append(f"trang_thai.md {kb // 1000} KB > {NGUONG_TRANG_THAI // 1000} KB — đọc trọn tốn nhiều token, "
                            "đề nghị người dùng cắt gọn (chỉ con trỏ + tình trạng)")
    else:
        canh_bao.append("thiếu docs/knowledge/trang_thai.md")
    if not (goc / "AGENTS.md").is_file():
        canh_bao.append("thiếu AGENTS.md")
    if canh_bao:
        dong.append(f"- ⚠️ §13: {'; '.join(canh_bao)}.")
    nk = sorted(p.name for p in (kn / "nhat_ky").glob("*.md") if p.name[:1].isdigit())
    dong.append(f"- Đọc thêm: {kn}" + (f" (nhật ký mới nhất: nhat_ky/{nk[-1]})" if nk else "")
                + " · tra xuyên dự án: `python ~/.claude/harness/harness.py tim <từ khoá>`")
    return dong


def soat_plugin():
    cai_dat = (doc_json(CLAUDE_DIR / "plugins" / "installed_plugins.json", {}) or {}).get("plugins", {})
    bat = (doc_json(CLAUDE_DIR / "settings.json", {}) or {}).get("enabledPlugins", {})
    hong = [ten for ten, on in bat.items()
            if on and not any(Path(e.get("installPath", "")).is_dir() for e in cai_dat.get(ten, []))]
    dong = []
    if hong:
        dong.append(f"- ⚠️ Plugin bật nhưng hỏng đường dẫn cài: {', '.join(hong)} — skill của chúng sẽ vắng mặt; "
                    "xem ~/.claude/harness/VAN-HANH.md mục «Khôi phục».")
    tat = [ten for ten in PLUGIN_BAT_BUOC if not bat.get(ten)]
    if tat:
        dong.append(f"- ⚠️ Plugin BẮT BUỘC đang tắt: {', '.join(tat)} — báo người dùng bật lại "
                    "(`claude plugin enable <tên>`), chưa làm dự án khi thiếu.")
    return dong


def lech_ban_cai(chep, goc):
    """Bản chép CLAUDE.md (D:\\codevstdio, do cai-dat.ps1 tạo) thiếu hoặc khác bản gốc trong repo -> câu cảnh báo."""
    if not Path(goc).is_file():
        return None
    if not Path(chep).is_file():
        return f"- ⚠️ thiếu {chep} — luật harness không nạp; chạy lại cai-dat.ps1."
    if Path(chep).read_bytes() != Path(goc).read_bytes():
        return (f"- ⚠️ {chep} lệch {goc} — luật đang nạp là bản cũ. Báo người dùng chạy lại cai-dat.ps1 "
                "(hoặc cho phép chép đè).")
    return None


def bat_dau():
    vao = doc_dau_vao()
    cwd = Path(vao.get("cwd") or ".")
    c, h = chuan_hoa(str(cwd.resolve())), chuan_hoa(str(HOP_DONG))
    # Dưới HOP_DONG thì CLAUDE.md (§1–16) đã nạp đủ — chèn thêm bản nhắc là trả hai lần mỗi lượt.
    dong = [] if c == h or c.startswith(h + os.sep) else [(GOC / "NHAC-DINH-TUYEN.md").read_text(encoding="utf-8").strip()]
    if cwd.resolve().parent == cwd.resolve():
        dong.append("- ⚠️ §11: phiên mở ở gốc ổ đĩa — không nạp AGENTS.md của repo nào (đo 25/11: 38 phiên ở D:\\ chiếm 27% "
                    "quota, toàn phiên dài nhất). Việc dự án: đề nghị người dùng mở lại phiên trong thư mục repo.")
    r = repo_cua(c)
    goc = GOC_REPO / r[0] if r else cwd  # cwd ở thư mục con của repo -> vẫn lấy bộ nhớ ở gốc repo
    if (goc / "AGENTS.md").is_file():
        dong.append(f"- {goc} có AGENTS.md — đọc trước khi bắt tay (§5 LOAD_CONTEXT).")
    if r:
        dong += bo_nho_repo(goc)
    else:
        nk = cwd / "docs" / "knowledge" / "nhat_ky"
        ds = sorted(p.name for p in nk.glob("*.md") if p.name[:1].isdigit()) if nk.is_dir() else []
        if ds:
            dong.append(f"- Nhật ký phiên mới nhất: docs/knowledge/nhat_ky/{ds[-1]}")
    truoc = phien_truoc(str(cwd), vao.get("session_id", ""), vao.get("source") == "compact")
    if truoc:
        dong.append(truoc)
    dong += soat_plugin()
    lech = lech_ban_cai(HOP_DONG / "CLAUDE.md", GOC / "codevstdio" / "CLAUDE.md")
    if lech:
        dong.append(lech)
    if not dong:
        return
    xuat({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(dong)}})


# ---------------------------------------------------------------- chạy tay: quét và báo cáo

def doc_frontmatter(p):
    try:
        vb = p.read_text(encoding="utf-8", errors="replace")[:6000]
    except OSError:
        return {}
    phan = vb.split("---", 2)
    if not vb.startswith("---") or len(phan) < 3:
        return {}
    kq, khoa = {}, None
    for dong in phan[1].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", dong)
        if m:
            khoa, gia_tri = m.group(1), m.group(2).strip()
            kq[khoa] = "" if gia_tri in (">", "|", ">-", "|-") else gia_tri.strip("\"'")
        elif khoa and dong[:1] in (" ", "\t"):
            kq[khoa] = (kq[khoa] + " " + dong.strip()).strip()
    return kq


def quet_thu_muc(goc, tien_to):
    muc = []
    for loai, mau, ten_mac_dinh in (("skill", "skills/*/SKILL.md", lambda p: p.parent.name),
                                    ("lệnh", "commands/*.md", lambda p: p.stem),
                                    ("agent", "agents/*.md", lambda p: p.stem)):
        for p in sorted(goc.glob(mau)):
            if loai != "skill" and p.stem.isupper():  # README/AGENTS/CLAUDE.md là tài liệu, không phải lệnh/agent
                continue
            fm = doc_frontmatter(p)
            ten = tien_to + (fm.get("name") or ten_mac_dinh(p))
            muc.append((loai, "/" + ten if loai == "lệnh" else ten, " ".join(fm.get("description", "").split())[:160]))
    return muc


def quet():
    sys.stdout.reconfigure(encoding="utf-8")
    cai_dat = (doc_json(CLAUDE_DIR / "plugins" / "installed_plugins.json", {}) or {}).get("plugins", {})
    bat = (doc_json(CLAUDE_DIR / "settings.json", {}) or {}).get("enabledPlugins", {})
    nguon = []  # (tên nguồn, trạng thái, danh sách mục)
    for khoa, ds in sorted(cai_dat.items()):
        e = next((x for x in ds if x.get("scope") == "user"), ds[0])
        goc = Path(e.get("installPath", ""))
        trang_thai = ("bật" if bat.get(khoa) else "tắt") + ("" if goc.is_dir() else ", HỎNG đường dẫn")
        nguon.append((f"{khoa} {e.get('version', '')}", trang_thai, quet_thu_muc(goc, khoa.split("@")[0] + ":")))
    nguon.append(("~/.claude (người dùng)", "bật", quet_thu_muc(CLAUDE_DIR, "")))

    tong = sum(len(m) for _, _, m in nguon)
    out = ["# INVENTORY — những gì harness đang có", "",
           f"> Sinh tự động bởi `python ~/.claude/harness/harness.py quet` lúc {bay_gio()}. **Đừng sửa tay.**",
           "> Dùng để TRA CỨU «tổng thể có gì». Chọn công cụ theo loại việc: `DINH-TUYEN.md`.",
           "> Tên để gọi luôn lấy từ danh sách của phiên hiện tại — skill của plugin «tắt» không gọi được.", "",
           "| Nguồn | Trạng thái | Skill | Lệnh | Agent |", "| --- | --- | ---: | ---: | ---: |"]
    for ten, tt, muc in nguon:
        dem = {k: sum(1 for m in muc if m[0] == k) for k in ("skill", "lệnh", "agent")}
        out.append(f"| {ten} | {tt} | {dem['skill']} | {dem['lệnh']} | {dem['agent']} |")
    out += ["", f"**Tổng: {tong} mục.**"]
    for ten, tt, muc in nguon:
        if not muc or tt.startswith("tắt"):  # plugin tắt chỉ đếm, không liệt kê — tệp này có thể bị đọc vào ngữ cảnh
            continue
        out += ["", f"## {ten} — {tt}"]
        for loai in ("skill", "lệnh", "agent"):
            nhom = [m for m in muc if m[0] == loai]
            if nhom:
                out += ["", f"### {loai.capitalize()} ({len(nhom)})", ""]
                out += [f"- `{t}` — {mt}" if mt else f"- `{t}`" for _, t, mt in nhom]
    (GOC / "INVENTORY.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Đã ghi {GOC / 'INVENTORY.md'}: {tong} mục.")
    for ten, tt, muc in nguon:
        print(f"  {ten:<48} {tt:<22} {len(muc):>4}")


MA_MUC = re.compile(r"^#{2,4}\s+((?:[A-Z]{1,3}|\d{1,2})\.\d+[a-z]?)\b\s*(.*)$")


def don_tieu_de(s):
    """Dọn phần mô tả sau mã mục: gộp khoảng trắng, bỏ dấu nối/chấm thừa ở đầu,
    cắt 110 ký tự, thoát dấu gạch dọc để không vỡ bảng markdown."""
    return " ".join(s.split()).lstrip("—-–:. ")[:110].replace("|", "\\|")


def khoa_ma(ma):
    """Khoá sắp xếp tự nhiên: N.2 đứng trước N.13, không phải sau."""
    chu, so = ma.split(".", 1)
    dau = re.match(r"(\d+)([a-z]?)", so)
    so_hoa = chu.isdigit()
    return (0 if so_hoa else 1, int(chu) if so_hoa else 0, "" if so_hoa else chu,
            int(dau.group(1)), dau.group(2))


def tu_kiem_chi_muc():
    lay = lambda s: [m.groups() for m in map(MA_MUC.match, s.splitlines()) if m]
    assert lay("### E.1 ✅ Xong") == [("E.1", "✅ Xong")]
    assert lay("#### H.2b — Ghi chú") == [("H.2b", "— Ghi chú")]
    assert lay("# Tiêu đề\n## Việc 1\n### x.1 sai dạng\nN.9 không phải tiêu đề") == []
    assert lay("### 7.1. γ chọn sai chỗ") == [("7.1", ". γ chọn sai chỗ")]
    assert don_tieu_de(". γ chọn sai chỗ") == "γ chọn sai chỗ"
    assert don_tieu_de("a | b") == "a \\| b"
    assert khoa_ma("N.2") < khoa_ma("N.13") < khoa_ma("N.13a")
    assert khoa_ma("7.1") < khoa_ma("10.1") < khoa_ma("E.1")
    print("tự kiểm chi-muc: đạt.")


def chi_muc():
    """Sinh bảng tra «mã mục -> tệp nào, dòng nào» cho một thư mục tài liệu. Chạy tay.

    Dùng: harness.py chi-muc <thư mục> [tệp ra] [--ghi-de] [--tu-kiem]
    Mã mục = tiêu đề dạng `### N.13 ...`: chữ hoa, dấu chấm, số, hậu tố chữ thường tuỳ chọn.
    Bảng chỉ trỏ chỗ, không chép nội dung — §12 «một nguồn cho mỗi sự thật».
    """
    sys.stdout.reconfigure(encoding="utf-8")
    if "--tu-kiem" in sys.argv:
        return tu_kiem_chi_muc()
    tham = [a for a in sys.argv[2:] if not a.startswith("--")]
    if not tham:
        raise SystemExit("Dùng: harness.py chi-muc <thư mục> [tệp ra] [--ghi-de] [--tu-kiem]")
    thu_muc = Path(tham[0]).resolve()
    if not thu_muc.is_dir():
        raise SystemExit(f"Không có thư mục: {thu_muc}")
    ra = Path(tham[1]).resolve() if len(tham) > 1 else thu_muc / "chi_muc.md"
    # Không ghi đè tệp viết tay: mất bản duy nhất là thao tác không hoàn tác được (§9).
    if ra.exists() and "--ghi-de" not in sys.argv:
        if "Sinh tự động" not in ra.read_text(encoding="utf-8")[:400]:
            raise SystemExit(f"{ra} là tệp viết tay (không thấy dấu «Sinh tự động» ở đầu tệp).\n"
                             f"Muốn thay thì sao lưu trước rồi chạy lại với --ghi-de.")

    muc = []  # (mã, tệp, dòng, tiêu đề)
    tep = [p for p in sorted(thu_muc.glob("*.md")) if p.resolve() != ra]
    for p in tep:
        for i, dong in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            m = MA_MUC.match(dong)
            if m:
                tieu_de = don_tieu_de(m.group(2))
                muc.append((m.group(1), p, i, tieu_de))
    muc.sort(key=lambda t: khoa_ma(t[0]))

    trung = sorted({t[0] for t in muc if sum(1 for x in muc if x[0] == t[0]) > 1}, key=khoa_ma)
    goc_ra = ra.parent
    out = [f"# CHỈ MỤC `{thu_muc.name}/` — mã mục nằm ở tệp nào", "",
           f"> Sinh tự động bởi `python ~/.claude/harness/harness.py chi-muc {thu_muc.name}` lúc {bay_gio()}. **Đừng sửa tay.**",
           "> Cách tra: tìm mã ở bảng dưới rồi mở đúng tệp đó. Cần nguyên văn thì `grep -n \"### <mã>\" <tệp>`.",
           "> Bảng chỉ nói mục nào ở đâu. **Nội dung và số liệu ở tệp gốc — đừng chép sang đây.**", "",
           f"**{len(muc)} mã mục trong {len(tep)} tệp.**"]
    if trung:
        out += ["", f"⚠️ **Mã bị trùng ở nhiều chỗ: {', '.join(trung)}** — mã mục phải là duy nhất, sửa lại tiêu đề."]
    out += ["", "| Mã | Tệp | Dòng | Tiêu đề |", "| --- | --- | ---: | --- |"]
    for ma, p, i, td in muc:
        out.append(f"| `{ma}` | [`{p.name}`]({os.path.relpath(p, goc_ra).replace(os.sep, '/')}) | {i} | {td} |")
    # newline="\n": không có nó, Windows đổi LF thành CRLF và cả tệp lệch hash (DART §7.11).
    ra.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"Đã ghi {ra}: {len(muc)} mã mục trong {len(tep)} tệp.")
    if trung:
        print(f"  CẢNH BÁO — mã trùng: {', '.join(trung)}")


def bao_cao():
    sys.stdout.reconfigure(encoding="utf-8")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    ds = sorted((doc_json(p, {}) for p in VET_TONG_KET.glob("*.json")),
                key=lambda t: t.get("cap_nhat", ""), reverse=True)[:n]
    if not ds:
        print("Chưa có phiên nào được ghi vết.")
        return
    print(f"{'Cập nhật':<16}  {'Lượt':>5} {'Lỗi':>4} {'Tệp':>4} {'Token ra':>9} {'Cache đọc':>11}  Thư mục · dây ngắt")
    for t in ds:
        tk = t.get("token") or {}
        day = ", ".join(t.get("day_ngat", [])) or "-"
        print(f"{t.get('cap_nhat', '')[:16]:<16}  {t.get('luot_goi', 0):>5} {t.get('that_bai', 0):>4} "
              f"{len(t.get('tep_da_ghi', [])):>4} {tk.get('ra', 0):>9,} {tk.get('cache_doc', 0):>11,}  "
              f"{Path(t.get('cwd', '')).name} · {day}")
    print(f"Tổng {len(ds)} phiên: {sum(t.get('luot_goi', 0) for t in ds)} lượt gọi, "
          f"{sum((t.get('token') or {}).get('ra', 0) for t in ds):,} token ra.")


def luot_qua(b, sau):
    """Thứ tự (trong các lượt `goi` sau lần cổng bắn `b`) của lượt đầu chạy được đúng công cụ + đích ấy; None nếu không."""
    goi = [x for x in sau if x.get("loai") == "goi"]
    return next((k for k, x in enumerate(goi) if x.get("ok") and x.get("cong_cu") == b.get("cong_cu")
                 and x.get("tom_tat") == b["tom_tat"]), None)


def do_cong():
    """`harness.py do-cong` — mỗi cổng: số lần bắn, số phiên bị bắn, số lần tắt, số lần sau đó chính lệnh/tệp ấy chạy
    được («qua») và trung vị số lượt gọi từ lúc bắn đến lúc qua (0 = người dùng duyệt ngay)."""
    import statistics  # chỉ lệnh chạy tay này cần; nạp ở đầu tệp thì hook nào cũng trả ~29 ms
    sys.stdout.reconfigure(encoding="utf-8")
    tep = sorted(VET_PHIEN.glob("*.jsonl"))
    so = {}  # cổng -> [bắn, {phiên}, tắt, qua, [lượt vòng]]
    for p in tep:
        vet = doc_vet(p.stem)
        for i, b in enumerate(vet):
            if b.get("loai") != "cong":
                continue
            s = so.setdefault(b.get("cong", "?"), [0, set(), 0, 0, []])
            if b.get("quyet") == "tat":
                s[2] += 1
                continue
            s[0] += 1
            s[1].add(p.stem)
            if b.get("tom_tat"):
                j = luot_qua(b, vet[i + 1:])
                if j is not None:
                    s[3] += 1
                    s[4].append(j)
    if not so:
        print(f"Chưa có dòng vết cổng nào trong {len(tep)} phiên.")
        return
    print(f"{'Cổng':<12} {'Bắn':>5} {'Phiên':>9} {'Tắt':>5} {'Qua':>5}  Trung vị lượt vòng")
    for c, (ban, ph, tat, qua, luot) in sorted(so.items()):
        print(f"{c:<12} {ban:>5} {f'{len(ph)}/{len(tep)}':>9} {tat:>5} {qua:>5}  "
              f"{statistics.median(luot) if luot else '—'}")


def tim():
    """`harness.py tim <từ khoá> [từ khoá …]` — tra xuyên dự án trong <repo>/docs/knowledge/** và vet/tong-ket/.

    Không phân biệt hoa thường; mọi từ khoá phải có trên cùng một dòng. Tệp mới sửa in trước. ≤30 dòng."""
    tu = [t.lower() for t in sys.argv[2:]]
    if not tu:
        print("Dùng: harness.py tim <từ khoá> [từ khoá …]")
        return
    ds = [p for p in GOC_REPO.glob("*/docs/knowledge/**/*") if p.suffix.lower() in (".md", ".txt", ".json") and p.is_file()]
    ds = sorted(ds + list(VET_TONG_KET.glob("*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
    kq = []
    for p in ds:
        for i, d in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            thap = d.strip().lower()
            if all(t in thap for t in tu):
                kq.append(f"{p}:{i}: {d.strip()[max(0, thap.find(tu[0]) - 60):][:160]}")
    if len(kq) > 30:
        kq[29:] = [f"… còn {len(kq) - 29} dòng nữa — thêm từ khoá để thu hẹp."]
    print("\n".join(kq) or "Không thấy.")


def san_ngu_canh(duong_dan):
    """Ngữ cảnh của lượt API ĐẦU TIÊN = phần nạp cố định trước khi làm việc."""
    with Path(duong_dan).open(encoding="utf-8", errors="replace") as f:
        for dong in f:
            if '"usage"' not in dong:
                continue
            try:
                u = ((json.loads(dong).get("message") or {}).get("usage")) or {}
            except ValueError:
                continue
            n = ((u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
                 + (u.get("cache_read_input_tokens") or 0))
            if n:
                return n
    return 0


def do_ton():
    """`harness.py do-ton [transcript.jsonl|thư mục]` — chi phí ngữ cảnh của một phiên.

    Không có tham số thì lấy transcript mới nhất của thư mục hiện tại."""
    sys.stdout.reconfigure(encoding="utf-8")
    dd = sys.argv[2] if len(sys.argv) > 2 else ""
    p = Path(dd) if dd else Path.home() / ".claude" / "projects" / chuan_hoa_ten_du_an(Path.cwd())
    if p.is_dir():
        ds = sorted(p.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not ds:
            print(f"Không có transcript nào trong {p}")
            return
        p = ds[0]
    if not p.is_file():
        print(f"Không thấy {p}")
        return
    tk = dem_token(p)
    n = tk.get("so_yeu_cau", 0)
    ctx = tk.get("cache_doc", 0) + tk.get("cache_ghi", 0)
    print(f"Phiên  : {p.name}")
    print(f"Mô hình: {tk.get('mo_hinh', '?')}")
    print(f"Lượt API                 : {n:,}")
    san = san_ngu_canh(p)
    print(f"SÀN — ngữ cảnh lượt đầu  : {san:,} token   <- phần nạp cố định")
    print(f"Ngữ cảnh gửi lại (tổng)  : {ctx:,} token")
    print(f"  trung bình mỗi lượt    : {ctx // max(n, 1):,} token   <- chỉ số quyết định")
    print(f"Token sinh ra (output)   : {tk.get('ra', 0):,}")
    if n and ctx // n > 150_000:
        print("")
        print("CANH BAO — tren 150K token moi luot. §11: gop luot goi, dung doc tron tep lon, "
              "cat phien som va ban giao bang tep.")


def chuan_hoa_ten_du_an(duong_dan):
    return re.sub(r"[\\/:]", "-", str(duong_dan))


def tu_kiem_bat_buoc():
    """Chạy tay: kiểm cổng superpowers, cổng bàn giao §13, bộ nhớ đầu phiên và `tim` bằng một phiên giả, xong xoá vết giả."""
    import shutil, subprocess, tempfile, uuid
    sid = "tu-kiem-" + uuid.uuid4().hex[:8]
    goc_gia = GOC_REPO / "_tu_kiem"
    du_an = str(goc_gia / "a.md")
    trang_thai = str(goc_gia / "docs" / "knowledge" / "trang_thai.md")
    ngoai = str(Path(tempfile.gettempdir()) / "scratchpad" / "a.md")
    tam = Path(tempfile.mkdtemp(prefix="tu_kiem_"))
    lon = tam / "doc_lon.txt"

    def chay(lenh, *ts, _env=None, **vao):
        r = subprocess.run([sys.executable, __file__, lenh, *ts], capture_output=True, check=True,
                           input=json.dumps({"session_id": sid, **vao}).encode("utf-8"), env={**os.environ, **(_env or {})})
        return r.stdout.decode("utf-8")

    def ghi(p):
        return {"tool_name": "Write", "tool_input": {"file_path": p, "content": ""}}

    def skill(ten):
        return {"tool_name": "Skill", "tool_input": {"skill": ten}}

    g = lambda p: {"loai": "goi", "tep": str(p)}
    try:
        # Hàm thuần: tách lệnh shell §9.
        hoi = ["git -C repo push", "git --no-pager push origin main", "git -c core.x=1 reset --hard", "git push",
               "rm -rf x", 'bash -c "git -C r push"', "echo $(git push)", 'echo "a" && git -C r push 2>&1',
               r"Remove-Item -Recurse D:\x\y", '"C:/Program Files/Git/cmd/git.exe" -C r push', "git add .\ngit push",
               "f() { # chu thich\nrm -rf x\n}", "# ghi chu\nrm -rf y", "printf 'git push' | sh",
               "echo 'rm -rf x' | bash", "echo git push | Invoke-Expression", "echo 'git push' > a.sh; bash a.sh",
               'git push "x']  # ca cuối: ngoặc không đóng -> regex cũ
        for s in hoi:
            assert phan_tich_lenh(s), f"lọt lệnh phá huỷ: {s!r}"
        for s in ['echo "rm -rf la lenh nguy hiem"', 'grep -n "git push" README.md', "git -C repo status"]:
            assert not phan_tich_lenh(s), f"hỏi thừa: {s!r}"
        # §11: luật nạp sẵn không được phình lại âm thầm.
        hd = GOC / "codevstdio" / "CLAUDE.md"
        nap = [hd] + [hd.parent / d[1:].strip() for d in hd.read_text(encoding="utf-8").splitlines() if d.startswith("@")]
        so_tu = sum(len(p.read_text(encoding="utf-8").split()) for p in nap)
        assert so_tu <= TRAN_TU_LUAT, f"luật nạp sẵn {so_tu} từ > trần {TRAN_TU_LUAT} — rút gọn, hoặc nâng trần kèm lý do"
        # Vết hỏng (tệp bị khoá, đĩa đầy) không được làm câm cổng an ninh.
        goc = ghi_vet
        def hong(*_):
            raise OSError("khoá")
        globals()["ghi_vet"] = hong
        try:
            con = ghi_cong({}, "pha-huy", "ask")
        except OSError:
            con = False
        finally:
            globals()["ghi_vet"] = goc
        assert con, "ghi vết hỏng làm câm cổng an ninh"
        assert luot_qua({"cong_cu": "Write", "tom_tat": "f"}, [{"loai": "goi", "cong_cu": "Read", "ok": True, "tom_tat": "f"},
                        {"loai": "goi", "cong_cu": "Write", "ok": True, "tom_tat": "f"}]) == 1, "Read cùng tệp tính là «qua»"
        # Hàm thuần: bàn giao §13 và mục «Tiếp theo».
        assert thieu_ban_giao([g(du_an)]) == ["_tu_kiem"], "ghi tệp repo mà không đòi bàn giao"
        assert thieu_ban_giao([g(du_an), g(goc_gia / "docs/knowledge/nhat_ky/2026-11-15.md")]) == [], "đã ghi nhật ký mà vẫn đòi"
        assert thieu_ban_giao([g(trang_thai), g(du_an)]) == ["_tu_kiem"], "ghi trang_thai TRƯỚC lần ghi cuối mà coi là xong"
        assert thieu_ban_giao([g(HOP_DONG / "x.md"), g(ngoai)]) == [], "tệp ngoài repo/ bị đòi bàn giao"
        # Tệp hướng dẫn (CLAUDE.md, AGENTS.md) không kéo theo cổng xác minh / bàn giao / báo cáo.
        hd_nho = [g(goc_gia / "CLAUDE.md"), g(goc_gia / "AGENTS.md")]
        assert thieu_ban_giao(hd_nho) == [] and thieu_xac_minh(hd_nho) == 0, "sửa CLAUDE.md/AGENTS.md mà bị giữ lượt"
        # Xác minh = skill + một lệnh chạy thành công, cả hai SAU lần ghi cuối.
        sk = {"loai": "goi", "cong_cu": "Skill", "ok": True, "tom_tat": SKILL_XAC_MINH}
        kt = {"loai": "goi", "cong_cu": "Bash", "ok": True, "tom_tat": "pytest"}
        assert thieu_xac_minh([g(du_an), sk]) == 1, "gọi skill xác minh mà không chạy lệnh kiểm nào vẫn cho qua"
        assert thieu_xac_minh([g(du_an), {**kt, "ok": False}, sk]) == 1, "lệnh kiểm hỏng mà tính là đã kiểm"
        assert thieu_xac_minh([kt, g(du_an), sk]) == 1, "lệnh kiểm TRƯỚC lần ghi cuối mà tính là đã kiểm"
        assert thieu_xac_minh([g(du_an), kt, sk]) == 0, "đã gọi skill + chạy lệnh kiểm mà vẫn giữ"
        # Mẫu lỗi sandbox: lấy từ lỗi thật trong transcript (26/11) + mã lỗi của các backend sandbox.
        for s in ["/usr/bin/bash: line 1: /probe.py: Permission denied", "Remove-Item : Access is denied",
                  "ls: cannot open 'x': Operation not permitted", "Error: EPERM: operation not permitted, open 'x'",
                  "PermissionError: [Errno 13] Permission denied: 'D:/x.csv'", "touch: x: Read-only file system",
                  "Error: EACCES: permission denied", "Error: EROFS: read-only file system"]:
            assert MAU_SANDBOX.search(s), f"lỗi quyền thật không khớp mẫu sandbox: {s!r}"
        assert not MAU_SANDBOX.search("SyntaxError: invalid syntax"), "lỗi mã bị coi là sandbox"
        # Bản chép CLAUDE.md ở D:\codevstdio lệch bản gốc -> cảnh báo đầu phiên.
        c1, c2 = tam / "c1.md", tam / "c2.md"
        c1.write_text("x", encoding="utf-8")
        c2.write_text("x", encoding="utf-8")
        assert lech_ban_cai(c1, c2) is None, "hai bản giống nhau mà báo lệch"
        c2.write_text("y", encoding="utf-8")
        assert "cai-dat.ps1" in (lech_ban_cai(c1, c2) or ""), "bản chép lệch mà không cảnh báo"
        assert "thiếu" in (lech_ban_cai(tam / "khong.md", c2) or ""), "thiếu bản chép mà không cảnh báo"
        assert muc_tiep_theo("# T\nđầu\n## Việc tiếp theo\n- b\n### con\n- c\n## Khác\n- d") == ("- b\n### con\n- c", True)
        assert muc_tiep_theo("# T\n" + "x" * 3000) == (("# T\n" + "x" * 3000)[:1500], False), "thiếu mục thì phải lấy 1,5 KB đầu"
        kn = tam / "r" / "docs" / "knowledge"
        kn.mkdir(parents=True)
        (kn / "trang_thai.md").write_text("# T\n## Next\n- viec A\n" + "y\n" * 4000, encoding="utf-8")
        bn = bo_nho_repo(tam / "r")
        assert "viec A" in "\n".join(bn) and len(bn) <= 15, bn
        assert any("6 KB" in d and "AGENTS.md" in d for d in bn), "thiếu cảnh báo trang_thai > 6 KB / thiếu AGENTS.md"
        # Cổng qua hook thật.
        lenh = lambda c: {"tool_name": "Bash", "tool_input": {"command": c}}
        assert "ghi vào .env" in chay("canh-cong", **lenh("echo x > .env")), "sót ghi .env"
        assert "in .env" in chay("canh-cong", **lenh("cat .env")), "sót in .env"
        assert '"deny"' in chay("canh-cong", **ghi(du_an)), "chưa gọi superpowers mà ghi tệp dự án vẫn lọt"
        cong = lambda ten, q: any(b.get("loai") == "cong" and b.get("cong") == ten and b.get("quyet") == q for b in doc_vet(sid))
        assert cong("superpowers", "deny"), "cổng bắn mà không ghi vết"
        assert chay("canh-cong", _env={"HARNESS_TAT": "doc-lon, superpowers"}, **ghi(du_an)) == "", "tắt cổng mà vẫn chặn"
        assert cong("superpowers", "tat"), "cổng tắt mà không ghi «lẽ ra đã bắn»"
        assert '"ask"' in chay("canh-cong", _env={"HARNESS_TAT": "pha-huy"}, **lenh("git push")), "tắt được cổng an ninh"
        assert chay("canh-cong", **ghi(ngoai)) == "", "tệp ngoài dự án bị chặn nhầm"
        chay("sau-cong-cu", **skill("superpowers:writing-plans"))
        assert chay("canh-cong", **ghi(du_an)) == "", "đã gọi superpowers mà vẫn bị chặn"
        chay("sau-cong-cu", **ghi(du_an))
        o = chay("ket-phien")
        assert '"block"' in o and SKILL_XAC_MINH in o and "§13" in o, "thiếu verification + bàn giao mà không giữ gộp một lần"
        assert cong("xac-minh", "block") and cong("ban-giao", "block"), "giữ lượt ở Stop mà không ghi vết"
        assert chay("ket-phien", stop_hook_active=True) == "", "giữ lượt lặp vô hạn"
        chay("sau-cong-cu", **skill(SKILL_XAC_MINH))
        assert "lệnh kiểm" in chay("ket-phien"), "gọi skill xác minh mà chưa chạy lệnh kiểm nào vẫn cho qua"
        chay("sau-cong-cu", **lenh("python -m pytest"))
        assert '"block"' not in chay("ket-phien"), "đã nhắc bàn giao cho lần ghi này rồi mà vẫn giữ lần hai"
        chay("sau-cong-cu", **ghi(du_an))
        chay("sau-cong-cu", **skill(SKILL_XAC_MINH))
        chay("sau-cong-cu", **lenh("python -m pytest"))
        o = chay("ket-phien")
        assert '"block"' in o and "§13" in o, "ghi mới sau lần nhắc mà không nhắc bàn giao lại"
        chay("sau-cong-cu", **ghi(du_an))
        chay("sau-cong-cu", **ghi(trang_thai))
        chay("sau-cong-cu", **skill(SKILL_XAC_MINH))
        chay("sau-cong-cu", **lenh("python -m pytest"))
        assert chay("ket-phien") == "", "đã ghi trang_thai.md sau lần ghi cuối mà vẫn bị giữ / nhắc §13 lần nữa"
        # §8: báo xong mà tin nhắn cuối không có nhãn báo cáo -> giữ lượt một lần cho mỗi đợt ghi.
        def tin(s):
            p = tam / "tx_bc.jsonl"
            p.write_text(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": s}]}}) + "\n",
                         encoding="utf-8")
            return str(p)
        assert chay("ket-phien", transcript_path=tin("ĐÃ KIỂM CHỨNG chạy x, đạt")) == "", "có nhãn §8 mà vẫn giữ lượt"
        assert "§8" in chay("ket-phien", transcript_path=tin("Xong rồi.")), "báo xong không nhãn §8 mà không giữ lượt"
        assert chay("ket-phien", transcript_path=tin("Xong rồi.")) == "", "giữ lượt §8 hai lần cho cùng đợt ghi"
        # Tổng kết tất định + `tim`.
        tx = tam / "transcript.jsonl"
        tx.write_text(json.dumps({"type": "user", "message": {"content": f"sửa giúp {sid} password=abc123"}}) + "\n"
                      + json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}})
                      + "\n", encoding="utf-8")
        chay("sau-cong-cu", hook_event_name="PostToolUseFailure", tool_name="Bash", tool_input={"command": "python hong.py"})
        chay("ket-phien", transcript_path=str(tx))
        tk = doc_json(VET_TONG_KET / f"{sid}.json", {})
        assert tk.get("lenh_that_bai") == ["python hong.py"], tk.get("lenh_that_bai")
        assert sid in tk.get("prompt_cuoi", "") and "abc123" not in tk["prompt_cuoi"], tk.get("prompt_cuoi")
        assert f"{sid}.json:" in chay("tim", sid), "`tim` không thấy tổng kết phiên"
        # Bị sandbox chặn: nhắc riêng, không tính vào ngắt mạch §7.
        sb = dict(hook_event_name="PostToolUseFailure", tool_name="Bash", tool_input={"command": "ls D:/sb"},
                  error="ls: cannot open 'D:/sb': Operation not permitted")
        assert "sandbox" in chay("sau-cong-cu", **sb), "lỗi sandbox mà không nhắc"
        assert "ngắt mạch" not in chay("sau-cong-cu", **sb), "lỗi sandbox bị tính vào ngắt mạch §7"
        lon.write_text("x" * 250_000, encoding="utf-8")
        doc = lambda **ts: {"tool_name": "Read", "tool_input": {"file_path": str(lon), **ts}}
        assert "§11" in chay("canh-cong", **doc()), "đọc trọn tệp lớn mà không bị chặn"
        assert chay("canh-cong", **doc(limit=50)) == "", "đọc có limit mà vẫn bị chặn"
        pdf = tam / "lon.pdf"
        pdf.write_bytes(b"%PDF" + b"x" * 250_000)
        doc_pdf = lambda **ts: {"tool_name": "Read", "tool_input": {"file_path": str(pdf), **ts}}
        assert "pages" in chay("canh-cong", **doc_pdf()), "đọc trọn PDF lớn mà không bị chặn"
        assert chay("canh-cong", **doc_pdf(pages="1-3")) == "", "PDF có pages mà vẫn bị chặn"
        nho = tam / "nho.txt"
        nho.write_text("abc", encoding="utf-8")
        doc_nho = {"tool_name": "Read", "tool_input": {"file_path": str(nho)}}
        chay("sau-cong-cu", **doc_nho)
        assert chay("canh-cong", **doc_nho) == "", "đọc lại lần 2 đã bị chặn"
        chay("sau-cong-cu", **lenh("echo xen giua"))
        chay("sau-cong-cu", **doc_nho)
        assert "đọc lại" in chay("canh-cong", **doc_nho), "đọc lần 3 tệp chưa đổi mà không bị chặn"
        os.utime(nho, (nho.stat().st_atime, nho.stat().st_mtime + 5))
        assert chay("canh-cong", **doc_nho) == "", "tệp đã đổi mà vẫn chặn đọc lại"
        chay("sau-cong-cu", **doc_nho)
        chay("sau-cong-cu", **doc_nho)
        o = chay("truoc-nen", cwd=str(tam), transcript_path=str(tx))
        assert "8 mục" in o and "Việc đang làm" in o, "PreCompact không đưa khuôn tóm tắt 8 mục cho bản nén"
        assert chay("canh-cong", **doc_nho) == "", "sau nén ngữ cảnh mà vẫn chặn đọc lại"
        goc_o = Path(tam.anchor)
        assert "gốc ổ đĩa" in chay("bat-dau", cwd=str(goc_o)), "mở phiên ở gốc ổ đĩa mà không cảnh báo"
        assert "gốc ổ đĩa" not in chay("bat-dau", cwd=str(tam)), "cảnh báo gốc ổ đĩa nhầm"
        assert "superpowers" in chay("do-cong"), "do-cong không thấy cổng của phiên giả"
        doc_lai = lambda **ts: {"tool_name": "Read", "tool_input": {"file_path": du_an, **ts}}
        o = [chay("sau-cong-cu", **doc_lai()) for _ in range(8)]
        assert "vòng lặp" not in o[3] and "vòng lặp" in o[4], "5 lượt giống hệt mà không cảnh báo"
        assert "đừng gọi lại" not in o[6] and "đừng gọi lại" in o[7], "8 lượt giống hệt mà không nhắc chi tiết"
        assert not any("vòng lặp" in chay("sau-cong-cu", **doc_lai(offset=i)) for i in range(5)), "khác offset mà báo lặp"
        # Hộp duyệt ngữ cảnh phải bắn TRƯỚC autoCompact 200K, và lời nhắc là mệnh lệnh checkpoint.
        tx_lon = tam / "tx_lon.jsonl"
        tx_lon.write_text(json.dumps({"type": "assistant", "message": {"usage": {"cache_read_input_tokens": 175_000}}}) + "\n",
                          encoding="utf-8")
        o = chay("canh-cong", transcript_path=str(tx_lon), **lenh("echo ok"))
        assert '"ask"' in o and "trang_thai.md" in o, "ngữ cảnh 175K mà không hỏi checkpoint"
        # PreCompact ghi trạng thái -> SessionStart(compact) cùng phiên chèn lại việc dở.
        chay("truoc-nen", cwd=str(tam), transcript_path=str(tx))
        o = chay("bat-dau", cwd=str(tam), source="compact")
        assert "a.md" in o and "python hong.py" in o, "sau nén không chèn lại tệp đã ghi / lệnh hỏng của chính phiên"
        assert "a.md" not in chay("bat-dau", cwd=str(tam), source="startup"), "phiên mới chèn nhầm trạng thái của chính nó"
        print("tự kiểm bắt buộc: đạt.")
    finally:
        tep_vet(sid).unlink(missing_ok=True)
        shutil.rmtree(tam, ignore_errors=True)
        (VET_TONG_KET / f"{sid}.json").unlink(missing_ok=True)


LENH = {"bat-dau": bat_dau, "canh-cong": canh_cong, "sau-cong-cu": sau_cong_cu,
        "ket-phien": ket_phien, "truoc-nen": lambda: ket_phien(truoc_nen=True), "quet": quet, "bao-cao": bao_cao, "do-cong": do_cong,
        "chi-muc": chi_muc, "do-ton": do_ton, "tim": tim, "tu-kiem-bat-buoc": tu_kiem_bat_buoc}


def main():
    # Windows mặc định cp1252: print tiếng Việt ném UnicodeEncodeError, bị nuốt -> lệnh chạy tay im lặng.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ten = sys.argv[1] if len(sys.argv) > 1 else ""
    ham = LENH.get(ten)
    if ham is None:
        sys.stderr.write("Dùng: harness.py " + " | ".join(LENH) + "\n")
        return 1
    try:
        ham()
    except Exception:
        if ham in (quet, bao_cao, do_cong, chi_muc, do_ton, tim, tu_kiem_bat_buoc):
            raise
        import traceback  # chỉ nhánh lỗi cần; nạp ở đầu tệp thì hook nào cũng trả ~95 ms
        LOG_LOI.parent.mkdir(parents=True, exist_ok=True)
        with LOG_LOI.open("a", encoding="utf-8") as f:
            f.write(f"{bay_gio()} {ten}\n{traceback.format_exc()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
