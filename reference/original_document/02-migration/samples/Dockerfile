# syntax=docker/dockerfile:1
# =============================================================================
# Dockerfile — HustlyTasker API (Spring Boot 3.x / Java 21) — multi-stage
#
# Bối cảnh migration: backend rời Vercel (Next.js route handlers + server
# actions) sang Spring Boot chạy trên VPS. File này build image
#   ghcr.io/phucmetlamroi/hustlytasker-api
# (tên image phải KHỚP với docker-compose.yml và deploy.yml cùng thư mục).
#
# Giả định layout: pom.xml + src/ nằm ở build-context root (repo Spring riêng,
# hoặc `backend/` trong monorepo — khi đó chỉnh `context` trong deploy.yml).
# =============================================================================

########################
# Stage 1 — BUILD (Maven + JDK 21)
########################
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app

# Copy pom.xml TRƯỚC để layer-cache dependencies — chỉ đổi code thì không
# phải tải lại toàn bộ .m2 (build lại nhanh hơn nhiều trên CI).
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -q dependency:go-offline

# Copy source rồi build. Test đã chạy ở job riêng trong deploy.yml
# (mvn verify) nên ở đây skip để image build nhanh.
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -DskipTests package

# Tách fat-jar thành layer (dependencies / loader / app) để Docker cache
# tốt hơn: đổi code chỉ invalid layer `application/`, không invalid deps.
RUN java -Djarmode=layertools -jar target/*.jar extract --destination extracted

########################
# Stage 2 — RUNTIME (JRE 21 slim, non-root)
########################
FROM eclipse-temurin:21-jre-alpine AS runtime

# LƯU Ý nghiệp vụ repo này: pipeline review hiện tại re-tag colorspace video
# bằng ffmpeg trước khi đẩy Mux (src/lib/review/color-retag.ts trong app Next).
# Nếu port bước đó sang Spring thì mở comment dòng dưới (image nặng thêm ~80MB):
# RUN apk add --no-cache ffmpeg

# Non-root user — container KHÔNG chạy bằng root.
RUN addgroup -S spring && adduser -S -G spring spring
WORKDIR /app

# Copy các layer đã tách từ stage build (thứ tự: ít đổi -> hay đổi).
COPY --from=build /app/extracted/dependencies/          ./
COPY --from=build /app/extracted/spring-boot-loader/    ./
COPY --from=build /app/extracted/snapshot-dependencies/ ./
COPY --from=build /app/extracted/application/           ./

USER spring:spring
EXPOSE 8080

# MaxRAMPercentage thay cho -Xmx cứng: JVM tự lấy 75% RAM limit của container
# (compose có thể set mem_limit sau này mà không phải sửa image).
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0"

# HEALTHCHECK gọi Spring Actuator (cần dependency spring-boot-starter-actuator
# + management.endpoints.web.exposure.include=health trong application.yml).
# alpine có busybox wget sẵn — không cần cài curl.
# start-period 40s: Spring Boot + Hikari pool cần thời gian khởi động.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/actuator/health | grep -q '"status":"UP"' || exit 1

# Spring Boot >= 3.2: launcher đổi package sang `.loader.launch.JarLauncher`
# (bản < 3.2 là org.springframework.boot.loader.JarLauncher).
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS org.springframework.boot.loader.launch.JarLauncher"]
