# Intelligence Pulse Dashboard & Chat Proactive Insights

> Chronicle: 0001__2026-03-15__intelligence-pulse-dashboard-and-chat-proactive-insights.md
> Status: Completed

## User Requirements (Complete)

- Read HANDOFF.md and execute the next steps
- Focus on dashboard frontend expansion with `/frontend-dev` and `/frontend-design` skills
- Improve the chat proactive insights (InsightAgent should lead with health score/findings, not just list tables)

## Context

The data intelligence backend layer is fully implemented (8 chunks, 420+ tests). The `/metrics/dashboard` API already returns an `intelligence` section with health score, report counts, anomaly counts, and pending suggestions. However, the Nuxt dashboard UI was not rendering any of this data — the `DashboardMetrics` TypeScript type did not include the `intelligence` field, and there were no UI components for it.

The InsightAgent system prompt instructed it to list tables and explore data, but did not instruct it to proactively call `get_stave_intelligence` to surface existing health scores and findings at the start of a conversation.

**Key references:**
- `ui-nuxt/pages/index.vue` — dashboard page, now has Intelligence Pulse section
- `ui-nuxt/services/dashboard.ts` — added `IntelligenceMetrics` interface
- `ui-nuxt/composables/useDashboard.ts` — added intelligence defaults
- `ui-nuxt/assets/css/main.css` — added intelligence panel CSS
- `datametronome/podium/datametronome_podium/services/agents/insight.py` — updated system prompt

## Project State

**Before:** Dashboard showed 4 metric cards (success rate, active sources, quality checks, anomalies) with no intelligence data. InsightAgent would list tables when asked about data instead of leading with existing analysis. `DashboardMetrics` TypeScript type had no `intelligence` field.

**After:** Dashboard shows a full "Intelligence Pulse" section with animated SVG health score gauge, source coverage progress bar, and action items (suggestions + anomalies). InsightAgent now calls `get_stave_intelligence` as step 0 and leads with health score and findings when analysis exists.

## Objective (The WHY)

The intelligence layer was built but invisible — users had to manually invoke chat to see any AI insights. The dashboard is the landing page; surfacing the health score and action items there creates immediate value and directs users to the chat for deeper exploration.

## Affected Areas

| Area | Files/Modules | Impact |
|------|---------------|--------|
| Dashboard types | `ui-nuxt/services/dashboard.ts` | Added `IntelligenceMetrics` interface, optional `intelligence` field on `DashboardMetrics` |
| Dashboard composable | `ui-nuxt/composables/useDashboard.ts` | Added `intelligence: undefined` in error fallback |
| Dashboard page | `ui-nuxt/pages/index.vue` | Added `intelligence` computed + full Intelligence Pulse section template |
| Styles | `ui-nuxt/assets/css/main.css` | Added `.intelligence-panel`, `.intelligence-domain-badge`, `.health-arc-fill` + `draw-gauge` keyframe |
| InsightAgent | `services/agents/insight.py` | Added step 0 to system prompt: always call `get_stave_intelligence` first, lead with health score |

## Discoveries & Insights

- **2026-03-15**: SVG arc gauge math: r=42, C≈264, 270° arc = 198px. `stroke-dashoffset` animation from 198 (empty) to `198 - arcLength` (filled), with CSS `@keyframes draw-gauge { from { stroke-dashoffset: 198 } }` and final value set via HTML attribute. Clean CSS-only animation.
- **2026-03-15**: Intelligence section is conditionally rendered (`v-if="intelligence"`) so the dashboard degrades gracefully when no analysis has run yet.
- **2026-03-15**: `profiled_sources` vs `active_sources` — `profiled_sources` from the intelligence section counts distinct staves profiled; `active_sources` is the total active staves from outer metrics. Progress bar shows coverage ratio (may exceed 100% if source was profiled then deactivated — capped at 100%).

---

## CLAUDE.md Updates

### Updates to apply:

- [ ] Root `CLAUDE.md` — SVG arc gauge pattern: `stroke-dashoffset` animation with CSS `@keyframes from {}` + HTML final value attribute
