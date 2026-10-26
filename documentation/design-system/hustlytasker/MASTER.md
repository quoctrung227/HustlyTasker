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
No disabled fake Task/Review/AI menu items or business-write controls.

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

Future Task/Review screens reuse this master only after HT-FE-P3-02 approval.
AI Smart Task Generator may later belong to Task planning; AI Feedback Analyzer
to authorized feedback context. Neither has an active navigation item/API now.
No colors/layout/placeholder claim introduces Project or new permission rules.
