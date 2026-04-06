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

The selector bar sits at the top of the Intelligence Pulse section, replacing the current unlabelled header. It is populated from `GET /api/v1/staves` (returns `StaveResponse[]` with `id`, `name`, `is_active` — endpoint confirmed to exist) filtered to `is_active = true`.

**No active staves:** The Intelligence Pulse section is not rendered. The existing "No Insights Yet" empty state is shown instead.

**No favourites yet (new user / no stars set):**
- Show "All" pill + up to 3 source pills (worst health first, alphabetical tiebreaker) + "Others (N) ▾" if there are more than 3 staves.
- In this state the bar looks like a plain selector — no star icons are rendered. However, hovering any source pill reveals a ghost ☆ with a "Pin to bar" tooltip. Clicking it promotes that source to favourites and activates the favourites concept. This is the first-star discovery path.

**Once the user has at least one favourite:**
- Bar becomes: `All | ★ fav1 | ★ fav2 | ★ fav3 | Others (N) ▾`
- Favourites are shown in user-defined order (drag-to-reorder in Settings).
- Filled ★ on pinned pills; ghost ☆ on hover for all other pills.
- Clicking a ghost ☆ promotes that source to favourites (up to 3 max).
- When 3 favourites are set, all remaining ☆ buttons are disabled with a "max reached (3/3)" tooltip.
- While a PATCH to save a new favourite is in flight, all star buttons are disabled to prevent race conditions. Optimistic UI fills the star immediately; on API error the star reverts.

**Health dot:** Every source pill shows a small colored dot derived from its current health score:
- Green: score ≥ 80
- Amber: score 50–79
- Red: score < 50
- Grey (no dot): stave is active but has never been analysed (no entry in `stave_health_scores` map)

Health scores for the selector come from `intelligence.stave_health_scores` in the aggregated dashboard response (see API changes). Only active staves that have at least one `insight_report` are included in that map. Staves absent from the map (never analysed) are shown with a grey dot and sorted after all scored staves, alphabetically. The per-stave `GET /api/v1/insights/{stave_id}/dashboard` endpoint already returns `health_score`, confirming this field exists.

**Others dropdown:**
- Lists all remaining non-pinned staves with health dot, name, score, and ☆ pin button.
- All remaining staves are listed; no hard cap. If the list is very long (>10 items) it is scrollable within the dropdown.
- Sources within the dropdown are also clickable to select/scope the Pulse.
- N in "Others (N)" = total active staves − 3 (the 3 shown as inline pills).

### Selector rules summary

| Scenario | Bar contents |
|---|---|
| 0 active staves | No selector rendered — empty state shown |
| 0 favourites, ≤ 3 staves | All \| s1 \| s2 \| s3 (worst-health first, unscored last) |
| 0 favourites, > 3 staves | All \| s1 \| s2 \| s3 \| Others (active−3) |
| 1–3 favourites, any count | All \| ★ f1 \| ★ f2 \| ★ f3 \| Others (active−3) |

---

## Intelligence Pulse Scoping

### "All" selected (default)

The existing aggregated view is preserved as-is, including the "Source Coverage" panel (shows N-of-M active sources profiled, progress bar, and top table row counts). One addition: every action item card (suggestion, anomaly) gains a **source label badge** (e.g. `analytics_db`) so items are no longer anonymous. These labels come from the new `stave_id` and `stave_name` fields added to `top_suggestions` and `top_anomalies` in the dashboard response. If `stave_name` is null (e.g. orphaned record), fall back to displaying `stave_id`.

### Specific source selected

- The entire Pulse panel (health gauge, action items) reflects only that stave's data.
- Data is fetched from the existing per-stave endpoint `GET /api/v1/insights/{stave_id}/dashboard`.
- A context banner below the selector confirms the active scope: e.g. `Viewing: analytics_db · analytics · 67/100`. The domain segment (`analytics`) comes from `GET /api/v1/insights/{stave_id}/profile` (`domain_type` field, confirmed to exist in `DataProfileResponse`). If the profile is not yet available (404) or `domain_type` is null, the domain segment is omitted from the banner.
- The "Source Coverage" panel changes meaning in this view: it shows table coverage within that stave — number of tables profiled and top table row counts from the stave's `baseline_snapshot.table_metrics`. If no snapshot is available yet, display: "No snapshot available — run analysis to see table coverage."

---

## Favourites Storage

### DB change

Add a `dashboard_prefs` column (JSONB, not nullable) to the `users` table via an Alembic migration:

```python
# migration — server_default ensures all new and existing rows get '{}'
op.add_column('users', sa.Column(
    'dashboard_prefs',
    postgresql.JSONB,
    nullable=False,
    server_default='{}',
))
```

Structure:
```json
{ "pinned_staves": ["stave-uuid-1", "stave-uuid-2", "stave-uuid-3"] }
```

- `dashboard_prefs` is always a valid JSON object on read; the `pinned_staves` key may be absent (treat as empty list).
- Max 3 entries enforced at the API level (HTTP 400 if > 3 submitted).
- Unknown stave IDs are accepted at write time without validation; stale IDs are silently ignored on read.
- Array order = display order in selector bar.

### API changes

| Endpoint | Change |
|---|---|
| `GET /api/v1/auth/me` | Return `dashboard_prefs` field from user record |
| `PATCH /api/v1/auth/me` | New endpoint on the existing auth router. Accepts `{ "dashboard_prefs": { "pinned_staves": ["id1", ...] } }`. **Full replacement** of the `dashboard_prefs` object (not a merge). Validates max 3 entries (HTTP 400 if exceeded). Returns updated user object. |
| `GET /api/v1/metrics/dashboard` | Add `stave_id` (string) and `stave_name` (string, nullable — fall back to `stave_id`) to each item in `top_suggestions` and `top_anomalies` arrays. Add `stave_health_scores: { [stave_id]: number }` to the `intelligence` block — includes only active staves with at least one `insight_report`; staves with no report are omitted. |

`stave_id` is already a column on `insight_suggestions` — the existing SQL query simply needs to select it. `stave_name` is joined from the `staves` table (`LEFT JOIN staves ON insight_suggestions.stave_id = staves.id`).

No new endpoints needed. Per-stave intelligence data is already available at `GET /api/v1/insights/{stave_id}/dashboard`.

---

## Settings Page

A **new page** `ui-nuxt/pages/profile.vue` (route `/profile`), linked from the sidebar nav. It contains a "Dashboard Preferences" section with:

- All active staves listed with drag handle, health dot, name, domain badge, and pin toggle.
- Pinned sources show "★ Pinned" (amber); unpinned show "☆ Pin".
- When 3 are pinned, unpinned toggles show "☆ Pin (max reached)" and are non-interactive.
- Drag-to-reorder is implemented using [`vue-draggable-plus`](https://github.com/Alfred-Skyblue/vue-draggable-plus) (wraps SortableJS, compatible with Nuxt 3 / Vue 3). Drag end triggers `PATCH /api/v1/auth/me` with the new order.

---

## Frontend Components

| Component | Location | Responsibility |
|---|---|---|
| `DatasourceSelector.vue` | `ui-nuxt/components/` | Selector bar: pills, Others dropdown, star logic, in-flight disabled state |
| `index.vue` | `ui-nuxt/pages/` | Hosts selector, passes selected stave ID to Pulse, fetches scoped or aggregated data accordingly |
| Intelligence Pulse section | `index.vue` | Fetch `GET /insights/{stave_id}/dashboard` when a source is selected; aggregated endpoint when "All" |
| `profile.vue` | `ui-nuxt/pages/` | New page; Dashboard Preferences section with drag-to-reorder favourites |

---

## Data Flow

```
Page load
  → GET /api/v1/auth/me              (get pinned_staves; dashboard_prefs.pinned_staves or [])
  → GET /api/v1/staves               (get stave list: id, name, is_active)
  → GET /api/v1/metrics/dashboard    (aggregated; intelligence.stave_health_scores for dots)
  → render selector bar with correct pills and health dots

User selects "All" (default)
  → use already-fetched /metrics/dashboard data
  → render aggregated Pulse with source labels on each action item
  → Source Coverage panel: N-of-M sources profiled (unchanged)

User selects a specific source
  → GET /api/v1/insights/{stave_id}/dashboard  (health score, action items, snapshot table_metrics)
  → GET /api/v1/insights/{stave_id}/profile     (domain_type for context banner; skip if 404)
  → render scoped Pulse (health gauge, table coverage, action items for this stave)
  → context banner: stave name · domain (if available) · score
  → Source Coverage panel: table coverage within this stave (or placeholder if no snapshot)

User clicks ghost ☆ on a pill (inline star)
  → optimistic UI: star fills, all star buttons disabled
  → PATCH /api/v1/auth/me { dashboard_prefs: { pinned_staves: [...updated] } }
  → on success: re-enable buttons, selector re-renders
  → on error: revert star, show error toast

User reorders in Profile Settings
  → drag ends → PATCH /api/v1/auth/me with new order
  → selector bar re-renders in new order
```

---

## Out of Scope

- Multi-select (viewing 2 sources simultaneously).
- Per-source "Run Analysis" from the selector — stays on the Insights page.
- Macrocategory grouping (e.g. "production" vs "staging") — natural next step once favourites are in place.
