# HustlyTasker web design system

Date: 2026-10-26. HT-FE-P3-01 implementation choices for Owner review.
Scope: authenticated team-work SaaS web app; not a marketing landing page.
This master and frontend/src/styles.css are the shared reference for later UI
tasks. Read both before changes; do not introduce an independent screen theme.

## Research and selection

Read .agents/skills/ui-ux-pro-max/SKILL.md in full. Ran its Python CLI using
the existing Python3.12 dependency image, network none, read-only skill mount:

- `productivity SaaS team dashboard --design-system`: motion/landing output
  rejected as unsuitable; its Plus Jakarta Sans SaaS font recommendation fits.
- Narrowed once: `project management dashboard minimal --design-system
  --variance 2 --density 7`: selected **Minimalism & Swiss Style**, high
  contrast, restrained grid/hierarchy and spacing. Generated funnel/portfolio
  pattern and unrelated anti-patterns are not verified matches and are omitted.
- `productivity collaboration --domain color`: Productivity Tool, teal focus.
  Adapted to deeper teal for white-label contrast, warm neutral surfaces and
  muted lime secondary highlights; orange/indigo generated accents not adopted.
- `SaaS dashboard readable --domain typography`: Fira technical/code pairing
  not selected for this non-code work app. Use one Plus Jakarta Sans family.
- `accessible authentication --domain ux`: allow paste/password managers,
  label controls; no new authentication mechanism is authorized by a suggestion.
- `forms async loading --stack react`: explicit async error/loading handling.

Search output is advisory. No unverified full generator output is persisted;
this master records the deliberate product/platform-filtered synthesis. Native
safe-area/haptics/Dynamic Type patterns are not web requirements. No GSAP,
parallax, external font calls, photos, charts or decorative fake data are added.

## Tokens

| Semantic role | Value |
|---|---|
| Canvas | #f6f7f3 |
| Surface | #ffffff |
| Sidebar/ink | #16352f |
| Primary/action/focus | #23634f |
| Primary foreground | #ffffff |
| Accent | #d5ebaa, with dark ink text |
| Main text | #24362f |
| Muted text | #5b6860 |
| Border | #dfe5dd |
| Error | #b42318, pale background #fff1ef |
| Archived/muted surface | #eef1ec |

Primitive colors map to semantic CSS variables; components use semantic tokens.
State never relies on color alone. Text/background pairs must meet4.5:1 for
normal text,3:1 for meaningful UI boundaries/icons; verify measured pairs.

- Typography: locally bundled Plus Jakarta Sans Variable, Vietnamese glyphs,
  system sans fallback; body16px/1.6, labels14px, secondary12–14px, headings
  24–36px, weights400/500/600/700. IDs/period metadata use tabular numerals.
- Spacing:4/8/12/16/20/24/32/40/48px; page gutters20px mobile,32–40px desktop.
- Radius:8px controls,12px cards,16px featured surface; pill for badges only.
- Elevation: quiet border first, subtle shadow on overlays/hover; no glass blur.
- Motion:120–180ms color/opacity changes, reduced-motion removes animation.
- Icons: one Phosphor outline family; decorative icons aria-hidden, icon-only
  controls have accessible names; no emoji navigation.

## Layout and components

Desktop sidebar240px, content area max1280px, white topbar with breadcrumb,
responsive content grid. Below900px sidebar becomes an operable native-dialog
menu; navigation remains consistent. Real Profile cards/list and Workspace
monthly list/details use the same spacing/status/selection language. Dashboard
is a useful access overview of real accessible Profiles, not analytics fiction.
No disabled fake Task/Review/AI menu items. Business-write controls appear only
for implemented, explicitly approved surfaces with current capability hints.

Buttons: primary deep teal, secondary white bordered, ghost text, danger error
color. All have focus-visible outline, hover/pressed feedback and semantic
disabled/loading state; comfortable44px primary touch controls. Input labels
persist; inline errors connected via aria-describedby. Password paste/autofill
works. Loading skeletons reserve space, empty/error states explain next steps,
and retries are explicit. Tables/lists wrap long content; page controls do not
follow untrusted absolute pagination links. Dialog uses native focus containment
and Escape with focus restoration, no custom keyboard trap.

## Validation and future integration

Check375/768/1440 widths plus812×375 landscape, keyboard-only navigation, focus visibility, overflow,
heading order, reduced motion, labels and contrast. Test real empty/forbidden/
expired-session states and keep private content hidden during auth initialization.
Automated mock tests are not live backend proof; use isolated real fixtures.
Route headings receive programmatic focus for screen-reader orientation without
an interactive-control outline; keyboard-operated controls/skip links retain
their visible focus rings. Empty password fields need no screenshot redaction;
any populated password field is masked before a test screenshot is retained.

The Owner has now approved HT-FE-P3-02 Workspace/Task screens; these reuse this
master. HT-FE-P3-03 authorizes collaboration UI; the Owner subsequently approved
HT-API-FE-P3-03A for the bounded Submit/Review/old Comment-author capability
extension. Current verification and its final Owner review gate are in HANDOVER.
AI Smart Task Generator may later belong to Task planning; AI Feedback Analyzer
to authorized feedback context. Neither has an active navigation item/API now.
No colors/layout/placeholder claim introduces Project or new permission rules.

## Workspace and Task patterns — HT-FE-P3-02

No palette/font/layout reset. Task list uses semantic list rows, wrapping into
cards on mobile instead of forcing a wide table across the viewport. Titles
are primary links; status/priority always include text. Teal/canvas semantic
colors remain the base; urgent/overdue use the existing danger tokens. Overdue
is an indicator only, not a new workflow state. Real server counts describe
the active filters, never dashboard analytics inferred from a single page.

Filter controls are persistent labeled native selects/date inputs in a compact
responsive grid, with explicit Apply/Clear. "Tìm trong trang" searches only
loaded rows. Date range labels state UTC; editable Task deadlines state browser
timezone and are converted to UTC instants. Scope breadcrumbs and at most three
ancestor requests keep hierarchy navigation bounded; direct children paginate.

Reuse native Dialog, FormField, Button, Alert and Pagination. Create/edit forms
retain drafts on recoverable failures; focused error summary links complement
inline errors. Busy forms disable close/Escape/duplicate submissions. Archive/
restore has explicit confirmation. No optimistic success or status completion.
Workspace/member selectors show actual API data; no fabricated person names.

The skill's local UX "error summary validation" search was executed using the
existing Python test image, network none/read-only skill mount. Its focusable
summary, linked invalid fields and announced error guidance informs these forms.
Focused React async-error and responsive table UX searches were also executed
by the component/test agents. Web-relevant guidance is applied, without adopting
native-only advice or replacing existing design tokens. Actual final browser,
axe, keyboard and visual results are recorded in HANDOVER.md.

## Collaboration and personal Notifications — HT-FE-P3-03

Reuse the established palette, font, spacing, cards, fields, buttons and native
dialogs. Task sections show chronological revision cards with nested Review
feedback; comments use readable prewrapped text, metadata, counters and bounded
pagination. No tree recursion, new theme, rich text or fake upload control.
Moderation has explicit confirmation; failed forms keep drafts and announced
field errors. Confirmed tombstones hide content immediately across cached pages.

Personal Notifications add an existing-style bell, count badge and native modal
preview, plus a full paginated list. Read/unread is expressed by text and border,
not color alone. Controls retain44px touch space and visible keyboard focus.
The skill's actual focused `live badge count screen reader --domain ux` search
selected contextual atomic announcements without focus theft or competing bare
number regions. The collaboration agent also executed destructive-confirmation/
async-error UX searches. Existing full skill/web checklist and master were read;
native-only safe-area/dark-mode advice did not create a new requirement/theme.
Verify375/768/1440 and812x375 landscape with axe, keyboard and representative
PNG inspection; actual results belong in HANDOVER, not a design claim alone.

## Collaboration mutation forms — HT-API-FE-P3-03A

No visual direction, token or layout change. Submit, Approve and Request Changes
reuse native Dialog, the existing work-form/field/button styles and a focused
error summary with links plus inline messages. Submit explicitly accepts text
or URL, not a fake file-upload control. Request Changes has a required feedback
field; Approve has optional feedback and explicit confirmation. Pending controls
prevent duplicate submission and dismissal; drafts survive recoverable errors.
Current server capability booleans decide action visibility, without client-side
identity guesses or optimistic Task completion. Comment author actions use the
same existing edit/delete patterns after reload and pagination.

For this resume, the full skill/master were read and focused searches actually
ran for `error summary validation --domain ux` (Forms/Accessibility, web focusable
summary) and `async form error --stack react` (caught async failures). Their
applicable guidance supports announced errors, linked fields and pending/error
feedback. React-wide transition refactoring and native-only checklist items
were not adopted. Existing teal/neutral colors, typography and components stay
authoritative. Current isolated collaboration7/7 PASS verifies actual mutation
forms at375/768/1440/812x375, native keyboard/focus, overflow and axe WCAG2/2.1 AA
with0 violations.24 screenshots are retained; Submit375, RequestChanges812
landscape and Approve1440 were visually inspected. Final frontend, isolated
backend and browser regressions also pass; API03A is COMPLETE and FE03 is
IMPLEMENTATION COMPLETE at OWNER REVIEW GATE. Run/exit/cleanup evidence belongs
in HANDOVER; completion is not inferred from these design rules alone.

## Account lifecycle and MVP acceptance — HT-FE-P3-04

Reuse existing teal/neutral semantic tokens, typography, work-form/Input/FormField,
Alert, Card and native navigation/focus patterns. Registration and public recovery
forms use the existing status-page surface; authenticated current-account
verification stays within the established sidebar/topbar layout. No new visual
direction, font, framework, upload control or AI placeholder is introduced.

Visible labels, password-manager autocomplete and paste support follow the
actual focused `accessible authentication --domain ux` search and full skill
review. Its passkey/OAuth suggestion does not authorize a new auth mechanism.
Focused linked errors, static safe messages, async pending/abort feedback and
duplicate guards retain the established React/form patterns. Email/reset tokens
are masked manual-paste inputs, not URLs or persistent browser state; request
acceptance wording never promises verified email delivery or account existence.

Current395 unit/contract tests, typecheck/lint/build and all five real browser
suites22/22 pass, including the cohesive business journey and account-security
email-adapter flow. Four-size375/768/1440/812x375 landscape axe WCAG2/2.1AA has
0 violations; keyboard/native-dialog focus and overflow checks pass. Empty
registration375, reset812 landscape and completed Task1440 PNGs were visually
inspected. Manual interactive Owner review and real provider delivery are not
claimed. Local non-mutating startup/connectivity also pass; HANDOVER.md records
the actual exits, cleanup and limitations. FE04 is COMPLETE / OWNER REVIEW GATE.
Owner-approved MVP excludes Invitation/Profile Creation/membership onboarding
from this task while keeping their future product requirements. AI readiness
remains design only in FRONTEND_MVP_ACCEPTANCE.md; no automatic next task starts.
