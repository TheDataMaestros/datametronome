# Datasource-Aware Dashboard Design

**Date:** 2026-03-15
**Status:** Draft
**Branch:** feat/data-intelligence

---

## Problem

The current dashboard Intelligence Pulse aggregates all datasource intelligence into a single view — a single health score, a single list of suggestions, a single list of anomalies — with no indication of which datasource each item belongs to. The backend already stores intelligence data per-stave; the dashboard is actively discarding that context.

---

## Goal

Make the Intelligence Pulse explicitly scoped to a datasource. Users can switch context between sources using a selector bar, pin up to 3 favourites, and always know which source they are looking at.

---

## Selector Bar

### Behaviour

The selector bar sits at the top of the Intelligence Pulse section, replacing the current unlabelled header.

**No favourites yet (new user / no stars set):**
- Show "All" pill + one pill per active stave.
- If there are more than 4 staves (All + 3 visible + overflow), show an "Others (N) ▾" pill for the rest.
- No star UI is shown in this state — the favourites concept is dormant.

**Once the user stars at least one source:**
- Bar becomes: `All | ★ fav1 | ★ fav2 | ★ fav3 | Others (N) ▾`
- Stars are visible on all pills (filled ★ on favourited, ghost ☆ on hover for non-favourited).
- Clicking a ghost ☆ promotes that source to favourites (up to 3 max).
- When 3 favourites are set, remaining ☆ buttons are disabled with a "max reached" tooltip.

**Health dot:** Every source pill shows a small colored dot (green ≥80, amber 50–79, red <50) derived from its current health score. This gives status at a glance without clicking.

**Others dropdown:**
- Lists all non-pinned sources with health dot, name, score, and ☆ pin button.
- Sources within the dropdown are also clickable to select/scope the Pulse.
- If there are more than ~8 sources in Others, a "+ N more" footer links to the full staves list.

### Selector rules summary

| Scenario | Bar contents |
|---|---|
| 0 favourites, ≤4 staves | All \| s1 \| s2 \| s3 \| s4 |
| 0 favourites, >4 staves | All \| s1 \| s2 \| s3 \| Others(N) |
| 1–3 favourites, any count | All \| ★f1 \| ★f2 \| ★f3 \| Others(N) |

---

## Intelligence Pulse Scoping

### "All" selected (default)

The existing aggregated view is preserved with one addition: every action item card (suggestion, anomaly) gains a **source label badge** (e.g. `analytics_db`) so items are no longer anonymous.

### Specific source selected

- The entire Pulse panel (health gauge, source coverage, action items) reflects only that stave's data.
- A small context banner below the selector confirms the active scope: `Viewing: analytics_db · analytics · 67/100`.
- Data is fetched from the existing per-stave insights API (`GET /insights/{stave_id}/dashboard`) rather than the aggregated dashboard endpoint.

---

## Favourites Storage

Favourites are stored per user as a JSON field on the existing user record:

```json
{ "pinned_staves": ["stave-uuid-1", "stave-uuid-2", "stave-uuid-3"] }
```

- Field name: `dashboard_prefs` (JSON) on the `users` table.
- Max 3 entries enforced at the API level.
- Order of the array determines order in the selector bar (drag-to-reorder in settings writes a new order).
- Stale IDs (deleted staves) are silently ignored on read.

### API changes required

| Endpoint | Change |
|---|---|
| `PATCH /users/me` | Accept `dashboard_prefs: { pinned_staves: string[] }` |
| `GET /users/me` | Return `dashboard_prefs` field |
| `GET /metrics/dashboard` | Add `stave_id` to each item in `top_suggestions` and `top_anomalies` arrays |

No new endpoints needed. Per-stave intelligence data is already available at `GET /insights/{stave_id}/dashboard`.

---

## Settings Page (Profile → Dashboard Preferences)

A new section under the user profile page:

- Lists all active staves with drag handle, health dot, domain badge, and pin toggle.
- Pinned sources show "★ Pinned" (amber); unpinned show "☆ Pin".
- When 3 are pinned, unpinned toggles show "☆ Pin (max reached)" and are non-interactive.
- Drag-to-reorder updates the `pinned_staves` array order.

---

## Frontend Components

| Component | Location | Responsibility |
|---|---|---|
| `DatasourceSelector.vue` | `ui-nuxt/components/` | Selector bar: pills, Others dropdown, star logic |
| `index.vue` | `ui-nuxt/pages/` | Hosts selector, passes selected stave ID to Pulse |
| Intelligence Pulse section | `index.vue` | Fetch per-stave when `selectedStaveId !== null`, aggregated otherwise |
| `profile.vue` or `settings.vue` | `ui-nuxt/pages/` | Dashboard Preferences section |

---

## Data Flow

```
User selects "All"
  → fetch GET /metrics/dashboard  (existing)
  → render aggregated Pulse with source labels on each item

User selects "analytics_db"
  → fetch GET /insights/{stave_id}/dashboard  (existing)
  → render scoped Pulse for that stave
  → context banner shows stave name + domain + score

User stars a source (inline ☆ on pill)
  → optimistic UI update (star fills immediately)
  → PATCH /users/me { dashboard_prefs: { pinned_staves: [...] } }
  → on error: revert star

User reorders in Settings
  → drag ends → PATCH /users/me with new order
  → selector bar re-renders in new order
```

---

## Out of Scope

- Multi-select (viewing 2 sources simultaneously) — not in this iteration.
- Per-source "Run Analysis" from the selector — stays on the Insights page.
- Macrocategory grouping (e.g. "production" vs "staging") — noted as a natural next step once favourites are in place.

---

## Open Questions

None — all design decisions resolved in brainstorming session.
