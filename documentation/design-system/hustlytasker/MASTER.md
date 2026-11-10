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
The Owner-approved P4-02C fixture Smart Task Generator now belongs to Task
planning, with actual availability and explicit demo labeling. AI Feedback
Analyzer React integration is now separately authorized in P4-03C below; its
current verification status must be checked in HANDOVER rather than inferred
from this design guidance.
No colors/layout/placeholder claim introduces Project or new permission rules.

## Workspace and Task patterns — HT-FE-P3-02

### Task UX refinement — HT-FE-TASK-UX-REFINEMENT-01

Reuse the established tokens and shared components; no new visual direction,
dependency, palette, typography or Workspace-wide styling override. Task-only
description card is24rem on desktop, flex-column with a fixed outside heading
and an independently scrollable, named native section. min-height0/min-width0
allow the body to shrink; overflow-y:auto and overflow-wrap:anywhere keep all
content readable without horizontal clipping. Short content has no scrollbar.
Neighboring facts card aligns to the grid's start at its natural height. Mobile
stacks both cards and uses natural description height capped at24rem.

The scroll region remains a normal named section with tabIndex0 and the shared
focus ring, allowing keyboard scrolling without moving the page heading or
inventing a widget role. Its single element-local Biome exception explains that
keyboard requirement. Native fieldset groups the from/to UTC date filters in
one column, with the end bound directly below the start. Reset only that
fieldset's border/padding/margin; preserve UTC semantics and existing date picker.
Apply/Clear use a full-row action group; controls reflow at existing breakpoints.

Assignee labels come from the current server-scoped display_name. Use readable
unassigned/unavailable/legacy fallbacks instead of UUIDs or remembered names.
Names are presentation data, never permission evidence. Existing compensation
NULL projection and manager-only metadata writes remain unchanged.

Collaboration now says **Sản phẩm và đánh giá**. Submit uses a persistent
**Link sản phẩm hoàn thành** URL label/example, **Nộp sản phẩm**, explicit
pending/error/success states and the existing native decision dialogs. Each
revision's **Mở sản phẩm** action opens its own safe HTTP(S) URL in a new tab;
legacy non-URL values remain inert readable text. New URL-only500-code-point
validation supersedes earlier text-or-URL writes, without changing models or
rendering old paths as links. No upload/preview/realtime interaction is added.

Actual offline focused searches refined generic results to Web Keyboard
Navigation and html-tailwind Long Token Resilience. Relevant full-skill web
guidance informed visible focus, preserved DOM order, grouping and long-token
wrapping; native-only advice and unrelated generated styling were not adopted.
Geometry/scrolling,375/768/1440/landscape, keyboard and axe require real browser
verification; HANDOVER records actual final evidence and Owner review status.

### Task work-brief override — HT-FE-TASK-BRIEF-24H-VI-01 candidate

Ordinary Task forms now use the existing teal/neutral tokens, grouped optional
resource inputs and expected VND compensation, with a Task-only scrollable720px
native dialog and reachable sticky actions. No shared Dialog/theme reset.
Detail has job information, safe labeled resource actions and optional exact-pay
card; empty groups hide,0 remains visible. Links do not auto-fetch/embed.

HT-FE-TASK-COMPENSATION-RBAC-01 supersedes broad pay visibility: the server returns
NULL for unauthorized or unset compensation, and the entire pay card stays absent.
Helper text names legitimate management/current-assignee access and distinguishes
read from manager-only write. Do not render a misleading disabled financial card,
derive authority from role labels, or retain a previous response's amount. Reuse
the same teal/neutral surface, exact string formatting and semantic form controls;
this is privacy behavior/copy, not a new design system. Current tests belong in
HANDOVER, not an inferred visual or deployment acceptance claim.
Full local skill/master and offline focused React `async request cleanup`
search were actually used. Verified effect-cleanup guidance supports retaining
existing scope-bound requests and replacing current server responses; it does
not call for a new permission store, role inference or changed form layout.

Task deadline and date filters use a controlled dd/mm/yyyy text field with an
optional inline Vietnamese calendar, explicit24h hour/minute selects and clear.
Calendar month/weekday/control names are Vietnamese and keyboard accessible;
normal Task UI does not depend on browser datetime-local/AMPM localization.
Device-local input→UTC and UTC filter semantics remain. Unchanged edit timestamp
is not resubmitted; new/changed deadlines use minutes. Existing separate AI
proposal helpers/precision remain intact, outside this ordinary-form override.
Ordinary hierarchy affordances are removed; stored child data/API/AI proposal
relations remain. No fabricated progress algorithm or hidden Task rows.

Full local skill/master and focused Forms/date keyboard/React cleanup searches
were actually applied. Native labels/grouping, safe errors, precise string money,
retained scope-bound drafts and explicit submit/no automatic retry are reused.
Current isolated test/preservation/rollout status belongs in HANDOVER; candidate
schema does not authorize development migration or manual production claims.

No palette/font/layout reset. Task list uses semantic list rows, wrapping into
cards on mobile instead of forcing a wide table across the viewport. Titles
are primary links; status/priority always include text. Teal/canvas semantic
colors remain the base; urgent/overdue use the existing danger tokens. Overdue
is an indicator only, not a new workflow state. Real server counts describe
the active filters, never dashboard analytics inferred from a single page.

Filter controls are persistent labeled native selects/date inputs in a compact
responsive grid, with explicit Apply/Clear. "Tìm trong trang" searches only
loaded rows. Date range labels state UTC; editable Task deadlines state browser
timezone and are converted to UTC instants. Historical HT-FE-P3-02 used bounded
ancestor breadcrumbs/direct-child pagination; the current Task work-brief override
above removes those ordinary UI affordances while preserving the backend contract.

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
error summary with links plus inline messages. New Submit accepts an HTTP(S) URL
under the current Task UX refinement above. API03A's earlier text-or-URL policy
is historical; stored legacy values remain readable. There is no fake file-upload
control. Request Changes has a required feedback
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

## First-time Profile onboarding — HT-FE-P3-05

Reuse the existing teal/neutral tokens, Plus Jakarta Sans, content width/gutters,
Card, Button, FormField/Input, Alert and route-heading focus. No visual-direction
reset, new dependency, tenant selector store or decorative onboarding tour.

The actual focused `empty state onboarding action --domain ux` result selected
a useful message plus a working next action; Dashboard/Profiles now lead from
**Bạn chưa có tổ chức nào** to the protected **Tạo tổ chức mới** page. Existing
Users get the same creation link on the Profile list header. A focused React
async-form/error search informed caught failures, retained drafts and semantic
pending/disabled controls. Those are platform-relevant guidance, not permission
to change authentication or add native-only interactions.

The short name-only form uses persistent required label/helper, Vietnamese safe
errors, a focusable linked error summary, comfortable controls and a secondary
Cancel/back path. Pending state blocks duplicate submit and indicates progress;
the request/draft lifetime is current-User-scoped. Success is displayed only after
the server confirms and directs the User to existing Workspace creation under
the new Profile URL. It does not automatically create data beyond the requested
Profile. No password, token, owner ID or manual tenant field enters the form.

Current real isolated onboarding3/3 passed. Empty/form-error surfaces at
375/768/1440/812x375 landscape passed keyboard/focus/overflow and axe0 checks;
desktop-empty/mobile-form PNGs were visually inspected. Screenshots are local
Git-ignored HT-FE-P3-05 artifacts; exact run/exit/cleanup evidence is in HANDOVER.
All six real isolated browser suites25/25 and final development/schema/AI
preservation passed; actual exits and owned cleanup are verified. FE05 is
**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE**. No manual development website
or production verification is claimed. Historical FE04 exclusion applied only to that task;
FE05's Owner approval covers Profile creation, not Invitation/general membership.

## Fixture proposal preview and confirmation — HT-AI-P4-02C

Reuse the teal/neutral tokens, typography, Card/Button/FormField/Input/Alert,
route heading and shared native Dialog. No new visual direction, dependency,
global navigation item or Task Detail redesign. The manager-only Task-list entry
is secondary to existing manual creation and explains a disabled fixture flag.

The visible simulation banner precedes input/preview and explains synthetic-only
input, fixed output and the separate human-confirmation boundary. A persistent
label and6,000-character counter accompany the optional brief. Local Task edits
have inline validation plus a focused linked error summary; parent labels and
preview metadata distinguish hierarchy from editable Task fields.

The UI implementer read the full local skill/master and ran focused confirmation
UX and React async cleanup/retry searches. Applicable guidance is explicit
review-before-commit, semantic pending/disabled controls, caught recoverable
failures and deliberate retry. Native-only guidance does not replace web rules.
Keyboard-operable native confirmation/discard dialogs retain focus restoration,
Cancel/Escape and existing responsive spacing. No optimistic creation or silent
retry can imply success. Expired/ambiguous outcomes direct Users to recovery or
Task inspection without asserting that an uncertain mutation failed.
Internal-link and page-unload discard prompts cover local drafts; SPA browser
Back/Forward does not use the anchor guard and may discard unsaved edits. Do
not describe the current UI as providing durable draft persistence.

P4-02C final enabled real isolated browser4/4 PASS49.5s includes preview and
confirmation at375/768/1440/812×375, reduced motion, keyboard/native-dialog
Escape/focus restoration, overflow and axe WCAG2/2.1AA with0 violations. Root
visually inspected desktop preview1440 and confirmation375 PNGs from run
71178bfad5c24cefac78ec063cd54897. Disabled1/1 and onboarding3/3 also passed;
all corresponding process exits0 and owned cleanup are verified. Final
development/schema/source preservation and all8 real isolated Chromium suites
30/30 pass with actual exits0/owned cleanup and no remaining owned test
containers/networks. HANDOVER owns final evidence. P4-02C is **IMPLEMENTATION
COMPLETE — OWNER REVIEW GATE**, fixture-only; nondurable draft/SPA Back limits,
advisory build chunk size and manual development review remain explicit.
FE05/FE04 visual results above remain historical. No later AI work begins here.

## Advisory Feedback Analyzer — HT-AI-P4-03C

Reuse the existing Task Detail route and collaboration section hierarchy. The
Analyzer is a lightweight adjacent section, not a new sidebar destination,
dashboard redesign or second AI design system. Existing teal/neutral tokens,
Plus Jakarta Sans, Card/Button/Alert/Pagination and semantic focus states remain.
The current slice has a clear **Phân tích phản hồi** entry, visible fixture-only
disclosure and honest unavailable state when the shared backend flag is off.

Selected-source controls use labeled native checkboxes grouped by existing
Review feedback and Task Comments. Show actual readable source text separately
from synthetic suggestions; source IDs or author labels are not permission
proof. Pagination bounds the loaded list, and selection is unique/capped at20.
Optional focus has a persistent label,1,000-character counter and associated
validation feedback. It must not suggest that the fixed fixture tailors results
to entered focus. Submit is explicit and pending-disabled, never on keystrokes.

Results say **Kết quả mô phỏng**, distinguish source citations from evidence of
semantic understanding, and state that they are not saved as history. The
interface has no Apply/Confirm, fabricated confidence, timecode or automatic
Review/Task action. Display source/result text through normal React escaping,
wrap long content and keep category/priority meaning in text as well as color.
Current User/Profile/Workspace/Task state lifetime, aborts and stale-result
discarding are part of the interaction contract, not a visual permission grant.

The UI implementer read the full739-line local skill/master and ran focused
offline searches using the existing Python test image: `checkbox group error
summary --domain ux` selected the web focusable summary/connected inline-error
guidance; `async request cleanup race --stack react` selected effect cleanup
and caught async failures. These inform the actual grouped native controls,
linked/focused errors, pending feedback and request/cache cancellation behavior.
Existing web reflow, contrast, non-color-only status and semantic token guidance
remain authoritative; no generated design-system replacement or native-only
requirement is adopted.

Focused component32/32 and transport/client153/153 pass, including deletion-cache
race coverage. Final frontend675/675 and real Analyzer5/5 plus disabled1/1 pass;
all real browser regressions total36/36. Automated375/768/1440 and812×375 landscape
checks verify no horizontal overflow, keyboard Space/Enter, focused result,
reduced motion and zero WCAG2/2.1 AA axe violations. Four full-page screenshots
are saved in the Git-ignored task evidence directory. The375px/1440px images were
visually inspected: grouped feedback and synthetic result remain distinct/readable,
the focused result is visible and no horizontal overflow is present. Screenshot
inspection and automated checks are not represented as Owner manual acceptance.
[HANDOVER](../../HANDOVER.md) owns final evidence and Owner review status.
