---
name: UX Retheme Plan
overview: Retheme the Mac Mini Dashboard to the Midjourney "bioluminescent terminal" design system, upgrade Tailwind to v4, replace the LogsModal with expandable table rows containing inline details and logs, and fix log text wrapping.
todos:
  - id: tailwind-v4
    content: "Upgrade Tailwind from v3 to v4: update package.json, postcss config, migrate tailwind.config.js to @theme block in index.css with Midjourney tokens"
    status: pending
  - id: typography
    content: Add JetBrains Mono via Google Fonts in index.html, set as default font in CSS, apply type scale (30px headings, 16px body, 14px caption)
    status: pending
  - id: retheme-app
    content: "Update App.tsx: gradient background, restyle nav tabs to Midjourney spec (Steel Navy, Portal Blue active, pill-style)"
    status: pending
  - id: retheme-fleet
    content: "Refactor FleetView.tsx: add expandable rows with click-anywhere + chevron, inline detail fields + log viewer + action buttons, remove LogsModal dependency"
    status: pending
  - id: delete-logs-modal
    content: Delete LogsModal.tsx and LogsModal.test.tsx
    status: pending
  - id: retheme-all-workloads
    content: "Update AllWorkloadsView.tsx: Midjourney colors, surface tokens, updated table styling"
    status: pending
  - id: retheme-audit
    content: "Update AuditView.tsx: Midjourney colors, translucent pill Pin button"
    status: pending
  - id: retheme-settings
    content: "Update SettingsView.tsx: Midjourney colors, restyle toggles and section headings"
    status: pending
  - id: update-tests
    content: Update FleetView tests for expandable row behavior, delete LogsModal tests, verify all other view tests pass with 100% coverage
    status: pending
isProject: false
---

# UX Retheme: Midjourney Design System + Expandable Rows

## Scope

Three UX enhancements applied globally across all four views (Fleet, All Workloads, Audit, Settings):
1. Midjourney "bioluminescent terminal" design system (colors, typography, spacing, surfaces)
2. Expandable table rows in Fleet view (replaces LogsModal)
3. Log text wrapping (pre-wrap instead of horizontal scroll)

## 1. Tailwind v3 to v4 Migration

**Files:**
- [apps/web/package.json](apps/web/package.json) -- upgrade `tailwindcss` to v4, update PostCSS deps
- [apps/web/tailwind.config.js](apps/web/tailwind.config.js) -- delete (replaced by `@theme` in CSS)
- [apps/web/src/index.css](apps/web/src/index.css) -- new `@theme` block with all Midjourney design tokens
- [apps/web/postcss.config.js](apps/web/postcss.config.js) -- update for v4 (uses `@tailwindcss/postcss` plugin)

Current Tailwind config defines three custom colors:

```4:14:apps/web/tailwind.config.js
  theme: {
    extend: {
      colors: {
        panel: "#1a1a1e",
        row: "#222228",
        border: "#33333a",
      },
    },
  },
```

These become CSS `@theme` tokens mapped to Midjourney equivalents:
- `panel` (#1a1a1e) -> Steel Navy (#1d293d)
- `row` (#222228) -> Abyssal Blue (#0f1c36)
- `border` (#33333a) -> keep as custom or map to Deep Slate area

**New `@theme` block** in `index.css` will include all Midjourney tokens: Cosmic Void, Abyssal Blue, Steel Navy, Deep Slate, Mist, Fog, Ash, Portal Blue, Specimen Green, Warning Amber, Fault Red, plus font-family for JetBrains Mono.

## 2. Typography: JetBrains Mono Everywhere

- Add Google Fonts link in [apps/web/index.html](apps/web/index.html): `<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">`
- Set `font-family` on `body` in `index.css` to `'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`
- Remove current system sans-serif stack from `index.css`
- Type scale: headings 30px/1.25, body 16px/1.5, caption 14px/1.63

## 3. Color and Surface Retheme

All views get updated classes. Key mappings:

- **Page background**: `bg-black` -> gradient via CSS (`linear-gradient(0deg, #06051d 30%, #061434)`)
- **Nav tabs**: current `bg-panel` / `text-gray-400` -> Steel Navy bg, Mist/Ghost White text, active = Portal Blue text
- **Table headers**: `text-gray-500` -> Ash (#2e3038) or Mist depending on contrast
- **Table rows**: `bg-row` -> Abyssal Blue, `hover:bg-[#2a2a32]` -> Deep Slate
- **Borders**: `border-border` -> Fog-tinted or Ash-tinted at low opacity
- **Severity dots**: emerald/orange/red -> Specimen Green/Warning Amber/Fault Red
- **Error banners**: current red-900/950 tints stay but use Fault Red/Crimson Depth
- **Buttons**: current bordered buttons -> translucent 20% opacity pill style (9999px radius for pill buttons, 8px for cards)
- **Text**: white/gray-200/gray-300/gray-400/gray-500 -> Ghost White/Ice Blue/Mist/Ash hierarchy

**Files touched for class updates:**
- [apps/web/src/App.tsx](apps/web/src/App.tsx) -- page background, nav tabs
- [apps/web/src/components/FleetView.tsx](apps/web/src/components/FleetView.tsx) -- table, severity dots, buttons
- [apps/web/src/components/AllWorkloadsView.tsx](apps/web/src/components/AllWorkloadsView.tsx) -- table, mobile cards
- [apps/web/src/components/AuditView.tsx](apps/web/src/components/AuditView.tsx) -- table, Pin button
- [apps/web/src/components/SettingsView.tsx](apps/web/src/components/SettingsView.tsx) -- toggle rows, headings

## 4. Expandable Table Rows (Fleet View)

Replace the LogsModal with click-to-expand rows in Fleet view.

**Current flow:** Click "Logs" button -> opens `LogsModal` overlay
**New flow:** Click anywhere on a row -> row expands vertically, revealing:
- Detail fields: `severity_reason`, `last_seen`, `metadata` (key-value pairs)
- Action buttons: Restart, Stop (moved from collapsed row)
- Inline log viewer: fetched on demand, `<pre>` with `white-space: pre-wrap`, max-height ~300px, `overflow-y: auto`

**Implementation approach:**
- Add `expandedId` state (string | null) to FleetView
- Each `<tr>` gets `onClick` to toggle expansion
- Expanded content renders in a second `<tr>` (with `colSpan` across all columns) immediately below the parent row
- Small chevron icon on the right of each row, rotates 90deg when expanded
- Logs fetch triggers when row expands (reuse existing `openLogs` logic)
- Remove `LogsModal` component import and usage

**Files:**
- [apps/web/src/components/FleetView.tsx](apps/web/src/components/FleetView.tsx) -- major refactor: expandable rows, inline logs, move actions
- [apps/web/src/components/LogsModal.tsx](apps/web/src/components/LogsModal.tsx) -- delete (replaced by inline logs)

## 5. Log Text Wrapping

The current LogsModal `<pre>` uses `overflow-auto` which causes horizontal scrollbar. The new inline log viewer uses:

```css
white-space: pre-wrap;
word-break: break-all;
overflow-y: auto;
max-height: 300px;
```

This is applied in the expanded row's log section within FleetView.

## 6. Test Updates

All existing tests have 100% coverage. Changes to component structure (removing LogsModal, adding expandable rows) will require test updates:

- [apps/web/tests/FleetView.test.tsx](apps/web/tests/FleetView.test.tsx) -- update for expandable row behavior, remove LogsModal references
- [apps/web/tests/LogsModal.test.tsx](apps/web/tests/LogsModal.test.tsx) -- delete or repurpose
- [apps/web/tests/AllWorkloadsView.test.tsx](apps/web/tests/AllWorkloadsView.test.tsx) -- verify class changes don't break selectors
- [apps/web/tests/AuditView.test.tsx](apps/web/tests/AuditView.test.tsx) -- same
- [apps/web/tests/SettingsView.test.tsx](apps/web/tests/SettingsView.test.tsx) -- same

## Risk / Notes

- **Tailwind v4 migration** is the highest-risk item -- class syntax changes could cascade. Run `npm run test:coverage` after migration to catch regressions early.
- **100% coverage gate** must be maintained. Deleting LogsModal.tsx means deleting its test file and ensuring the inline logs path is fully covered in FleetView tests.
- **No new dependencies** beyond Tailwind v4 ecosystem (`@tailwindcss/postcss`). JetBrains Mono loaded via Google Fonts CDN (no npm package).
