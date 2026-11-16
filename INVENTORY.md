# INVENTORY — những gì harness đang có

> Sinh tự động bởi `python ~/.claude/harness/harness.py quet` lúc 2026-11-15T11:38:56. **Đừng sửa tay.**
> Dùng để TRA CỨU «tổng thể có gì». Chọn công cụ theo loại việc: `DINH-TUYEN.md`.
> Tên để gọi luôn lấy từ danh sách của phiên hiện tại — skill của plugin «tắt» không gọi được.

| Nguồn | Trạng thái | Skill | Lệnh | Agent |
| --- | --- | ---: | ---: | ---: |
| caveman@caveman c72984e4392c | tắt | 20 | 5 | 3 |
| claude-mem@thedotmack 15.18.3 | tắt | 30 | 0 | 0 |
| mattpocock-skills@claude-plugins-official 1.3.1 | bật | 0 | 0 | 0 |
| ponytail@ponytail 4.9.0 | bật | 6 | 0 | 0 |
| superpowers@claude-plugins-official 7.0.2 | bật | 15 | 0 | 0 |
| ~/.claude (người dùng) | bật | 2 | 0 | 0 |

**Tổng: 81 mục.**

## ponytail@ponytail 4.9.0 — bật

### Skill (6)

- `ponytail:ponytail` — Forces the laziest solution that actually works, simplest, shortest, most minimal. Channels a senior dev who has seen everything: question whether the task need
- `ponytail:ponytail-audit` — Whole-repo audit for over-engineering. Like ponytail-review, but scans the entire codebase instead of a diff: a ranked list of what to delete, simplify, or repl
- `ponytail:ponytail-debt` — Harvest every `ponytail:` comment in the codebase into a debt ledger, so the deliberate shortcuts and deferrals ponytail leaves behind get tracked instead of ro
- `ponytail:ponytail-gain` — Show ponytail's measured impact as a compact scoreboard: less code, less cost, more speed, from the benchmark medians. One-shot display, not a persistent mode, 
- `ponytail:ponytail-help` — Quick-reference card for all ponytail modes, skills, and commands. One-shot display, not a persistent mode. Trigger: /ponytail-help, "ponytail help", "what pony
- `ponytail:ponytail-review` — Code review focused exclusively on over-engineering. Finds what to delete: reinvented standard library, unneeded dependencies, speculative abstractions, dead fl

## superpowers@claude-plugins-official 7.0.2 — bật

### Skill (15)

- `superpowers:brainstorming` — You MUST use this before any creative work - creating features, building components, adding functionality, modifying behavior, or planning anything new, in soft
- `superpowers:diagnosing-superpowers` — Use when a superpowers session went wrong and your human partner wants to know why — repeated work, ignored plans, stumbles, poor results, a skill that didn't f
- `superpowers:dispatching-parallel-agents` — Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
- `superpowers:executing-plans` — Use when executing an implementation plan in the current session as the implementer yourself — your human partner chose inline execution, or no subagent tool is
- `superpowers:finishing-a-development-branch` — Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
- `superpowers:receiving-code-review` — Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical 
- `superpowers:requesting-code-review` — Use when completing tasks, implementing major features, or before merging to verify work meets requirements
- `superpowers:subagent-driven-development` — Use when executing implementation plans with independent tasks in the current session
- `superpowers:systematic-debugging` — Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
- `superpowers:test-driven-development` — Use when implementing any feature or bugfix, before writing implementation code
- `superpowers:using-git-worktrees` — Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via n
- `superpowers:using-superpowers` — Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
- `superpowers:verification-before-completion` — Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output be
- `superpowers:writing-plans` — Use when you have a spec or requirements for a multi-step task, before touching code
- `superpowers:writing-skills` — Use when creating new skills, editing existing skills, or verifying skills work before deployment

## ~/.claude (người dùng) — bật

### Skill (2)

- `find-skills` — Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for X", "is there a skill that can...", or express int
- `task-observer` — Monitors task execution for skill improvement opportunities: logs patterns, user corrections and methodology worth preserving to the workspace, turns them into 
