# Suggestion Lifecycle, Notifications & Re-analyze Fix

> Chronicle: 0002__2026-03-15__suggestion-lifecycle-and-notifications.md
> Status: In Progress

## User Requirements (Complete)

"re-analyze does not work though, also the Suggestions should have a timestamp on how it was suggested, followed by when it was READ by (user) and if and when was Accepted or Dismissed! It's important! if dismissed we can also put a Reason. Some suggestions and action point can also be assigned to users (and in this way we could wired up Notifications)"

Three distinct asks:
1. **Re-analyze button is broken** — appears to do nothing
2. **Suggestion lifecycle tracking**: suggested_at (exists), read_at + read_by, resolved_at (exists), dismiss_reason (new), assigned_to + assigned_at (new)
3. **Notifications**: wire assignment events to a notification feed, visible in the UI

## Context

- `insight_suggestions` table: id, stave_id, tenant_id, report_id, priority, category, action, reasoning, based_on, status, resolved_at, created_at — no read/assign/dismiss-reason fields
- `/insights/{stave_id}/suggest/{id}/accept` and `/dismiss` routes exist but dismiss has no reason support
- Re-analyze: `triggerAnalysis()` dispatches then sleeps 2s then reloads — analysis takes ~30s so stale data is shown
- `/insights/{stave_id}/analyze/{task_id}` polling endpoint already exists
- `notifications.vue` + `useNotifications.ts` exist but only pull from `checks` (failed check runs), not from insights assignments
- Users table: id, username, email (no avatar/display_name yet)

**Key references:**
- `datametronome/podium/datametronome_podium/features/insights/` — model, repo, schema, router
- `datametronome/podium/alembic/versions/004_intelligence_store.py` — migration to extend
- `ui-nuxt/pages/insights.vue` — re-analyze + suggestion cards UI
- `ui-nuxt/composables/useNotifications.ts` — extend with assignment events
- `ui-nuxt/layouts/dashboard.vue` — notification badge in nav

## Project State

**Before:** Re-analyze dispatches task but reloads before completion. Suggestions show action text only — no timestamps, no read tracking, no dismiss reason, no assignment, no notifications.

**After:** Re-analyze polls until task completes. Suggestion cards show full lifecycle timeline (suggested → read → resolved). Dismissal captures reason. Any suggestion can be assigned to a user, triggering a DB notification. Notification feed in sidebar shows unread count.

## Objective (The WHY)

Suggestions without lifecycle context are unactionable — you can't tell if a teammate has already seen something, why it was dismissed, or who owns it. The user wants DataMetronome to function like a data quality ticketing system where AI findings have an owner and audit trail. Notifications close the loop so the assignee actually knows about it.

## Affected Areas

| Area | Files/Modules | Impact |
|------|---------------|--------|
| DB migration | `alembic/versions/005_suggestion_lifecycle.py` | Add read_at, read_by, dismiss_reason, assigned_to, assigned_at + new notifications table |
| Domain model | `features/insights/model.py` | Add new fields to InsightSuggestion; new Notification model |
| Repo | `features/insights/repo.py` | mark_read, assign, dismiss_with_reason, notification CRUD |
| Schema | `features/insights/schema.py` | Update SuggestionResponse; NotificationResponse |
| Router | `features/insights/router.py` | /mark-read, /assign, dismiss with reason body, /notifications |
| Frontend service | `services/insights.ts` | markRead, assign, dismissWithReason, getNotifications |
| Insights page | `pages/insights.vue` | Re-analyze polling, lifecycle timeline, dismiss modal, assign |
| Notifications | `composables/useNotifications.ts` | Merge API notifications with check-based ones |
| Layout | `layouts/dashboard.vue` | Live badge with unread count |

## Discoveries & Insights

- **2026-03-15**: Re-analyze root cause confirmed — the 2s sleep is far too short for Gemini 2.5 Pro (~30s). The polling endpoint already exists, just needs to be used.
- **2026-03-15**: `notifications` table is a clean new addition — existing `useNotifications` only uses localStorage for check failures; need to merge both sources.
- **2026-03-15**: Dismiss reason and assignment are additive columns — safe to migrate without touching existing data.

---

## CLAUDE.md Updates

### Updates to apply:

- [ ] None yet — patterns to emerge from implementation
