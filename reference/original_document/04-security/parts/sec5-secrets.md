# §5 — Secrets & Hạ tầng (Security Audit Phase 4)

> Phạm vi: nơi lưu secret, rò rỉ secret trong git history, quyền DB, so sánh secret không timing-safe, các file nhạy cảm (dev.db / dump PII / Python function public).
> Phương pháp: đọc code + config THẬT tại worktree `cranky-austin`, chạy `git log/grep`, so khớp hash secret hiện hành vs lịch sử. **Không in giá trị secret** — chỉ tên biến + bằng chứng file:line/commit. Ngày audit: 2026-08-02.
> Đối chiếu audit cũ: một số fix cũ (JWT fail-closed R1, INNGEST_DEV P5-005) ĐÃ có trong code hiện tại (xác minh bên dưới); nhưng rò rỉ credential DB thì CHƯA xử lý.

---

## 0. Tóm tắt (mức độ)

| ID | Vấn đề | Mức |
|---|---|---|
| SEC5-01 | Connection string Neon prod (role `neondb_owner`, full-priv) bị commit vào **history nhánh main** và **chưa xoay khóa** — hash khớp `.env` hiện hành | **Critical** |
| SEC5-02 | `prisma/dev.db` (SQLite) đang tracked — chứa user thật + bcrypt hash + **2 mật khẩu plaintext** | **High** |
| SEC5-03 | `api/scoring.py` public Vercel function: auth **fail-open**, nối thẳng prod DB, chạy UPDATE bảng `Client` | **High** |
| SEC5-04 | `api/vdownloader.py` public Vercel function: **KHÔNG xác thực** — open download-proxy, subprocess yt-dlp theo URL người dùng | **High** |
| SEC5-05 | Dump PII/tài chính thật tracked: `all_users_output.txt`, `all_tasks_kcd.txt`, `pending_tasks_export.md` | **Medium** |
| SEC5-06 | App kết nối DB bằng role owner `neondb_owner` — không least-privilege | **Medium** |
| SEC5-07 | `JWT_SECRET` trong `.env` là chuỗi yếu/đoán được; guard fail-closed chỉ bắt đúng 1 placeholder | **Medium** |
| SEC5-08 | 6/7 cron so sánh CRON_SECRET không timing-safe (`key !== secret`) | **Low** |
| SEC5-09 | `/api/test-email` nhận CRON_SECRET qua query param `?secret=` | **Low** |

Điểm LÀM ĐÚNG (không phải finding — xem §6): `.env` gitignore đúng & chưa từng bị commit; `.env.example` sạch; `INTEGRATION_TOKEN_SECRET`/`REVIEW_COOKIE_SECRET` dùng chuẩn (AES-256-GCM/JWT, fail-closed); env.ts fail-closed JWT + INNGEST_DEV.

---

## 1. (a) Secrets đang nằm ở đâu

### 1.1. File `.env` (KHÔNG in giá trị — chỉ tên biến)

Toàn bộ secret nằm trong `.env` (10.588 bytes, tại root, **không** tracked). Các biến có mặt (`.env:10-99`):

| Nhóm | Tên biến |
|---|---|
| Database | `DATABASE_URL` (Neon, role `neondb_owner`) |
| Auth/session | `JWT_SECRET`, `CRON_SECRET` |
| Email | `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `ADMIN_EMAIL` |
| Dịch thuật | `GPT4_API_KEY` |
| Supabase | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` |
| LiveKit (dead-dep) | `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `NEXT_PUBLIC_LIVEKIT_URL` |
| Rate-limit | `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` |
| Turnstile (env mồ côi) | `NEXT_PUBLIC_TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` |
| OAuth integrations | `INTEGRATION_TOKEN_SECRET`, `DROPBOX_CLIENT_ID/SECRET`, `GOOGLE_CLIENT_ID/SECRET` |
| Cloudflare Stream (env mồ côi) | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_STREAM_API_TOKEN`, `CLOUDFLARE_STREAM_CUSTOMER_SUBDOMAIN`, `CLOUDFLARE_STREAM_KEY_ID`, `CLOUDFLARE_STREAM_KEY_PEM` |
| Web-push | `NEXT_PUBLIC_VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` |
| Review module (R2/Mux/Inngest) | `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `MUX_TOKEN_ID`, `MUX_TOKEN_SECRET`, `MUX_WEBHOOK_SECRET`, `MUX_SIGNING_KEY_ID`, `MUX_SIGNING_PRIVATE_KEY`, `INNGEST_EVENT_KEY`, `INNGEST_SIGNING_KEY`, `REVIEW_COOKIE_SECRET` |

> Ghi chú vệ sinh: nhiều secret của service ĐÃ chết/mồ côi vẫn nằm trong `.env` (LiveKit, Cloudflare Stream `KEY_PEM`, Turnstile) — nên thu hồi/xóa khỏi provider dù không phải lỗ hổng trực tiếp.

### 1.2. `env.ts` — validate rất mỏng (`src/lib/env.ts:5-9`)

Chỉ validate **3 biến** qua zod: `DATABASE_URL`, `JWT_SECRET` (min 10), `NODE_ENV`. Toàn bộ ~40 secret còn lại đọc ad-hoc `process.env.*` rải rác, không có schema tập trung → dễ thiếu biến mà không fail sớm. Có 3 guard fail-closed hữu ích (đã verify):
- JWT_SECRET = placeholder trong production → `throw` (`env.ts:37-42`, fix "AUDIT R1").
- `INNGEST_DEV` truthy trong production → `throw` (bỏ verify chữ ký webhook Inngest) (`env.ts:53-60`, fix "P5-005").
- Thiếu `INNGEST_SIGNING_KEY` trong production → chỉ log lỗi (`env.ts:61-63`).

---

## 2. (b) Rò rỉ secret trong GIT HISTORY — **SEC5-01 (Critical)**

### 2.1. `.env` chưa từng bị commit (tốt)

`git log --all --full-history -- .env` = **rỗng**. `git log -S` cho `RESEND_API_KEY`, `CRON_SECRET`, `REVIEW_COOKIE_SECRET`, `INTEGRATION_TOKEN_SECRET`, `SUPABASE service_role`, `MUX_TOKEN_SECRET`, `R2_SECRET_ACCESS_KEY` = **0 commit**. Nghĩa là các secret này chỉ sống trong `.env` local + Vercel env, không lọt git.

### 2.2. NHƯNG connection string DB thì ĐÃ LỌT — và vẫn còn hiệu lực

`git log --all -S "npg_"` (npg_ = prefix mật khẩu Neon) ra 4 commit **đều reachable từ `main`** (đã verify `git merge-base --is-ancestor <c> main` = YES cho cả 4):

| Commit | Ngày | File chứa connection string |
|---|---|---|
| `ed46780` | 2026-03-06 | `check-user.ts` (thêm — `git show ed46780:check-user.ts` dòng 9: `new Pool({ connectionString: "postgresql://neondb_owner:npg_…@ep-autumn-flower-…neon.tech/neondb…" })`) |
| `2c7e226` | — | `test-neon.ts` (thêm cùng chuỗi) |
| `f0fafd7` | — | xóa `check-user.ts` |
| `99dced1` | — | xóa `test-neon.ts` |

Hai file đã bị **xóa khỏi HEAD** (`git ls-files check-user.ts test-neon.ts` = rỗng) nhưng **secret còn nguyên trong history** và ai clone repo cũng `git show ed46780:check-user.ts` đọc được.

**Bằng chứng credential VẪN LÀ CÁI ĐANG DÙNG (chưa xoay khóa):** so khớp hash (không in giá trị):

```
sha256(password npg_ trong .env hiện tại)        = 20e1a20f…766c7b
sha256(password npg_ trong ed46780 + 2c7e226)    = 20e1a20f…766c7b   ← KHỚP
sha256(host ep-… trong .env)                     = e1103b82…082d55
sha256(host ep-… trong history)                  = e1103b82…082d55   ← KHỚP
```

→ Mật khẩu + host trong git history **trùng khít** `DATABASE_URL` prod hiện hành (`.env:10`). Role là `neondb_owner` (chủ DB Neon, full quyền). Bất kỳ ai có quyền đọc repo (GitHub) đều lấy được credential prod còn sống.

**Fix:** (1) XOAY NGAY mật khẩu Neon `neondb_owner` (Neon console → Reset password) + cập nhật Vercel env — đây là việc gấp nhất. (2) Sau khi xoay, cân nhắc purge history (`git filter-repo`/BFG) để gỡ chuỗi cũ, dù giá trị đã vô hiệu. (3) Không bao giờ hardcode connection string vào script debug — dùng `process.env`.

### 2.3. Quét rộng file tracked hiện tại: sạch

`git grep -nIE "(re_…|signkey-prod-|sk-acc-|AKIA…|npg_…|eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVC)" HEAD` (trừ `.env.example`, `electron/release/**`) → **0 secret thật**; 2 hit chỉ là doc mô tả *format* key (`IMPLEMENTATION-NOTES.md:37`, `scripts/probe-review-provisioning.ts:146`). Trong HEAD, các `postgresql://` còn lại đều là placeholder mẫu (`electron/assets/setup-wizard.html:302`, `mcp-server/claude_desktop_config.example.json:7`). ⇒ Không có secret sống hardcode trong source hiện tại; rủi ro nằm ở **history** (SEC5-01) + **dev.db** (SEC5-02).

---

## 3. (c) `.env` có bị .gitignore đúng không — ĐÚNG

| Kiểm tra | Kết quả |
|---|---|
| `git check-ignore .env` | in `.env`, exit 0 → **đã ignore** |
| `.gitignore` | dòng 34 `.env*` (kèm comment dòng 33) |
| `git ls-files \| grep -i env` | chỉ `.env.example` (tracked, đã đọc — **sạch**, toàn biến rỗng, `.env.example:1-24`) |
| File local | `.env`, `.env.example`, `.env.test` tồn tại; `.env` và `.env.test` KHÔNG tracked |

→ Cấu hình gitignore đúng. (Lưu ý phụ: pattern `.env*` cũng match `.env.example`, nhưng file này đã tracked từ trước nên vẫn theo repo; nội dung sạch nên không sao.)

---

## 4. (d) Quyền truy cập DB — **SEC5-06 (Medium)**

- Connection string dùng role **`neondb_owner`** (`.env:10`) — đây là owner role mặc định của Neon, có full DDL + DML (CREATE/DROP/ALTER/DELETE) trên `neondb`. App đọc qua `POSTGRES_URL || DATABASE_URL` (`src/lib/env.ts:19`, `src/lib/db.ts`).
- **Không có tách quyền**: mọi truy vấn runtime của app, mọi cron, cả 2 Python function (`api/scoring.py:23`, khi còn sống) đều dùng CHUNG một role owner. Không có role app-level chỉ SELECT/INSERT/UPDATE/DELETE trên schema `public`.
- Hệ quả: một lỗ SQLi hoặc app-compromise = toàn quyền DB (kể cả DROP bảng, đọc mọi tenant). Cũng chính vì role rò rỉ ở SEC5-01 là owner nên thiệt hại tối đa.

**Fix:** tạo Neon role riêng cho app với quyền tối thiểu (GRANT SELECT/INSERT/UPDATE/DELETE trên schema `public`, KHÔNG cấp owner/CREATE/DROP); giữ `neondb_owner` chỉ cho migration (`prisma db push`) chạy tách biệt. Kết hợp với xoay khóa ở SEC5-01.

---

## 5. Các secret & file nhạy cảm khác

### 5.1. (e) So sánh secret không timing-safe & dùng secret

**SEC5-08 (Low) — CRON_SECRET 6/7 cron không timing-safe.** Chỉ `auth-cleanup` dùng `timingSafeEqual` (`src/app/api/cron/auth-cleanup/route.ts:19-25,37` — hàm `safeEqual`, "H1 fix"). 6 cron còn lại so sánh chuỗi thường `if (key !== secret)`: `send-digest/route.ts:26`, và tương tự `check-deadline`, `cleanup-notifications`, `hard-delete-workspaces`, `hard-delete-profiles`, `review-janitor`. `api/scoring.py:15` cũng so sánh thường. Rủi ro timing side-channel qua mạng thực tế thấp (jitter lớn) nhưng nên đồng nhất về `timingSafeEqual`.

**REVIEW_COOKIE_SECRET — dùng ĐÚNG (không phải finding).** `src/lib/review/share-auth.ts:43-45`: đọc env, **fail-closed** nếu thiếu hoặc <32 byte (`throw`), dùng ký JWT HS256 cho cookie `rv_unlock_{slug}`.

**INTEGRATION_TOKEN_SECRET — dùng ĐÚNG (không phải finding).** `src/lib/token-encryption.ts:19-33`: AES-256-GCM, validate đúng 64 hex (32 byte), fail-closed nếu thiếu/sai độ dài; format `base64(iv[12]+authTag[16]+ciphertext)`, có `setAuthTag` khi giải mã (`token-encryption.ts:39-72`). Đây là mẫu chuẩn để nhân rộng.

**SEC5-07 (Medium) — JWT_SECRET yếu.** `.env:11` đặt `JWT_SECRET="super-secret-key-at-least-32-chars-long-for-safety"` — chuỗi mô tả/đoán được, không phải random. Guard `env.ts:37` chỉ chặn đúng 1 placeholder `"temporary-build-secret-key-change-me"` (`env.ts:3`), KHÔNG bắt secret yếu này. Nếu prod (Vercel) cũng dùng giá trị này thì kẻ tấn công đoán được có thể **ký giả JWT session** (giả mạo mọi role — session là HS256 jose, xem parts/09). *Không xác minh được giá trị prod trên Vercel từ repo* → cần chủ dự án kiểm tra Vercel env và thay bằng 32+ byte random nếu trùng.

**SEC5-09 (Low) — test-email nhận secret qua query.** `src/app/api/test-email/route.ts:12-18`: chấp nhận `url.searchParams.get('secret')` làm CRON_SECRET → secret lọt access log / Referer / lịch sử trình duyệt. File tự ghi "DELETE after debugging" (`route.ts:3`) nhưng vẫn sống. **Fix:** xóa route hoặc bỏ nhánh query-param, chỉ nhận qua header.

### 5.2. (f) `prisma/dev.db` + Python function public

**SEC5-02 (High) — `prisma/dev.db` (SQLite) tracked chứa credential/PII thật.** `git ls-files prisma/dev.db` = tracked (commit cũ nhất repo, 2026-01-24). Datasource thật là Postgres/Neon (`prisma/schema.prisma:7`) nên đây là DB prototype cũ nhưng **dữ liệu là thật**:
- Bảng `User` = 5 hàng thật: 1 `ADMIN` + 4 `USER`; cột `password` chứa bcrypt hash `$2b$10$…` (60 ký tự) của cả 5.
- Cột **`plainPassword`** (KHÔNG có trong schema live — verify `grep plainPassword prisma/schema.prisma` = 0) chứa **mật khẩu plaintext của 2 user** (độ dài 9 và 10 ký tự).
- Bảng `Task` = 2 hàng.

→ Username + bcrypt hash + 2 mật khẩu plaintext của user thật đang nằm trong git history công khai. Nếu user còn dùng lại mật khẩu đó trên prod (cùng username) → lộ tài khoản. **Fix:** `git rm --cached prisma/dev.db`, thêm `*.db`/`prisma/dev.db` vào `.gitignore`, purge khỏi history, và **bắt 2 user đó đổi mật khẩu** trên prod. (Điểm cộng: schema/app live KHÔNG lưu plaintext — chỉ dev.db cũ.)

**SEC5-04 (High) — `api/vdownloader.py` public không xác thực.** Tracked + deploy qua `vercel.json:3-5` (`"functions": {"api/*.py": {"maxDuration": 10}}`) → endpoint sống `/api/vdownloader`. `do_GET` (`api/vdownloader.py:45`) **không có bất kỳ check auth nào**: bất kỳ ai gọi `?url=<youtube>` sẽ khiến server chạy `subprocess.Popen(["yt-dlp", … video_url])` (`vdownloader.py:151-169`) tải/stream video tùy ý → lạm dụng băng thông/compute, dùng `YOUTUBE_COOKIES` (cookie YouTube ghi ra `/tmp`, `vdownloader.py:33-38`); còn có `?diagnostic=true` lộ python version/cwd (`vdownloader.py:56-77`). Không code nào trong repo gọi tới (dead nhưng vẫn deploy). **Fix:** xóa `api/vdownloader.py` + block `api/*.py` trong `vercel.json` + `requirements.txt`.

**SEC5-03 (High) — `api/scoring.py` public, auth fail-open, ghi thẳng DB.** Cùng cơ chế deploy. `do_POST` (`api/scoring.py:10`) check: `if cron_secret and auth_header != f"Bearer {cron_secret}": 401` (`scoring.py:15`) — **fail-open**: nếu env `CRON_SECRET` KHÔNG set trong scope của function thì bỏ qua auth hoàn toàn. Khi qua cửa, nó parse `DATABASE_URL` (`scoring.py:23-38`) nối thẳng Postgres bằng `pg8000` (role owner) và chạy `UPDATE "Client" SET "aiScore"/"frictionIndex"/"tier"` hàng loạt (`scoring.py:111-115`). So sánh secret cũng plain-compare (`scoring.py:15`). Dead code, không ai giám sát. **Fix:** xóa cùng `vdownloader.py`; nếu muốn giữ, đổi sang fail-closed (`if not cron_secret or not hmac.compare_digest(...)`).

### 5.3. (b bổ sung) Dump PII/tài chính tracked — **SEC5-05 (Medium)**

`git ls-files` xác nhận tracked: `all_users_output.txt`, `all_tasks_kcd.txt`, `missing_task_findings.txt` (0 byte), `pending_tasks_export.md`. Nội dung `all_users_output.txt` (7 dòng) là output script `check-*` cũ: tên user thật + **giá trị tiền VND** ("User: Vincent … Total Value 3.600.000 VND") — không có password hash, nhưng là **PII + số liệu tài chính nội bộ** commit lên repo. `all_tasks_kcd.txt` (10KB) là dump task. **Fix:** `git rm --cached` + gitignore + (tùy) purge history; các dump dữ liệu thật không nên nằm trong repo.

> Ngoài repo (local, untracked — theo parts/11, nhắc lại để xử lý): `.tmp/video-report/chrome-*-history.sqlite` (44MB lịch sử trình duyệt thật), `.codex-studyplace-dev.log` (135MB). Không lọt git nhưng nên xóa khỏi máy.

---

## 6. Điểm làm ĐÚNG (không phải finding — để không đề xuất thừa)

| Hạng mục | Bằng chứng |
|---|---|
| `.env` gitignore + chưa từng commit | `git check-ignore .env` exit 0; `git log -- .env` rỗng; `.gitignore:34` |
| `.env.example` sạch (không giá trị thật) | `.env.example:1-24` toàn biến rỗng |
| Không secret sống hardcode trong HEAD | quét regex rộng = 0 hit thật (§2.3) |
| Mã hóa OAuth token at-rest chuẩn | `src/lib/token-encryption.ts` AES-256-GCM, fail-closed, authTag |
| Cookie unlock review ký JWT + fail-closed | `src/lib/review/share-auth.ts:43-45` |
| JWT placeholder + INNGEST_DEV fail-closed | `src/lib/env.ts:37-42,53-60` (fix R1 & P5-005 đã hiện diện) |
| Webhook Mux verify HMAC timingSafeEqual ±5' | `src/app/api/webhooks/mux/route.ts:23-48` (parts/10) |

---

## 7. Thứ tự ưu tiên xử lý

1. **SEC5-01 (gấp nhất):** Xoay mật khẩu Neon `neondb_owner` + cập nhật Vercel env. (Credential prod đang sống nằm trong history công khai.)
2. **SEC5-03 / SEC5-04:** Xóa `api/scoring.py` + `api/vdownloader.py` + block `api/*.py` trong `vercel.json` + `requirements.txt` (gỡ 2 endpoint public không giám sát).
3. **SEC5-02:** Gỡ `prisma/dev.db` khỏi tracking + buộc 2 user đổi mật khẩu.
4. **SEC5-06:** Tạo DB role least-privilege cho runtime app.
5. **SEC5-07:** Kiểm tra & thay `JWT_SECRET` prod nếu trùng chuỗi yếu.
6. **SEC5-05 / SEC5-08 / SEC5-09:** Gỡ dump PII; đồng nhất `timingSafeEqual` cho cron; xóa/siết `/api/test-email`.
7. Sau (1)(2)(3): cân nhắc purge git history (BFG/`git filter-repo`) cho các chuỗi đã lộ.
