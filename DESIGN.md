# OpenStack Inventory Design System

## 0. Research Log
- Embedded refs: shortlisted operational dashboard references → picked taste-skill + a restrained enterprise inventory direction because the audience is infrastructure operators.
- Lazyweb: skipped — no external product reference was requested and the host has no frontend browsing requirement.
- Imagen drafts: skipped — an operational dashboard benefits from data clarity over concept imagery.

## 1. Atmosphere & Identity
Quiet control-plane tooling: dense enough for operators, calm enough to scan during an incident. The signature is a deep evergreen masthead paired with paper-like panels and small mono status labels.

## 2. Color
| Role | Token | Value | Usage |
|---|---|---|---|
| Ink | --ink | #17211f | Headings and navigation |
| Paper | --paper | #f4f6f2 | Page background |
| Panel | --panel | #ffffff | Cards and tables |
| Line | --line | #dce4de | Quiet separators |
| Evergreen | --green | #166b53 | Links, counts, healthy status |
| Mint | --mint | #dcefe5 | Healthy status surfaces |
| Amber | --amber | #a26017 | Partial and empty status |
| Red | --red | #a4372e | Missing and unavailable status |
| Muted | --muted | #6d7b76 | Supporting copy |

## 3. Typography
- Primary: system sans stack for reliable local rendering and Chinese text.
- Mono: ui-monospace stack for IDs, status codes, and timestamps.
- Scale: 42px page title, 28px summary number, 19px card title, 16px body, 13px supporting text, 11px overline.

## 4. Spacing & Layout
- Base unit: 4px.
- Content width: 1240px; page padding 24px desktop and 16px mobile.
- Dashboard: four-column service grid, collapsing to two and one columns at 900px and 600px.
- Details: full-width overflow-safe table with a document-level scroll owner.

## 5. Components
### Service Card
- Structure: link, service index, status pill, title, count, message, detail affordance.
- States: default, hover, focus, unavailable, empty.
- Accessibility: native link semantics and visible focus inherited from browser.
- Motion: 180ms transform and shadow on hover only.

### Status Pill
- Variants: ok, partial, empty, not_configured, unavailable.
- Accessibility: status text remains visible; color is not the only signal.

### Resource Table
- Structure: semantic table, type, name, ID, expandable JSON details.
- States: populated, empty, unavailable.
- Accessibility: table headers, native details disclosure, horizontal overflow on narrow screens.

## 6. Motion & Interaction
- Hover lift uses transform and shadow for service cards.
- No essential information depends on animation.
- Reduced-motion users receive the same content without transition reliance.

## 7. Depth & Surface
Mixed: dark masthead for structural depth, tonal paper/panel separation for content, and a restrained hover shadow only for interactive cards.

## 8. Accessibility Constraints & Accepted Debt
- WCAG 2.2 AA target; body text remains at least 13px for metadata and 16px for prose; keyboard-native links and disclosures are preserved.
- Accepted debt: no client-side auto-refresh control in this first read-only slice; refresh is bounded server-side by the cache interval and can be revisited after live cluster feedback.
