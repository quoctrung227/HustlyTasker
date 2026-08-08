/**
 * PHASE 5 — Seed test accounts cho TỪNG role thật của HustlyTasker.
 *
 * CHỈ DÙNG CHO DEV/TEST. Script này có guard cứng: từ chối chạy nếu
 * DATABASE_URL không phải Neon TEST branch (host chứa "frosty-forest").
 * KHÔNG BAO GIỜ chạy vào prod (ep-autumn-flower...).
 *
 * Cách chạy (từ repo root):
 *   npx tsx docs/system-audit/05-accounts/seed-test-accounts.ts
 * (script tự đọc .env.test — không cần export env thủ công)
 *
 * Hash password dùng ĐÚNG thuật toán của hệ thống: bcryptjs, 10 rounds
 * (giống src/actions/create-user.ts:87 và signup flow). Không insert plaintext.
 *
 * Idempotent: upsert theo username — chạy lại không tạo bản ghi trùng,
 * nhưng mỗi lần chạy sẽ RANDOM LẠI password (in ra stdout).
 */
import { readFileSync } from 'fs'
import { join } from 'path'
import { randomBytes } from 'crypto'
import bcrypt from 'bcryptjs'

// ── 1. Load .env.test + guard chống chạy nhầm prod ──────────────────────────
const envPath = join(process.cwd(), '.env.test')
const envRaw = readFileSync(envPath, 'utf8')
const m = envRaw.match(/^DATABASE_URL=["']?([^"'\r\n]+)["']?/m)
if (!m) {
    console.error('❌ Không tìm thấy DATABASE_URL trong .env.test')
    process.exit(1)
}
const dbUrl = m[1]
if (!dbUrl.includes('frosty-forest')) {
    console.error('❌ GUARD: DATABASE_URL không phải Neon TEST branch (frosty-forest). Từ chối chạy.')
    process.exit(1)
}
if (dbUrl.includes('autumn-flower')) {
    console.error('❌ GUARD: Đây là PROD database. Từ chối chạy.')
    process.exit(1)
}
process.env.DATABASE_URL = dbUrl
process.env.POSTGRES_URL = dbUrl // src/lib/env.ts ưu tiên POSTGRES_URL

// Import SAU khi set env để PrismaClient nhận đúng connection string.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { PrismaClient } = require('@prisma/client')
const prisma = new PrismaClient()

const BCRYPT_ROUNDS = 10 // giống src/actions/create-user.ts:87

function strongPassword(): string {
    // 18 ký tự base64url ≈ 108 bit entropy
    return randomBytes(14).toString('base64url').slice(0, 18) + '!A9'
}

type SeedUser = {
    username: string
    email: string
    displayName: string
    userRole: 'ADMIN' | 'USER' | 'AGENCY_ADMIN' | 'CLIENT' | 'LOCKED'
    profileRole?: 'OWNER' | 'ADMIN' | 'USER' | 'CLIENT'
    workspaceRole?: 'OWNER' | 'ADMIN' | 'MEMBER' | 'GUEST'
    note: string
}

// Mỗi role THẬT trong code có ít nhất 1 account đại diện.
// UserRole enum: prisma/schema.prisma (ADMIN/USER/AGENCY_ADMIN/CLIENT/LOCKED)
// ProfileRole qua ProfileAccess.role (OWNER/ADMIN/USER/CLIENT)
// WorkspaceRole qua WorkspaceMember.role String (OWNER/ADMIN/MEMBER/GUEST)
const USERS: SeedUser[] = [
    { username: 'test-audit-global-admin', email: 'test+global-admin@example.com', displayName: 'Audit Global Admin', userRole: 'ADMIN', profileRole: 'OWNER', workspaceRole: 'OWNER', note: 'UserRole=ADMIN (global) + profile OWNER + workspace OWNER' },
    { username: 'test-audit-profile-owner', email: 'test+profile-owner@example.com', displayName: 'Audit Profile Owner', userRole: 'USER', profileRole: 'OWNER', workspaceRole: 'OWNER', note: 'ProfileRole=OWNER — chủ team' },
    { username: 'test-audit-profile-admin', email: 'test+profile-admin@example.com', displayName: 'Audit Profile Admin', userRole: 'USER', profileRole: 'ADMIN', workspaceRole: 'ADMIN', note: 'ProfileRole=ADMIN — quản trị được mời' },
    { username: 'test-audit-editor', email: 'test+editor@example.com', displayName: 'Audit Editor', userRole: 'USER', profileRole: 'USER', workspaceRole: 'MEMBER', note: 'Staff/editor thường (ProfileRole=USER, WorkspaceRole=MEMBER)' },
    { username: 'test-audit-ws-guest', email: 'test+ws-guest@example.com', displayName: 'Audit Workspace Guest', userRole: 'USER', profileRole: 'USER', workspaceRole: 'GUEST', note: 'WorkspaceRole=GUEST' },
    { username: 'test-audit-agency-admin', email: 'test+agency-admin@example.com', displayName: 'Audit Agency Admin', userRole: 'AGENCY_ADMIN', profileRole: 'USER', workspaceRole: 'MEMBER', note: 'UserRole=AGENCY_ADMIN (legacy — còn trong enum)' },
    { username: 'test-audit-client', email: 'test+client@example.com', displayName: 'Audit Client', userRole: 'CLIENT', profileRole: 'CLIENT', note: 'UserRole=CLIENT — LOGIN BỊ CHẶN by design (src/actions/auth-actions.ts:361-363); khách dùng portal token /share' },
    { username: 'test-audit-locked', email: 'test+locked@example.com', displayName: 'Audit Locked', userRole: 'LOCKED', note: 'UserRole=LOCKED — trạng thái ban, login bị chặn (src/actions/auth-actions.ts:302-303)' },
]

async function main() {
    console.log('🌱 Seeding AUDIT test accounts vào Neon TEST branch (frosty-forest)...')

    // ── 2. Profile + Workspace + Client test ────────────────────────────────
    let profile = await prisma.profile.findFirst({ where: { name: 'AUDIT-TEST Team' } })
    if (!profile) profile = await prisma.profile.create({ data: { name: 'AUDIT-TEST Team' } })

    let workspace = await prisma.workspace.findFirst({ where: { name: 'AUDIT-TEST 2026-08', profileId: profile.id } })
    if (!workspace) {
        workspace = await prisma.workspace.create({
            data: { name: 'AUDIT-TEST 2026-08', description: 'Workspace test cho system audit — xoá thoải mái', profileId: profile.id },
        })
    }

    let client = await prisma.client.findFirst({ where: { profileId: profile.id, name: 'AUDIT-TEST Client' } })
    if (!client) {
        client = await prisma.client.create({
            data: { name: 'AUDIT-TEST Client', profileId: profile.id, workspaceId: workspace.id },
        })
    }

    // ── 3. Users + memberships ──────────────────────────────────────────────
    const rows: Array<{ role: string; username: string; email: string; password: string; note: string }> = []

    for (const u of USERS) {
        const password = strongPassword()
        const hashed = await bcrypt.hash(password, BCRYPT_ROUNDS)

        const user = await prisma.user.upsert({
            where: { username: u.username },
            update: { password: hashed, role: u.userRole, email: u.email },
            create: {
                username: u.username,
                usernameSetByUser: true,
                password: hashed,
                email: u.email,
                displayName: u.displayName,
                nickname: u.displayName,
                role: u.userRole,
                authProvider: 'email',
                emailVerified: true,
                emailVerifiedAt: new Date(),
                hasAcceptedTerms: true,
                termsAcceptedAt: new Date(),
                hasCompletedEmailMigration: true,
                profileId: profile.id,
            },
        })

        if (u.profileRole) {
            await prisma.profileAccess.upsert({
                where: { userId_profileId: { userId: user.id, profileId: profile.id } },
                update: { role: u.profileRole, clientId: u.profileRole === 'CLIENT' ? client.id : null },
                create: {
                    userId: user.id,
                    profileId: profile.id,
                    role: u.profileRole,
                    clientId: u.profileRole === 'CLIENT' ? client.id : null,
                },
            })
        }

        if (u.workspaceRole) {
            await prisma.workspaceMember.upsert({
                where: { userId_workspaceId: { userId: user.id, workspaceId: workspace.id } },
                update: { role: u.workspaceRole },
                create: { userId: user.id, workspaceId: workspace.id, role: u.workspaceRole },
            })
        }

        if (u.userRole === 'CLIENT') {
            await prisma.user.update({ where: { id: user.id }, data: { clientId: client.id } })
        }

        const roleLabel = [
            `User:${u.userRole}`,
            u.profileRole ? `Profile:${u.profileRole}` : null,
            u.workspaceRole ? `WS:${u.workspaceRole}` : null,
        ].filter(Boolean).join(' / ')
        rows.push({ role: roleLabel, username: u.username, email: u.email, password, note: u.note })
    }

    console.log('\n=== KẾT QUẢ (COPY VÀO accounts.md) ===')
    console.log(JSON.stringify({ profileId: profile.id, workspaceId: workspace.id, clientId: client.id, accounts: rows }, null, 2))
}

main()
    .then(async () => { await prisma.$disconnect() })
    .catch(async (e) => { console.error(e); await prisma.$disconnect(); process.exit(1) })
