"""Intelligence pipeline service -- orchestrates stages 1-5."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from datametronome_podium.archetypes import load_archetype, match_archetypes
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.insights.model import (
    BaselineSnapshot,
    DataProfile,
    InsightCreatedCheck,
    InsightReport,
    InsightSuggestion,
    StaveQueryPlan,
)
from datametronome_podium.features.insights.repo import InsightsRepo

logger = logging.getLogger(__name__)


class InsightPipelineService:
    """Runs the 5-stage intelligence pipeline."""

    def __init__(self, executor: QueryExecutor) -> None:
        self.executor = executor
        self.repo = InsightsRepo(executor)

    # ------------------------------------------------------------------
    # Stage 1: Discovery
    # ------------------------------------------------------------------

    async def _discover_schema(self, stave_id: str) -> dict[str, Any]:
        """Discover tables, columns, and sample data for a stave.

        Uses the stave's connection config via ConnectionTester to query
        the data source directly.
        """
        from datametronome_podium.services.connection_tester import ConnectionTester
        from datametronome_podium.services.stave_service import deserialize_stave

        stave_rows = await self.executor.query(
            "SELECT * FROM staves WHERE id = ?", [stave_id],
        )
        if not stave_rows:
            raise ValueError(f"Stave not found: {stave_id}")

        stave = deserialize_stave(stave_rows[0])
        tester = ConnectionTester()
        connector = await tester.get_connector(stave, read_only=True)

        try:
            table_names = await _list_tables_for_stave(connector, stave)
            schema, samples = await _collect_schema_and_samples(
                connector, table_names, stave
            )
        finally:
            try:
                await connector.close()
            except Exception:
                pass

        return {"tables": table_names, "schema": schema, "samples": samples}

    # ------------------------------------------------------------------
    # Stage 2: Classification
    # ------------------------------------------------------------------

    async def classify_domain(
        self,
        table_names: list[str],
        schema: dict,
        samples: dict,
    ) -> dict[str, Any]:
        """Classify the business domain using deterministic matching + LLM."""
        matches = match_archetypes(table_names)
        candidates = [(name, score) for name, score in matches if score >= 0.4]

        try:
            return await self._llm_classify(
                table_names, schema, samples, candidates
            )
        except Exception as exc:
            logger.warning(
                "LLM classification failed: %s. Falling back to deterministic.",
                exc,
            )
            return _deterministic_fallback(candidates, exc)

    async def _llm_classify(
        self,
        table_names: list[str],
        schema: dict,
        samples: dict,
        candidates: list[tuple[str, float]],
    ) -> dict[str, Any]:
        """Use LLM to confirm/refine domain classification."""
        from pydantic_ai import Agent

        from datametronome_podium.services.agent_factory import (
            build_heavy_model_from_settings,
        )
        from datametronome_podium.services.agents.insight_models import (
            LLMDomainClassification,
        )

        model = build_heavy_model_from_settings()

        candidate_info = _format_candidate_info(candidates)
        schema_summary = {
            k: list(v.keys()) if isinstance(v, dict) else str(v)
            for k, v in list(schema.items())[:10]
        }
        prompt = (
            "Classify this database's business domain.\n\n"
            f"Tables: {table_names}\n"
            f"Schema summary: {json.dumps(schema_summary, indent=2)}\n"
            f"{candidate_info}\n\n"
            "Respond with: domain_type, confidence (0-1), business_context "
            "(1 sentence), entity_roles (fact/dimension/event tables), "
            "matched_archetype (if any)."
        )

        agent: Agent[None, LLMDomainClassification] = Agent(  # ty: ignore[invalid-assignment]
            model=model,
            output_type=LLMDomainClassification,
            retries=2,
        )
        result = await agent.run(prompt)
        return result.output.model_dump()

    # ------------------------------------------------------------------
    # Stage 3: Baseline Snapshot
    # ------------------------------------------------------------------

    async def capture_baseline(
        self,
        stave_id: str,
        discovery: dict[str, Any],
        snapshot_type: str = "daily",
    ) -> BaselineSnapshot:
        """Capture quantitative baseline metrics for all tables."""
        now = _utc_now_iso()
        table_metrics = _build_table_metrics(discovery)

        snapshot = BaselineSnapshot(
            id=f"snap-{uuid.uuid4()}",
            stave_id=stave_id,
            tenant_id="default",
            snapshot_type=snapshot_type,  # ty: ignore[invalid-argument-type]
            table_metrics=table_metrics,
            column_stats={},
            captured_at=now,
        )
        await self.repo.create_snapshot(snapshot)
        return snapshot

    # ------------------------------------------------------------------
    # Stage 4: Business Analysis
    # ------------------------------------------------------------------

    async def analyze_business(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        profile: DataProfile | None = None,
    ) -> dict[str, Any]:
        """LLM-powered business analysis with dynamic context."""
        from pydantic_ai import Agent

        from datametronome_podium.services.agent_factory import (
            build_heavy_model_from_settings,
        )
        from datametronome_podium.services.agents.insight import (
            _build_system_prompt,
        )
        from datametronome_podium.services.agents.insight_models import (
            LLMInsightReport,
        )

        archetype_ctx, profile_ctx = _build_analysis_context(profile)

        historical_ctx = await self._build_historical_context(stave_id)

        system_prompt = _build_system_prompt(
            archetype_context=archetype_ctx,
            profile_context=profile_ctx,
            historical_context=historical_ctx,
        )

        model = build_heavy_model_from_settings()
        agent: Agent[None, LLMInsightReport] = Agent(  # ty: ignore[invalid-assignment]
            model=model,
            output_type=LLMInsightReport,
            system_prompt=system_prompt,
            retries=2,
        )

        domain_info = (
            f"Domain: {profile.domain_type}" if profile else "Domain not yet classified."
        )
        prompt = (
            "Analyze this data source and produce a business insight report.\n\n"
            f"Current snapshot metrics:\n"
            f"{json.dumps(snapshot.table_metrics, indent=2)}\n\n"
            f"{domain_info}\n\n"
            "Produce: health_score (0-100), dimensions (scored), "
            "anomalies (with evidence), suggestions (actionable), "
            "summary (natural language), key_findings, and any checks_to_create.\n"
            'report_type: "daily"'
        )

        result = await agent.run(prompt)
        return result.output.model_dump()

    async def _build_historical_context(self, stave_id: str) -> str | None:
        """Load previous snapshots for comparison."""
        history = await self.repo.list_snapshots(stave_id, days=30, limit=30)
        if len(history) > 1:
            prev = history[1]
            return (
                f"Previous snapshot ({prev.captured_at}): "
                f"{json.dumps(prev.table_metrics)}"
            )
        return None

    # ------------------------------------------------------------------
    # Track 2: Business Intelligence
    # ------------------------------------------------------------------

    async def _analyze_business_intelligence(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        profile: DataProfile | None,
        discovery: dict | None = None,
        fingerprint: str | None = None,
    ) -> dict[str, Any] | None:
        """Run the three-phase BusinessIntelligenceAgent.

        discovery + fingerprint are provided for full pipeline runs (auto-scan, daily).
        Both are None for on-demand runs, which skip Phases 1+2 and use the existing plan.
        """
        if not profile or profile.domain_type == "generic":
            logger.info(
                "Skipping BI analysis for stave %s — no domain profile",
                stave_id,
            )
            return None

        from datametronome_podium.services.agent_factory import (
            build_heavy_model_from_settings,
        )
        from datametronome_podium.services.agents.business_intelligence import (
            run_phase1_schema_overview,
            run_phase2_generate_and_validate,
            run_phase3_execute_and_analyze,
        )
        from datametronome_podium.services.connection_tester import ConnectionTester
        from datametronome_podium.services.stave_service import deserialize_stave

        archetype = load_archetype(profile.domain_type)
        if not archetype or not archetype.get("kpi_definitions"):
            logger.info(
                "No BI kpi_definitions for domain %s", profile.domain_type
            )
            return None

        connector = None
        schema_interpretation = None

        try:
            stave_rows = await self.executor.query(
                "SELECT * FROM staves WHERE id = ?", [stave_id]
            )
            if not stave_rows:
                return None
            stave = deserialize_stave(stave_rows[0])

            config = stave.connection_config or {}
            ds_type = (stave.data_source_type or "").lower()
            schema_prefix = ""
            if ds_type in ("postgres", "postgresql"):
                pg_schema = config.get("schema", "public")
                schema_prefix = f'"{pg_schema}".'

            # Determine whether we need to regenerate the query plan
            existing_plan = await self.repo.get_valid_plan(stave_id)
            now_iso = _utc_now_iso()

            needs_generation = False
            if discovery is not None and fingerprint is not None:
                # Full pipeline run: check fingerprint
                if existing_plan is None:
                    needs_generation = True
                elif existing_plan.schema_fingerprint != fingerprint:
                    logger.info(
                        "Schema fingerprint changed for stave %s — invalidating plan",
                        stave_id,
                    )
                    await self.repo.invalidate_plan(stave_id, now_iso)
                    needs_generation = True
            # On-demand (discovery=None): always use existing plan; no generation

            model = build_heavy_model_from_settings()
            tester = ConnectionTester()
            connector = await tester.get_connector(stave, read_only=True)

            plan_skipped: list[dict[str, str]] = []

            if needs_generation:
                # Phase 1: schema overview (no DB connection)
                logger.info("Phase 1: schema overview for stave %s", stave_id)
                schema_interpretation = await run_phase1_schema_overview(
                    discovery, archetype, model  # ty: ignore[invalid-argument-type]
                )

                # Phase 2: generate + validate SQL
                logger.info("Phase 2: query generation for stave %s", stave_id)
                generated = await run_phase2_generate_and_validate(
                    schema_interpretation, archetype, connector, schema_prefix, model
                )
                if generated is None:
                    logger.warning(
                        "Phase 2 aborted for stave %s — abort threshold hit",
                        stave_id,
                    )
                    return None

                new_plan = StaveQueryPlan(
                    id=str(uuid.uuid4()),
                    stave_id=stave_id,
                    tenant_id=profile.tenant_id,
                    schema_fingerprint=fingerprint,  # ty: ignore[invalid-argument-type]
                    kpi_queries=generated.kpi_queries,
                    performer_queries=generated.performer_queries,
                    skipped=generated.skipped,
                    generated_by_model=str(model),
                    generated_at=now_iso,
                )
                await self.repo.create_plan(new_plan)
                active_plan = new_plan
                plan_skipped = generated.skipped
            elif existing_plan is not None:
                active_plan = existing_plan
                plan_skipped = existing_plan.skipped
            else:
                # On-demand with no existing plan — skip BI track
                logger.info(
                    "No query plan for stave %s, skipping BI track", stave_id
                )
                return None

            # Phase 3: execute + analyze
            logger.info("Phase 3: BI analysis for stave %s", stave_id)
            try:
                bi_report = await run_phase3_execute_and_analyze(
                    kpi_queries=active_plan.kpi_queries,
                    performer_queries=active_plan.performer_queries,
                    skipped=plan_skipped,
                    connector=connector,
                    schema_prefix=schema_prefix,
                    domain_type=profile.domain_type,
                    model=model,
                )
            except Exception as exc:
                logger.warning(
                    "Phase 3 execution failed for stave %s — invalidating plan: %s",
                    stave_id,
                    exc,
                )
                await self.repo.invalidate_plan(stave_id, now_iso)
                return None
            result = bi_report.model_dump()
            if schema_interpretation is not None:
                result["_schema_interpretation"] = schema_interpretation.model_dump()
            return result

        except Exception as exc:
            logger.warning(
                "BI analysis failed for stave %s: %s", stave_id, exc
            )
            return None
        finally:
            if connector is not None:
                try:
                    await connector.close()
                except Exception:
                    pass

    async def _run_both_tracks(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        profile: DataProfile | None,
        discovery: dict | None = None,
        fingerprint: str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Run Track 1 (data quality) then Track 2 (BI) sequentially.

        Sequential execution avoids Celery prefork event loop issues where
        concurrent asyncio tasks can fail if a pydantic-ai / httpx client
        retains a reference to the previous task's closed event loop.
        """
        quality: dict[str, Any] | None = None
        bi: dict[str, Any] | None = None

        try:
            quality = await self.analyze_business(stave_id, snapshot, profile)
        except Exception as exc:
            logger.warning(
                "Track 1 (data quality) failed for stave %s: %s", stave_id, exc
            )

        try:
            bi = await self._analyze_business_intelligence(
                stave_id, snapshot, profile,
                discovery=discovery, fingerprint=fingerprint,
            )
        except Exception as exc:
            logger.warning(
                "Track 2 (BI) failed for stave %s: %s", stave_id, exc
            )

        return quality, bi

    # ------------------------------------------------------------------
    # Stage 5: Suggest + Act
    # ------------------------------------------------------------------

    async def persist_results(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        analysis: dict[str, Any] | None,
        classification: dict[str, Any] | None = None,
        discovery: dict[str, Any] | None = None,
        bi_analysis: dict[str, Any] | None = None,
    ) -> InsightReport:
        """Persist analysis results: report, suggestions, checks, profile."""
        now = _utc_now_iso()

        await self._upsert_profile(
            stave_id, classification, analysis, now, discovery
        )

        report = _build_report(stave_id, snapshot, analysis, now)
        await self.repo.create_report(report)

        await self._persist_suggestions(stave_id, report, now)
        await self._persist_auto_checks(stave_id, report, analysis, now)

        # Track 2: persist BI report if available
        if bi_analysis:
            if "_schema_interpretation" in bi_analysis:
                interp = bi_analysis.pop("_schema_interpretation")
                await self.repo.update_profile(stave_id, {
                    "schema_interpretation": json.dumps(interp),
                })
            await self._persist_business_report(
                stave_id, snapshot.id, bi_analysis, now
            )

        return report

    async def _upsert_profile(
        self,
        stave_id: str,
        classification: dict[str, Any] | None,
        analysis: dict[str, Any] | None,
        now: str,
        discovery: dict[str, Any] | None = None,
    ) -> None:
        """Create or update the data profile with classification + patterns."""
        profile = await self.repo.get_profile(stave_id)

        schema_map = discovery.get("schema", {}) if discovery else {}

        if classification and not profile:
            profile = DataProfile(
                id=f"dp-{uuid.uuid4()}",
                stave_id=stave_id,
                tenant_id="default",
                domain_type=classification["domain_type"],
                domain_confidence=classification["confidence"],
                domain_context={
                    "business_context": classification.get("business_context", "")
                },
                schema_map=schema_map,
                entity_roles=classification.get("entity_roles", {}),
                created_at=now,
                updated_at=now,
            )
            await self.repo.create_profile(profile)

        elif classification and profile:
            update: dict[str, Any] = {
                "domain_type": classification["domain_type"],
                "domain_confidence": classification["confidence"],
                "domain_context": {
                    "business_context": classification.get("business_context", "")
                },
                "entity_roles": classification.get("entity_roles", {}),
            }
            if schema_map:
                update["schema_map"] = schema_map
            if profile.domain_type != classification["domain_type"]:
                update["profile_version"] = profile.profile_version + 1
                update["previous_classification"] = {
                    "domain_type": profile.domain_type,
                    "confidence": profile.domain_confidence,
                    "changed_at": now,
                }
            await self.repo.update_profile(stave_id, update)

        if analysis and profile:
            await self._accumulate_patterns(stave_id, profile, analysis, now)

    async def _accumulate_patterns(
        self,
        stave_id: str,
        profile: DataProfile,
        analysis: dict[str, Any],
        now: str,
    ) -> None:
        """Merge new anomaly patterns into learned_patterns."""
        new_patterns: dict[str, Any] = {}
        for anomaly in analysis.get("anomalies", []):
            key = f"{anomaly.get('category')}_{anomaly.get('table')}"
            existing = profile.learned_patterns.get(key, {})
            new_patterns[key] = {
                "first_seen": existing.get("first_seen", now),
                "last_seen": now,
                "occurrences": existing.get("occurrences", 0) + 1,
            }
        if new_patterns:
            merged = {**profile.learned_patterns, **new_patterns}
            await self.repo.update_profile(stave_id, {"learned_patterns": merged})

    async def _persist_suggestions(
        self, stave_id: str, report: InsightReport, now: str
    ) -> None:
        """Persist each suggestion from the report."""
        for sug in report.suggestions:
            suggestion = InsightSuggestion(
                id=f"sug-{uuid.uuid4()}",
                stave_id=stave_id,
                tenant_id="default",
                report_id=report.id,
                priority=sug.get("priority", "medium"),
                category=sug.get("category", "general"),
                action=sug.get("action", ""),
                reasoning=sug.get("reasoning", ""),
                based_on=sug.get("based_on", ""),
                check_spec=sug.get("check_spec"),
                created_at=now,
            )
            await self.repo.create_suggestion(suggestion)

    async def _persist_auto_checks(
        self,
        stave_id: str,
        report: InsightReport,
        analysis: dict[str, Any] | None,
        now: str,
    ) -> None:
        """Auto-create clefs from LLM check specs."""
        checks = analysis.get("checks_to_create", []) if analysis else []
        for spec in checks:
            try:
                await self._create_check_from_spec(
                    stave_id, report.id, spec, now
                )
            except Exception as exc:
                logger.warning("Failed to auto-create check: %s", exc)

    async def _create_check_from_spec(
        self, stave_id: str, report_id: str, spec: dict, now: str
    ) -> None:
        """Create a clef from an LLM-generated check spec and link it."""
        valid_types = {
            "row_count", "freshness", "column_values",
            "forecast", "data_profile_drift", "lookup_validation",
        }
        check_type = spec.get("check_type", "")
        if check_type not in valid_types:
            logger.warning("Skipping invalid check type: %s", check_type)
            return

        clef_id = f"clef-ai-{uuid.uuid4()}"
        clef_data = {
            "id": clef_id,
            "stave_id": stave_id,
            "name": f"AI: {spec.get('table', 'unknown')} {check_type}",
            "check_type": check_type,
            "config": json.dumps(spec.get("config", {})),
            "schedule": spec.get("schedule", "0 0 * * *"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        await self.executor.insert("clefs", clef_data)

        link = InsightCreatedCheck(
            id=f"icc-{uuid.uuid4()}",
            report_id=report_id,
            clef_id=clef_id,
            rationale=spec.get("rationale", "AI-generated check"),
            created_at=now,
        )
        await self.repo.create_check_link(link)

    async def _persist_business_report(
        self,
        stave_id: str,
        snapshot_id: str,
        bi_analysis: dict[str, Any],
        now: str,
    ) -> None:
        """Persist BusinessReport from BI track output."""
        from datametronome_podium.features.insights.model import BusinessReport

        report = BusinessReport(
            id=f"br-{uuid.uuid4()}",
            stave_id=stave_id,
            snapshot_id=snapshot_id,
            tenant_id="default",
            business_health_score=bi_analysis.get("business_health_score", 0),
            executive_summary=bi_analysis.get("executive_summary", ""),
            kpis=bi_analysis.get("kpis", []),
            top_performers=bi_analysis.get("top_performers", []),
            bottom_performers=bi_analysis.get("bottom_performers", []),
            trends=bi_analysis.get("trends", []),
            opportunities=bi_analysis.get("opportunities", []),
            risks=bi_analysis.get("risks", []),
            generated_at=now,
        )
        await self.repo.create_business_report(report)

    # ------------------------------------------------------------------
    # Full pipeline orchestrations
    # ------------------------------------------------------------------

    async def run_auto_scan(self, stave_id: str) -> InsightReport:
        """Full pipeline: 1 -> 2 -> 3 -> 4 -> 5.

        Includes business analysis so the first scan immediately produces
        a real health score, anomalies, and suggestions.
        """
        from datametronome_podium.services.agents.business_intelligence import (
            compute_schema_fingerprint,
        )

        discovery = await self._discover_schema(stave_id)
        classification = await self.classify_domain(
            discovery["tables"], discovery["schema"], discovery["samples"],
        )
        snapshot = await self.capture_baseline(
            stave_id, discovery, snapshot_type="auto_scan",
        )
        # Fetch existing profile (None on first run — analysis still works)
        profile = await self.repo.get_profile(stave_id)
        fingerprint = compute_schema_fingerprint(discovery.get("schema", {}))
        quality_analysis, bi_analysis = await self._run_both_tracks(
            stave_id, snapshot, profile,
            discovery=discovery, fingerprint=fingerprint,
        )
        return await self.persist_results(
            stave_id, snapshot, quality_analysis,
            classification=classification, discovery=discovery,
            bi_analysis=bi_analysis,
        )

    async def run_daily(self, stave_id: str) -> InsightReport:
        """Full pipeline 1 -> 2 -> 3 -> 4 -> 5 (with parallel BI track)."""
        from datametronome_podium.services.agents.business_intelligence import (
            compute_schema_fingerprint,
        )

        discovery = await self._discover_schema(stave_id)
        classification = await self.classify_domain(
            discovery["tables"], discovery["schema"], discovery["samples"],
        )
        snapshot = await self.capture_baseline(
            stave_id, discovery, snapshot_type="daily",
        )
        profile = await self.repo.get_profile(stave_id)
        fingerprint = compute_schema_fingerprint(discovery.get("schema", {}))
        quality_analysis, bi_analysis = await self._run_both_tracks(
            stave_id, snapshot, profile,
            discovery=discovery, fingerprint=fingerprint,
        )
        return await self.persist_results(
            stave_id, snapshot, quality_analysis,
            classification=classification, discovery=discovery,
            bi_analysis=bi_analysis,
        )

    async def run_on_demand(self, stave_id: str) -> InsightReport:
        """Stages 3 -> 4 -> 5 (reuse existing profile, fresh snapshot + BI)."""
        from datametronome_podium.services.agents.business_intelligence import (
            compute_schema_fingerprint,
        )
        discovery = await self._discover_schema(stave_id)
        fingerprint = compute_schema_fingerprint(discovery.get("schema", {}))
        snapshot = await self.capture_baseline(
            stave_id, discovery, snapshot_type="on_demand",
        )
        profile = await self.repo.get_profile(stave_id)
        quality_analysis, bi_analysis = await self._run_both_tracks(
            stave_id, snapshot, profile,
            discovery=discovery, fingerprint=fingerprint,
        )
        return await self.persist_results(
            stave_id, snapshot, quality_analysis,
            discovery=discovery, bi_analysis=bi_analysis,
        )


# ------------------------------------------------------------------
# Private helpers (kept module-level for single-responsibility)
# ------------------------------------------------------------------


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _list_tables_for_stave(connector: Any, stave: Any) -> list[str]:
    """List tables respecting the stave's data source type."""
    ds_type = (stave.data_source_type or "").lower()
    config = stave.connection_config or {}

    if not hasattr(connector, "list_tables"):
        logger.warning(
            "list_tables not available for %s connector", ds_type,
        )
        return []

    if ds_type == "bigquery":
        tables = await connector.list_tables(config.get("dataset"))
    elif ds_type in ("postgres", "postgresql"):
        tables = await connector.list_tables(config.get("schema", "public"))
    else:
        tables = await connector.list_tables()

    return [str(t) for t in tables]


async def _collect_schema_and_samples(
    connector: Any, table_names: list[str], stave: Any = None
) -> tuple[dict, dict]:
    """Collect schema info, row counts, and sample data for discovered tables."""
    schema: dict[str, Any] = {}
    samples: dict[str, Any] = {}

    # Build schema prefix for SQL queries (e.g., "olist".)
    sql_prefix = ""
    if stave:
        config = stave.connection_config if isinstance(stave.connection_config, dict) else {}
        ds_type = (stave.data_source_type or "").lower()
        if ds_type in ("postgres", "postgresql"):
            pg_schema = config.get("schema", "public")
            sql_prefix = f'"{pg_schema}".'

    for name in table_names[:20]:
        if hasattr(connector, "get_table_info"):
            try:
                info = await connector.get_table_info(name)
                schema[name] = info
            except Exception as exc:
                logger.warning("Failed to get schema for %s: %s", name, exc)

        # Get row count via COUNT(*)
        row_count = 0
        if hasattr(connector, "query"):
            try:
                count_sql = f'SELECT COUNT(*) as cnt FROM {sql_prefix}"{name}"'
                count_result = await connector.query(
                    {"sql": count_sql}
                )
                if count_result and isinstance(count_result, list) and len(count_result) > 0:
                    row = count_result[0]
                    if isinstance(row, dict):
                        row_count = row.get("cnt", row.get("count", 0))
            except Exception as exc:
                logger.warning("Failed to count rows for %s: %s", name, exc)

        # Get sample data
        sample_data: dict[str, Any] = {}
        if hasattr(connector, "sample_table"):
            try:
                raw_sample = await connector.sample_table(name, limit=100)
                if isinstance(raw_sample, list):
                    sample_data = {"rows": raw_sample}
                elif isinstance(raw_sample, dict):
                    sample_data = raw_sample
                else:
                    sample_data = {}
            except Exception as exc:
                logger.warning("Failed to sample table %s: %s", name, exc)
                sample_data = {"error": str(exc)}

        # Merge row_count into sample data
        sample_data["row_count"] = row_count
        samples[name] = sample_data

    return schema, samples


def _deterministic_fallback(
    candidates: list[tuple[str, float]], exc: Exception
) -> dict[str, Any]:
    """Build a classification result from deterministic matching only."""
    if candidates:
        return {
            "domain_type": candidates[0][0],
            "confidence": candidates[0][1],
            "business_context": (
                f"Detected via signature matching (LLM failed: {exc})"
            ),
            "entity_roles": {},
            "matched_archetype": candidates[0][0],
        }
    return {
        "domain_type": "generic",
        "confidence": 0.0,
        "business_context": "Could not classify domain",
        "entity_roles": {},
        "matched_archetype": None,
    }


def _format_candidate_info(candidates: list[tuple[str, float]]) -> str:
    """Format archetype candidates for LLM prompt."""
    if not candidates:
        return ""
    lines = [f"Top archetype candidates: {candidates}"]
    for name, _ in candidates[:3]:
        arch = load_archetype(name)
        if arch:
            lines.append(f"{name}: {arch.get('description', '')}")
    return "\n".join(lines)


def _build_analysis_context(
    profile: DataProfile | None,
) -> tuple[dict | None, dict | None]:
    """Build archetype and profile context dicts for analysis."""
    archetype_ctx = None
    profile_ctx = None

    if profile:
        if profile.domain_type != "generic":
            archetype_ctx = load_archetype(profile.domain_type)
        profile_ctx = {
            "domain_type": profile.domain_type,
            "learned_patterns": profile.learned_patterns,
        }

    return archetype_ctx, profile_ctx


def _build_table_metrics(discovery: dict[str, Any]) -> dict[str, Any]:
    """Extract table metrics from discovery samples."""
    table_metrics: dict[str, Any] = {}

    for table_name in discovery.get("tables", []):
        sample = discovery.get("samples", {}).get(table_name, {})

        if isinstance(sample, dict) and "error" in sample:
            table_metrics[table_name] = {
                "row_count": 0,
                "null_rates": {},
                "status": "skipped",
                "skip_reason": sample["error"],
            }
            continue

        row_count = sample.get("row_count", 0) if isinstance(sample, dict) else 0
        analysis = sample.get("analysis", {}) if isinstance(sample, dict) else {}

        null_rates: dict[str, float] = {}
        if isinstance(analysis, dict):
            for field_info in analysis.get("important_fields", []):
                if isinstance(field_info, dict) and "null_pct" in field_info:
                    null_rates[field_info.get("name", "")] = field_info["null_pct"]

        table_metrics[table_name] = {
            "row_count": row_count,
            "null_rates": null_rates,
            "status": "ok",
        }

    return table_metrics


def _build_report(
    stave_id: str,
    snapshot: BaselineSnapshot,
    analysis: dict[str, Any] | None,
    now: str,
) -> InsightReport:
    """Build an InsightReport model from analysis results."""
    if analysis:
        report_type = analysis.get("report_type", "daily")
        health_score = analysis.get("health_score", 50)
    else:
        report_type = "initial"
        health_score = 50

    return InsightReport(
        id=f"rpt-{uuid.uuid4()}",
        stave_id=stave_id,
        tenant_id="default",
        snapshot_id=snapshot.id,
        report_type=report_type,
        health_score=health_score,
        dimensions=analysis.get("dimensions", []) if analysis else [],
        anomalies=analysis.get("anomalies", []) if analysis else [],
        suggestions=analysis.get("suggestions", []) if analysis else [],
        summary=(
            analysis.get("summary", "Initial scan completed.")
            if analysis
            else "Initial scan completed."
        ),
        key_findings=analysis.get("key_findings", []) if analysis else [],
        created_at=now,
    )
