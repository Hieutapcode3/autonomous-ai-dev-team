# Git Workflow — Autonomous AI Dev Team

> Dự án này sử dụng **Git Flow** chuẩn. Mọi thay đổi đều đi qua nhánh feature → develop → release → main. Không commit thẳng lên `main` hay `develop`.

---

## Mục lục

1. [Cấu trúc nhánh](#1-cấu-trúc-nhánh)
2. [Quy tắc đặt tên nhánh](#2-quy-tắc-đặt-tên-nhánh)
3. [Quy tắc commit message](#3-quy-tắc-commit-message)
4. [Luồng làm việc hàng ngày](#4-luồng-làm-việc-hàng-ngày)
5. [Tạo Feature Branch](#5-tạo-feature-branch)
6. [Tạo Bugfix Branch](#6-tạo-bugfix-branch)
7. [Tạo Hotfix Branch](#7-tạo-hotfix-branch)
8. [Quy trình Release](#8-quy-trình-release)
9. [Pull Request & Review](#9-pull-request--review)
10. [Giải quyết Conflict](#10-giải-quyết-conflict)
11. [Tag & Versioning](#11-tag--versioning)
12. [Các lệnh thường dùng](#12-các-lệnh-thường-dùng)

---

## 1. Cấu trúc nhánh

```
main
│   Production-only. Luôn deployable.
│   Chỉ nhận merge từ release/* hoặc hotfix/*.
│   Mỗi merge vào main phải được tag version.
│
develop
│   Integration branch. Nơi các feature hội tụ.
│   Phải pass CI trước khi merge vào đây.
│
├── feature/<tên>          Tính năng mới
├── bugfix/<tên>           Sửa lỗi trên develop
├── release/<version>      Chuẩn bị release
└── hotfix/<tên>           Sửa lỗi khẩn cấp trên main
```

### Sơ đồ luồng

```
main    ─────────────────────────────────────────────── v1.0 ── v1.1 ──►
             ↑                                             ↑
             │                                       hotfix/xxx
             │                                             ↑
develop ─────┼──────────────────────────────── release/v1.0 ──────────►
             │       ↑           ↑                   ↑
             │  feature/A   feature/B           feature/C
```

---

## 2. Quy tắc đặt tên nhánh

| Loại | Prefix | Ví dụ |
|------|--------|-------|
| Tính năng mới | `feature/` | `feature/github-auto-push` |
| Sửa lỗi | `bugfix/` | `bugfix/websocket-reconnect` |
| Hotfix production | `hotfix/` | `hotfix/token-validation-crash` |
| Release | `release/` | `release/v1.1.0` |
| Thử nghiệm | `experiment/` | `experiment/streaming-llm` |

**Quy tắc:**
- Dùng chữ thường, nối bằng dấu `-`
- Không dùng dấu cách, ký tự đặc biệt, tiếng Việt có dấu
- Tên ngắn gọn, rõ mục đích (tối đa 5 từ)

---

## 3. Quy tắc commit message

Dùng chuẩn **[Conventional Commits](https://www.conventionalcommits.org/)**.

### Cú pháp

```
<type>(<scope>): <mô tả ngắn>

[body - tùy chọn, mô tả chi tiết]

[footer - tùy chọn, ví dụ: Closes #123]
```

### Các type hợp lệ

| Type | Dùng khi |
|------|---------|
| `feat` | Thêm tính năng mới |
| `fix` | Sửa bug |
| `chore` | Cấu hình, build, dependencies |
| `docs` | Chỉ thay đổi tài liệu |
| `refactor` | Refactor code, không thêm feature/fix bug |
| `test` | Thêm/sửa test |
| `perf` | Cải thiện performance |
| `ci` | Thay đổi CI/CD pipeline |
| `style` | Format code (không ảnh hưởng logic) |
| `revert` | Revert commit trước |

### Ví dụ

```bash
# Tốt ✅
feat(backend): add GitHub auto-push after DAG completes
fix(websocket): handle reconnect when server restarts
chore(deps): upgrade next.js to 16.3.8
docs: add git workflow guide

# Không tốt ❌
update code
fix bug
wip
```

### Breaking Change

```bash
feat(api)!: change session endpoint response schema

BREAKING CHANGE: /api/sessions now returns `task_map` instead of `tasks`
```

---

## 4. Luồng làm việc hàng ngày

```bash
# 1. Luôn bắt đầu bằng cách cập nhật develop
git checkout develop
git pull origin develop

# 2. Tạo nhánh feature từ develop
git checkout -b feature/ten-tinh-nang

# 3. Code, commit thường xuyên (nhỏ, rõ ràng)
git add <files>
git commit -m "feat(scope): mô tả"

# 4. Đẩy nhánh lên remote để backup và review
git push -u origin feature/ten-tinh-nang

# 5. Tạo Pull Request trên GitHub: feature → develop
# 6. Sau khi được review và approve → merge
# 7. Xóa nhánh feature sau khi merge
```

---

## 5. Tạo Feature Branch

### Bước 1 — Cập nhật develop

```bash
git checkout develop
git pull origin develop
```

### Bước 2 — Tạo nhánh

```bash
git checkout -b feature/<tên-tính-năng>

# Ví dụ thực tế trong dự án này:
git checkout -b feature/dag-visualization
git checkout -b feature/cost-tracking
git checkout -b feature/multi-provider-llm
```

### Bước 3 — Phát triển và commit

```bash
# Commit thường xuyên, từng unit nhỏ
git add backend/app/planner.py
git commit -m "feat(planner): add topological batch ordering"

git add frontend/components/DAGCanvas.tsx
git commit -m "feat(ui): render live DAG nodes with React Flow"
```

### Bước 4 — Sync với develop (tránh conflict lớn)

```bash
git fetch origin
git rebase origin/develop

# Hoặc nếu không dùng rebase:
git merge origin/develop
```

### Bước 5 — Push và tạo Pull Request

```bash
git push -u origin feature/<tên-tính-năng>
# → Vào GitHub tạo PR: feature/* → develop
```

### Bước 6 — Sau khi merge PR

```bash
# Xóa nhánh local
git branch -d feature/<tên-tính-năng>

# Xóa nhánh remote
git push origin --delete feature/<tên-tính-năng>
```

---

## 6. Tạo Bugfix Branch

Dùng cho lỗi phát hiện trên `develop` (không phải production).

```bash
# Tạo từ develop
git checkout develop
git pull origin develop
git checkout -b bugfix/websocket-reconnect

# Fix lỗi, commit
git add <files>
git commit -m "fix(websocket): handle reconnect when server restarts unexpectedly"

# Push và tạo PR về develop
git push -u origin bugfix/websocket-reconnect

# Sau khi merge, dọn nhánh
git checkout develop
git pull origin develop
git branch -d bugfix/websocket-reconnect
git push origin --delete bugfix/websocket-reconnect
```

---

## 7. Tạo Hotfix Branch

Dùng khi `main` có lỗi nghiêm trọng cần sửa ngay, không chờ release cycle.

```bash
# Bắt buộc tạo từ main
git checkout main
git pull origin main
git checkout -b hotfix/token-validation-crash

# Fix lỗi
git add <files>
git commit -m "fix(auth): prevent crash when github token is malformed"

# Push lên remote
git push -u origin hotfix/token-validation-crash
```

### Merge hotfix vào cả main VÀ develop

```bash
# 1. Merge vào main
git checkout main
git merge --no-ff hotfix/token-validation-crash -m "Merge hotfix/token-validation-crash into main"
git tag -a v1.0.1 -m "v1.0.1 - Fix token validation crash"
git push origin main --tags

# 2. Back-merge vào develop (bắt buộc!)
git checkout develop
git merge --no-ff hotfix/token-validation-crash -m "Merge hotfix/token-validation-crash into develop"
git push origin develop

# 3. Dọn nhánh
git branch -d hotfix/token-validation-crash
git push origin --delete hotfix/token-validation-crash
```

> **Lưu ý:** Không bao giờ quên merge hotfix về `develop`. Nếu bỏ qua, lỗi sẽ tái xuất ở release tiếp theo.

---

## 8. Quy trình Release

Khi `develop` ổn định và sẵn sàng release.

### Bước 1 — Tạo release branch từ develop

```bash
git checkout develop
git pull origin develop
git checkout -b release/v1.1.0
```

### Bước 2 — Chuẩn bị release

```bash
# Chỉ commit các thay đổi liên quan release:
# - Bump version trong package.json, pyproject.toml...
# - Cập nhật CHANGELOG.md
# - Sửa bug nhỏ phát hiện trong quá trình test

git commit -m "chore(release): bump version to v1.1.0"
git commit -m "docs: update CHANGELOG for v1.1.0"
```

### Bước 3 — Merge vào main

```bash
git checkout main
git merge --no-ff release/v1.1.0 -m "Merge branch 'release/v1.1.0' into main"
```

### Bước 4 — Tạo tag

```bash
git tag -a v1.1.0 -m "v1.1.0 - <mô tả tóm tắt>"
```

### Bước 5 — Back-merge vào develop

```bash
git checkout develop
git merge --no-ff release/v1.1.0 -m "Merge branch 'release/v1.1.0' back into develop"
```

### Bước 6 — Push tất cả

```bash
git push origin main develop --tags

# Xóa release branch
git branch -d release/v1.1.0
git push origin --delete release/v1.1.0
```

---

## 9. Pull Request & Review

### Checklist trước khi tạo PR

- [ ] Code chạy local không có lỗi
- [ ] Đã viết/cập nhật test nếu cần
- [ ] Commit message theo Conventional Commits
- [ ] Branch đã được rebase/merge với develop mới nhất
- [ ] Không commit file nhạy cảm (`.env`, token, key)
- [ ] PR description mô tả rõ: làm gì, tại sao, test như nào

### Template PR Description

```markdown
## Mô tả
<!-- Tóm tắt thay đổi và lý do -->

## Loại thay đổi
- [ ] Bug fix
- [ ] Tính năng mới
- [ ] Breaking change
- [ ] Tài liệu

## Cách test
1. Chạy backend: `python backend/run.py`
2. Chạy frontend: `cd frontend && npm run dev`
3. Mở http://localhost:3000 và...

## Screenshots (nếu có UI)
```

### Quy tắc review

- Tối thiểu **1 người approve** trước khi merge
- Dùng **Squash merge** cho feature branch nhỏ, **Merge commit** (`--no-ff`) cho feature lớn
- Không self-merge (trừ hotfix khẩn cấp)

---

## 10. Giải quyết Conflict

```bash
# Khi rebase bị conflict
git rebase origin/develop
# → Conflict xuất hiện

# 1. Mở file conflict, chỉnh sửa vùng <<<< >>>> ====
# 2. Stage file đã sửa
git add <file-da-sua>

# 3. Tiếp tục rebase
git rebase --continue

# Nếu muốn hủy và về trạng thái cũ
git rebase --abort
```

### Tips tránh conflict

```bash
# Sync develop vào nhánh mình thường xuyên (mỗi ngày)
git fetch origin
git rebase origin/develop

# Commit nhỏ, thường xuyên thay vì 1 commit khổng lồ
# Tránh để nhánh sống quá lâu (> 3-5 ngày) mà không sync
```

---

## 11. Tag & Versioning

Dự án dùng **Semantic Versioning**: `MAJOR.MINOR.PATCH`

| Phần | Tăng khi |
|------|---------|
| `MAJOR` | Breaking changes, API không tương thích ngược |
| `MINOR` | Tính năng mới, backward-compatible |
| `PATCH` | Bug fix, backward-compatible |

```bash
# Xem tất cả tags
git tag -l

# Tạo annotated tag (dùng cho release)
git tag -a v1.2.0 -m "v1.2.0 - Add streaming LLM support"

# Push tag lên remote
git push origin v1.2.0

# Push tất cả tags cùng lúc
git push origin --tags

# Xóa tag nhầm (local + remote)
git tag -d v1.2.0
git push origin --delete v1.2.0
```

---

## 12. Các lệnh thường dùng

### Xem trạng thái

```bash
# Xem tất cả nhánh (local + remote)
git branch -a

# Xem graph commit đẹp
git log --oneline --graph --all --decorate

# Xem thay đổi chưa commit
git status
git diff

# Xem lịch sử file cụ thể
git log --follow -p backend/app/orchestrator.py
```

### Quản lý nhánh

```bash
# Đổi tên nhánh
git branch -m ten-cu ten-moi

# Xóa nhánh local (đã merge)
git branch -d feature/ten-nhanh

# Xóa nhánh local (chưa merge, cẩn thận!)
git branch -D feature/ten-nhanh

# Xóa nhánh remote
git push origin --delete feature/ten-nhanh

# Dọn các remote-tracking branches đã xóa trên remote
git remote prune origin
```

### Undo & Sửa lỗi

```bash
# Sửa commit message gần nhất (chưa push)
git commit --amend -m "feat: message đúng"

# Thêm file quên vào commit gần nhất (chưa push)
git add ten-file-quen
git commit --amend --no-edit

# Undo commit gần nhất (giữ code, bỏ commit)
git reset --soft HEAD~1

# Undo commit gần nhất (bỏ luôn code - cẩn thận!)
git reset --hard HEAD~1

# Revert 1 commit đã push (tạo commit mới đảo ngược)
git revert <commit-sha>

# Lưu tạm thay đổi chưa commit
git stash
git stash pop          # lấy lại thay đổi
git stash list         # xem danh sách stash
```

### Sync & Remote

```bash
# Cập nhật tất cả remote về local
git fetch --all --prune

# Pull với rebase thay vì merge commit
git pull --rebase origin develop

# Xem remote hiện tại
git remote -v

# Thêm remote
git remote add origin https://github.com/Hieutapcode3/autonomous-ai-dev-team.git
```

---

## Tóm tắt nhanh (Quick Reference Card)

```
Việc cần làm                      Lệnh
────────────────────────────────────────────────────────────────────
Bắt đầu feature mới               git checkout develop && git pull
                                   git checkout -b feature/ten

Commit code                        git add <files>
                                   git commit -m "feat(scope): mô tả"

Đẩy nhánh lên remote              git push -u origin feature/ten

Sync develop vào nhánh            git fetch origin && git rebase origin/develop

Merge feature vào develop          Pull Request trên GitHub (--no-ff)

Tạo release                        git checkout -b release/vX.Y.Z  (từ develop)

Merge release vào main             git checkout main
                                   git merge --no-ff release/vX.Y.Z
                                   git tag -a vX.Y.Z -m "..."
                                   git push origin main --tags

Back-merge release về develop      git checkout develop
                                   git merge --no-ff release/vX.Y.Z

Hotfix production                  git checkout main
                                   git checkout -b hotfix/ten
                                   ... fix & commit ...
                                   Merge vào cả main VÀ develop + tag
```

---

> **5 nguyên tắc vàng:**
> 1. `main` luôn deployable — không commit trực tiếp
> 2. `develop` luôn buildable — phải pass CI
> 3. Commit nhỏ, thường xuyên, message rõ ràng
> 4. Không bao giờ force push lên `main` hay `develop`
> 5. Hotfix phải back-merge về cả `develop`
