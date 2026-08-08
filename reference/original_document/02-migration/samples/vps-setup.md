# VPS Setup — Ubuntu 24.04 cho HustlyTasker API

> Hướng dẫn dựng VPS chạy bộ file mẫu cùng thư mục: `Dockerfile` + `docker-compose.yml` + `Caddyfile` + `.env.example` + `deploy.yml`. Quy ước cố định xuyên suốt: deploy dir **`/opt/hustlytasker`**, user **`deploy`**, domain API **`api.hustlytasker.xyz`**, image **`ghcr.io/phucmetlamroi/hustlytasker-api`**. Frontend Next.js VẪN ở Vercel (`hustlytasker.xyz`) — những gì frontend phải đổi nằm ở `frontend-changes.md`.

## 0. Chuẩn bị trước khi SSH

| Việc | Chi tiết |
|---|---|
| DNS | Tạo A record `api.hustlytasker.xyz` → IP VPS. Nếu domain nằm sau Cloudflare proxy (mây cam): **tắt proxy (DNS only)** ít nhất trong lần Caddy xin cert đầu tiên, hoặc chuyển hẳn sang DNS-01. |
| Chọn VPS | Tối thiểu 2 vCPU / 4GB RAM / 40GB SSD (JVM + Postgres 16 + Caddy; JVM lấy 75% RAM limit theo `JAVA_OPTS` trong Dockerfile). Region gần user VN (Singapore) — DB self-host nằm cùng máy nên hết độ trễ Neon US. |
| SSH key | Tạo key ed25519 riêng cho deploy: `ssh-keygen -t ed25519 -f deploy_key`. Public key sẽ vào VPS, private key dán vào GitHub secret `SSH_KEY` (khớp `deploy.yml`). |

## 1. User + SSH hardening

```bash
# (đang là root sau khi provision)
adduser deploy
usermod -aG sudo deploy
rsync -a ~/.ssh /home/deploy/ && chown -R deploy:deploy /home/deploy/.ssh
# thêm public key của deploy_key vào /home/deploy/.ssh/authorized_keys

# Khoá đường root + password
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

## 2. Firewall — ufw (22/80/443)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH      # 22
sudo ufw allow 80/tcp       # ACME HTTP-01 + redirect HTTPS
sudo ufw allow 443/tcp      # HTTPS
sudo ufw allow 443/udp      # HTTP/3 (Caddy)
sudo ufw enable
sudo ufw status verbose
```

> **Bẫy Docker + ufw (quan trọng):** port PUBLISH bởi Docker (`ports:` trong compose) đi thẳng vào iptables chain `DOCKER`, **bypass ufw**. Vì vậy `docker-compose.yml` mẫu chỉ publish 80/443 (Caddy — vốn dĩ phải public) và bind Postgres vào `127.0.0.1:5432` — **không bao giờ** viết `"5432:5432"` rồi tin rằng ufw đang chặn. Truy cập DB từ máy dev qua SSH tunnel: `ssh -L 5432:127.0.0.1:5432 deploy@VPS`.

## 3. fail2ban

```bash
sudo apt update && sudo apt install -y fail2ban
sudo tee /etc/fail2ban/jail.local > /dev/null <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
EOF
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd    # kiểm tra jail đang chạy
```

Không cần jail cho HTTP: rate-limit tầng ứng dụng đã có (Upstash — `src/lib/rate-limit-upstash.ts` fail-closed ở prod, port sang Spring giữ nguyên hành vi).

## 4. Cài Docker (repo chính thức, Ubuntu 24.04 "noble")

```bash
sudo apt update && sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu noble stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# deploy chạy docker không cần sudo (cần cho script SSH trong deploy.yml)
sudo usermod -aG docker deploy
# logout/login lại để nhận group
```

## 5. Dựng thư mục app

```bash
sudo mkdir -p /opt/hustlytasker/backups
sudo chown -R deploy:deploy /opt/hustlytasker
cd /opt/hustlytasker

# Copy 3 file từ samples/ (scp hoặc dán tay):
#   docker-compose.yml
#   Caddyfile
#   .env          (từ .env.example — điền giá trị thật)
```

## 6. Quản lý secrets — .env

```bash
cd /opt/hustlytasker
cp .env.example .env   # hoặc scp lên
nano .env              # điền giá trị thật (danh sách key trong .env.example)
chmod 600 .env         # CHỈ owner đọc được
chown deploy:deploy .env
```

Quy tắc:

- **Không commit** `.env` vào bất kỳ repo nào; `.env.example` (không giá trị) mới được commit.
- **`JWT_SECRET` và `REVIEW_COOKIE_SECRET` phải GIỮ NGUYÊN giá trị đang chạy trên Vercel** trong giai đoạn chuyển tiếp — session cookie 30 ngày là JWT HS256 ký bằng `JWT_SECRET` (`src/lib/jwt.ts:2-21`), đổi là toàn bộ user logout; cookie unlock guest `/r/` ký bằng `REVIEW_COOKIE_SECRET` (`src/lib/review/share-auth.ts:111-144`).
- Secret CI/CD (SSH_KEY, GHCR_TOKEN…) nằm ở GitHub Actions secrets, **không** nằm trên VPS; VPS chỉ giữ `.env` runtime.
- Xoay secret: sửa `.env` → `docker compose up -d --no-deps api` (không cần build lại).

## 7. GHCR login (pull image private)

```bash
# PAT (classic) scope read:packages — cùng giá trị với secret GHCR_TOKEN trong deploy.yml
echo '<GHCR_TOKEN>' | docker login ghcr.io -u <GHCR_USER> --password-stdin
```

`deploy.yml` cũng tự login mỗi lần deploy nên bước này chỉ cần cho lần chạy tay đầu tiên.

## 8. Khởi động lần đầu + SSL

```bash
cd /opt/hustlytasker
docker compose up -d
docker compose ps                 # 3 service: db (healthy) -> api (healthy) -> caddy
docker compose logs -f caddy      # xem Caddy xin cert Let's Encrypt
curl -s https://api.hustlytasker.xyz/actuator/health   # {"status":"UP"}
```

- Caddy **tự động** xin + gia hạn cert (lưu ở volume `caddy_data`) — không certbot, không cron renew. Điều kiện duy nhất: DNS đúng + port 80/443 mở (mục 2).
- Nếu xin cert fail nhiều lần sẽ dính rate-limit Let's Encrypt (5 lần/tuần/domain) — debug bằng CA staging trước: thêm `acme_ca https://acme-staging-v02.api.letsencrypt.org/directory` vào block domain trong `Caddyfile`, hết lỗi thì bỏ ra.

## 9. Backup Postgres — pg_dump cron + rclone lên R2

Repo đã có sẵn tài khoản Cloudflare R2 (bucket video review `hustly-review` — `src/lib/review/r2.ts`). Tạo **bucket riêng** `hustly-db-backups` cho dump (đừng trộn với bucket asset đang phục vụ user), cấp API token S3 riêng chỉ có quyền write bucket đó.

### 9.1 Cài + cấu hình rclone

```bash
sudo apt install -y rclone
mkdir -p ~/.config/rclone
tee ~/.config/rclone/rclone.conf > /dev/null <<'EOF'
[r2backup]
type = s3
provider = Cloudflare
access_key_id = <R2_BACKUP_ACCESS_KEY_ID>
secret_access_key = <R2_BACKUP_SECRET_ACCESS_KEY>
endpoint = https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com
acl = private
EOF
chmod 600 ~/.config/rclone/rclone.conf
rclone lsd r2backup:    # kiểm tra kết nối
```

### 9.2 Script backup

```bash
tee /opt/hustlytasker/backup.sh > /dev/null <<'EOF'
#!/usr/bin/env bash
# pg_dump custom-format (-Fc: đã nén, restore chọn lọc được bằng pg_restore)
set -euo pipefail
cd /opt/hustlytasker
STAMP=$(date -u +%Y%m%d-%H%M%S)
FILE="backups/hustlytasker-${STAMP}.dump"

# exec vào container db — không cần cài postgres-client trên host
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-hustly}" -Fc "${POSTGRES_DB:-hustlytasker}" > "$FILE"

# Đẩy lên R2 (bucket riêng cho backup)
rclone copy "$FILE" r2backup:hustly-db-backups/

# Giữ 14 ngày local (R2 giữ lâu hơn — đặt lifecycle rule 90 ngày trên bucket)
find backups/ -name '*.dump' -mtime +14 -delete
EOF
chmod +x /opt/hustlytasker/backup.sh
```

### 9.3 Cron

```bash
crontab -e   # user deploy
# 19:30 UTC = 02:30 VN — trước review-janitor 20:00 UTC (lịch giữ từ vercel.json:48)
30 19 * * * /opt/hustlytasker/backup.sh >> /opt/hustlytasker/backups/backup.log 2>&1
```

### 9.4 Kiểm tra restore (làm ít nhất 1 lần trước cutover, rồi mỗi quý)

```bash
docker compose exec -T db createdb -U hustly restore_test
docker compose exec -T db pg_restore -U hustly -d restore_test < backups/hustlytasker-<stamp>.dump
# đếm bảng, so sánh: schema thật có 67 model + 3 partial unique index + 5 CHECK
# + 1 trigger nằm NGOÀI schema.prisma (parts/03-models.md) — pg_dump -Fc mang
# theo đủ vì dump ở tầng Postgres, không phải tầng Prisma.
docker compose exec -T db dropdb -U hustly restore_test
```

> Điểm ăn tiền của việc rời `prisma db push`: các constraint thủ công (2 partial unique `lower(name)` trên ReviewFolder/ReviewAsset, CHECK, trigger last-owner) từng phải duy trì bằng 6 file SQL tay (`prisma/migrations/manual/`) vì `db push` không biết chúng. `pg_dump` chụp đúng trạng thái DB thật nên restore không mất — nhưng khi chuyển sang Flyway/Liquibase ở Spring, phải đưa các SQL tay này vào migration V1 baseline.

## 10. Watchtower — cân nhắc: KHÔNG dùng

| | Phân tích |
|---|---|
| Watchtower làm gì | Poll registry, thấy tag `:latest` đổi là tự pull + restart container. |
| Vì sao KHÔNG hợp với setup này | Pipeline `deploy.yml` đã deploy **explicit** sau khi `mvn verify` xanh + chờ healthcheck. Thêm watchtower tạo đường deploy thứ hai không qua gate test, có thể restart api giữa lúc Actions đang deploy (đúng cái mà `concurrency` trong workflow đang chống). |
| Khi nào cân nhắc lại | Nếu sau này muốn auto-update **image hạ tầng** (postgres/caddy vá CVE) — chạy watchtower scope hẹp bằng label `com.centurylinklabs.watchtower.enable=true` chỉ trên db/caddy, lịch tuần, và vẫn để api ngoài scope. |
| Thay thế nhẹ hơn | `docker compose pull && up -d` cho db/caddy trong cửa sổ bảo trì thủ công, mỗi tháng. |

## 11. Vận hành hằng ngày

```bash
docker compose ps                          # trạng thái + health
docker compose logs -f --tail=200 api      # log Spring
docker compose exec db psql -U hustly hustlytasker   # vào DB
df -h && docker system df                  # disk (image cũ đã được prune trong deploy.yml)
```

Rollback 1 lệnh (image tag sha do `deploy.yml` push):

```bash
cd /opt/hustlytasker
API_IMAGE=ghcr.io/phucmetlamroi/hustlytasker-api:sha-<commit_cũ> docker compose up -d --no-deps api
```
