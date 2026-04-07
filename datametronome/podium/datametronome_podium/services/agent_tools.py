"""
Standalone async tool functions for DataMetronome agents.

These are extracted from ADKAgent and shared across all Pydantic AI sub-agents.
Each function calls the DB directly (no HTTP) and has no runtime deps on agent state.
"""
import logging

from datametronome_podium.core.database import get_executor

logger = logging.getLogger(__name__)


from datametronome_podium.core.query import quote_identifier as _quote_identifier


async def list_staves(
    limit: int = 100, skip: int = 0, active_only: bool = False
) -> dict[str, object]:
    """List all data sources (staves) in DataMetronome.

    Args:
        limit: Maximum number of staves to return (default: 100)
        skip: Number of staves to skip for pagination (default: 0)
        active_only: If True, return only active staves (is_active=True). Default: False (all staves)
    """
    try:
        from datetime import datetime

        from datametronome_podium.services.stave_service import deserialize_stave

        executor = get_executor()
        if active_only:
            staves = await executor.query(
                "SELECT * FROM staves WHERE is_active = TRUE ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [limit, skip],
            )
        else:
            staves = await executor.query(
                "SELECT * FROM staves ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [limit, skip],
            )

        staves_list = []
        for stave in staves:
            try:
                deserialized = deserialize_stave(stave)
                stave_dict = deserialized.model_dump()
                if isinstance(stave_dict.get("created_at"), datetime):
                    stave_dict["created_at"] = stave_dict["created_at"].isoformat()
                if isinstance(stave_dict.get("updated_at"), datetime):
                    stave_dict["updated_at"] = stave_dict["updated_at"].isoformat()
                staves_list.append(stave_dict)
            except Exception as e:
                logger.warning("Failed to deserialize stave %s: %s", stave.get('id', 'unknown'), e)
                continue

        return {"staves": staves_list, "count": len(staves_list)}
    except Exception as e:
        logger.error("Error listing staves: %s", e, exc_info=True)
        return {"error": f"Failed to list staves: {str(e)}", "staves": []}


async def get_stave(stave_id: str) -> dict[str, object]:
    """Get details about a specific data source (stave) by ID."""
    try:
        from datetime import datetime

        from datametronome_podium.services.stave_service import deserialize_stave

        executor = get_executor()
        staves = await executor.query(
            "SELECT * FROM staves WHERE id = ?", [stave_id]
        )

        if not staves:
            return {"error": f"Stave not found: {stave_id}"}

        deserialized = deserialize_stave(staves[0])
        stave_dict = deserialized.model_dump()
        if isinstance(stave_dict.get("created_at"), datetime):
            stave_dict["created_at"] = stave_dict["created_at"].isoformat()
        if isinstance(stave_dict.get("updated_at"), datetime):
            stave_dict["updated_at"] = stave_dict["updated_at"].isoformat()

        return stave_dict
    except Exception as e:
        logger.error("Error getting stave %s: %s", stave_id, e, exc_info=True)
        return {"error": f"Failed to get stave: {str(e)}"}


async def create_stave(
    name: str,
    data_source_type: str,
    connection_config: dict[str, object],
    description: str | None = None,
    is_active: bool = True,
) -> dict[str, object]:
    """Create a new data source (stave) in DataMetronome.

    Args:
        name: Human-readable name for the data source (e.g., "Production Database")
        data_source_type: Type of data source. Supported: postgres, mysql, mongodb, sqlite, redis, snowflake, bigquery
        connection_config: Connection parameters as a dictionary. For postgres: {"host": "localhost", "port": 5432, "database": "mydb", "user": "user", "password": "pass"}
        description: Optional description of the data source
        is_active: Whether this data source should be actively monitored (default: True)

    Returns:
        Dictionary with the created stave data including its ID
    """
    try:
        import json
        import uuid
        from datetime import datetime, timezone

        from datametronome_podium.services.stave_service import deserialize_stave

        executor = get_executor()

        stave_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat() + "Z"

        await executor.insert("staves", {
            "id": stave_id,
            "name": name,
            "description": description,
            "data_source_type": data_source_type,
            "connection_config": json.dumps(connection_config),
            "is_active": is_active,
            "created_at": now,
            "updated_at": now,
        })

        staves = await executor.query(
            "SELECT * FROM staves WHERE id = ?", [stave_id]
        )
        if not staves:
            return {"error": "Stave created but could not be retrieved"}

        deserialized = deserialize_stave(staves[0])
        stave_dict = deserialized.model_dump()
        if isinstance(stave_dict.get("created_at"), datetime):
            stave_dict["created_at"] = stave_dict["created_at"].isoformat()
        if isinstance(stave_dict.get("updated_at"), datetime):
            stave_dict["updated_at"] = stave_dict["updated_at"].isoformat()

        return stave_dict
    except Exception as e:
        logger.error("Error creating stave: %s", e, exc_info=True)
        return {"error": f"Failed to create stave: {str(e)}"}


async def list_stave_tables(
    stave_id: str, include_structure: bool = True
) -> dict[str, object]:
    """List all tables in a specific data source (stave) by ID.

    This tool allows you to see what tables are available in a datasource,
    and optionally get their structure (columns, data types, etc.).

    Args:
        stave_id: The ID of the stave (data source) to query
        include_structure: Whether to include table structure/schema information (default: True)

    Returns:
        Dictionary with tables list, count, and stave information
    """
    connector = None
    try:
        from datametronome_podium.services.connection_tester import ConnectionTester
        from datametronome_podium.services.stave_service import deserialize_stave

        executor = get_executor()
        staves = await executor.query(
            "SELECT * FROM staves WHERE id = ?", [stave_id]
        )

        if not staves:
            return {"error": f"Stave not found: {stave_id}"}

        stave = deserialize_stave(staves[0])

        tester = ConnectionTester()
        connector = await tester.get_connector(stave, read_only=True)

        if not hasattr(connector, "list_tables"):
            return {
                "error": f"list_tables not available for {stave.data_source_type} connector"
            }

        if stave.data_source_type == "bigquery":
            dataset = stave.connection_config.get("dataset")
            table_names = await connector.list_tables(dataset)
        elif stave.data_source_type in ["postgres", "postgresql"]:
            schema = stave.connection_config.get("schema", "public")
            table_names = await connector.list_tables(schema)
        else:
            table_names = await connector.list_tables()

        tables = []
        for table_name in table_names:
            table_info = {"name": table_name}
            if include_structure:
                try:
                    if hasattr(connector, "get_table_info"):
                        structure = await connector.get_table_info(table_name)
                        table_info["structure"] = structure
                except Exception as e:
                    logger.warning("Could not get structure for table %s: %s", table_name, e)
                    table_info["structure"] = None
            tables.append(table_info)

        return {
            "success": True,
            "stave_id": stave_id,
            "stave_name": stave.name,
            "data_source_type": stave.data_source_type,
            "count": len(tables),
            "tables": tables,
        }
    except Exception as e:
        logger.error("Error listing tables for stave %s: %s", stave_id, e, exc_info=True)
        return {"error": f"Failed to list tables: {str(e)}"}
    finally:
        if connector:
            try:
                await connector.close()
            except Exception:
                pass


async def get_table_sample(
    stave_id: str, table_name: str, limit: int = 100
) -> dict[str, object]:
    """Get a sample of data from a specific table.

    This tool retrieves a sample of rows from a table to help analyze
    data patterns, identify important fields, and understand data characteristics.

    Args:
        stave_id: The ID of the stave (data source) containing the table
        table_name: Name of the table to sample
        limit: Number of rows to sample (default: 100, max recommended: 1000)

    Returns:
        Dictionary with sample data, column information, and data analysis
    """
    connector = None
    try:
        from datametronome_podium.services.connection_tester import ConnectionTester
        from datametronome_podium.services.stave_service import deserialize_stave

        executor = get_executor()
        staves = await executor.query(
            "SELECT * FROM staves WHERE id = ?", [stave_id]
        )

        if not staves:
            return {"error": f"Stave not found: {stave_id}"}

        stave = deserialize_stave(staves[0])

        tester = ConnectionTester()
        connector = await tester.get_connector(stave, read_only=True)

        config = stave.connection_config if isinstance(stave.connection_config, dict) else {}
        if stave.data_source_type == "bigquery":
            # BigQuery uses backtick quoting; escape backticks in the identifier
            safe_table = table_name.replace("`", "")
            query = f"SELECT * FROM `{safe_table}` LIMIT {limit}"
        elif stave.data_source_type in ["postgres", "postgresql"]:
            pg_schema = config.get("schema", "public")
            query = (
                f"SELECT * FROM {_quote_identifier(pg_schema)}.{_quote_identifier(table_name)}"
                f" LIMIT {limit}"
            )
        else:
            query = f"SELECT * FROM {_quote_identifier(table_name)} LIMIT {limit}"

        sample_data = await connector.query({"sql": query})

        if not sample_data:
            return {
                "success": True,
                "stave_id": stave_id,
                "table_name": table_name,
                "row_count": 0,
                "sample_data": [],
                "columns": [],
                "analysis": {
                    "message": "Table is empty or query returned no results",
                    "important_fields": [],
                },
            }

        analysis = _analyze_sample_data(sample_data)

        return {
            "success": True,
            "stave_id": stave_id,
            "stave_name": stave.name,
            "data_source_type": stave.data_source_type,
            "table_name": table_name,
            "row_count": len(sample_data),
            "limit": limit,
            "columns": list(sample_data[0].keys()) if sample_data else [],
            "sample_data": sample_data[:10],
            "analysis": analysis,
        }
    except Exception as e:
        logger.error(
            "Error getting sample data from table %s in stave %s: %s",
            table_name, stave_id, e, exc_info=True,
        )
        return {"error": f"Failed to get sample data: {str(e)}"}
    finally:
        if connector:
            try:
                await connector.close()
            except Exception:
                pass


async def suggest_quality_checks(
    stave_id: str,
    table_name: str | None = None,
    use_sample_data: bool = True,
    sample_limit: int = 100,
) -> dict[str, object]:
    """Suggest quality checks based on table structure and optionally sample data.

    This tool analyzes the schema of tables in a data source and suggests
    appropriate quality checks based on column names, data types, nullable
    constraints, and optionally actual data samples to identify patterns.

    Args:
        stave_id: The ID of the stave (data source) to analyze
        table_name: Optional specific table name. If not provided, suggests
                   checks for all tables in the stave.
        use_sample_data: Whether to analyze sample data for better suggestions
                       (default: True).
        sample_limit: Number of rows to sample when use_sample_data is True
                    (default: 100)

    Returns:
        Dictionary with suggested quality checks for each table analyzed
    """
    connector = None
    try:
        from datametronome_podium.services.connection_tester import ConnectionTester
        from datametronome_podium.services.stave_service import deserialize_stave

        executor = get_executor()
        staves = await executor.query(
            "SELECT * FROM staves WHERE id = ?", [stave_id]
        )

        if not staves:
            return {"error": f"Stave not found: {stave_id}"}

        stave = deserialize_stave(staves[0])

        tester = ConnectionTester()
        connector = await tester.get_connector(stave, read_only=True)

        if table_name:
            tables_to_analyze = [table_name]
        else:
            if not hasattr(connector, "list_tables"):
                return {
                    "error": f"list_tables not available for {stave.data_source_type} connector"
                }

            if stave.data_source_type == "bigquery":
                dataset = stave.connection_config.get("dataset")
                tables_to_analyze = await connector.list_tables(dataset)
            elif stave.data_source_type in ["postgres", "postgresql"]:
                schema = stave.connection_config.get("schema", "public")
                tables_to_analyze = await connector.list_tables(schema)
            else:
                tables_to_analyze = await connector.list_tables()

        suggestions = []

        for tbl_name in tables_to_analyze:
            try:
                if not hasattr(connector, "get_table_info"):
                    continue

                table_info = await connector.get_table_info(tbl_name)

                if isinstance(table_info, dict):
                    columns = table_info.get("columns", [])
                elif isinstance(table_info, list):
                    columns = table_info
                else:
                    continue

                if not columns:
                    continue

                sample_analysis = None
                if use_sample_data:
                    try:
                        if stave.data_source_type == "bigquery":
                            dataset = stave.connection_config.get("dataset")
                            if dataset:
                                if "." in dataset:
                                    qualified_table = f"`{dataset}.{tbl_name}`"
                                else:
                                    project_id = stave.connection_config.get("project_id")
                                    if project_id:
                                        qualified_table = f"`{project_id}.{dataset}.{tbl_name}`"
                                    else:
                                        qualified_table = f"`{dataset}.{tbl_name}`"
                            else:
                                qualified_table = f"`{tbl_name}`"
                            query = f"SELECT * FROM {qualified_table} LIMIT {sample_limit}"
                        elif stave.data_source_type in ["postgres", "postgresql"]:
                            query = f'SELECT * FROM "{tbl_name}" LIMIT {sample_limit}'
                        else:
                            query = f"SELECT * FROM {tbl_name} LIMIT {sample_limit}"

                        sample_data = await connector.query({"sql": query})
                        if sample_data:
                            sample_analysis = _analyze_sample_data(sample_data)
                    except Exception as e:
                        logger.warning("Could not get sample data for table %s: %s", tbl_name, e)
                        sample_analysis = None

                table_suggestions = _analyze_table_structure(
                    tbl_name, columns, stave.data_source_type
                )

                if sample_analysis and sample_analysis.get("important_fields"):
                    table_suggestions = _enhance_suggestions_with_data(
                        table_suggestions, sample_analysis, tbl_name
                    )

                if table_suggestions:
                    reasoning = f"Analyzed {len(columns)} columns"
                    if sample_analysis:
                        reasoning += f" and {sample_analysis.get('message', 'sample data')}"
                    reasoning += f" - suggested {len(table_suggestions)} quality checks"

                    suggestions.append(
                        {
                            "table": tbl_name,
                            "suggested_clefs": table_suggestions,
                            "reasoning": reasoning,
                            "data_analysis_used": sample_analysis is not None,
                            "important_fields": sample_analysis.get("important_fields", [])[:5]
                            if sample_analysis
                            else [],
                        }
                    )
            except Exception as e:
                logger.warning("Could not analyze table %s: %s", tbl_name, e)
                continue

        return {
            "success": True,
            "stave_id": stave_id,
            "stave_name": stave.name,
            "data_source_type": stave.data_source_type,
            "tables_analyzed": len(suggestions),
            "suggestions": suggestions,
        }
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(
            "Error suggesting quality checks for stave %s: %s: %s",
            stave_id, error_type, error_msg, exc_info=True,
        )
        if "credentials" in error_msg.lower() or "authentication" in error_msg.lower():
            return {
                "error": f"Authentication error: {error_msg}. "
                "Please verify the stave's connection configuration has valid credentials."
            }
        return {"error": f"Failed to suggest quality checks ({error_type}): {error_msg}"}
    finally:
        if connector:
            try:
                await connector.close()
            except Exception:
                pass


async def list_clefs(
    limit: int = 100,
    skip: int = 0,
    stave_id: str | None = None,
    active_only: bool = False,
) -> dict[str, object]:
    """List all data quality checks (clefs) in DataMetronome.

    Args:
        limit: Maximum number of clefs to return (default: 100)
        skip: Number of clefs to skip for pagination (default: 0)
        stave_id: If provided, only return clefs for this stave
        active_only: If True, return only active clefs (is_active=True). Default: False (all clefs)
    """
    try:
        from datetime import datetime

        from datametronome_podium.services.stave_service import deserialize_clef

        executor = get_executor()

        if stave_id and active_only:
            clefs = await executor.query(
                "SELECT * FROM clefs WHERE stave_id = ? AND is_active = TRUE ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [stave_id, limit, skip],
            )
        elif stave_id:
            clefs = await executor.query(
                "SELECT * FROM clefs WHERE stave_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [stave_id, limit, skip],
            )
        elif active_only:
            clefs = await executor.query(
                "SELECT * FROM clefs WHERE is_active = TRUE ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [limit, skip],
            )
        else:
            clefs = await executor.query(
                "SELECT * FROM clefs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [limit, skip],
            )

        clefs_list = []
        for clef in clefs:
            try:
                deserialized = deserialize_clef(clef)
                clef_dict = deserialized.model_dump()
                if isinstance(clef_dict.get("created_at"), datetime):
                    clef_dict["created_at"] = clef_dict["created_at"].isoformat()
                if isinstance(clef_dict.get("updated_at"), datetime):
                    clef_dict["updated_at"] = clef_dict["updated_at"].isoformat()
                clefs_list.append(clef_dict)
            except Exception as e:
                logger.warning("Failed to deserialize clef %s: %s", clef.get('id', 'unknown'), e)
                continue

        return {"clefs": clefs_list, "count": len(clefs_list)}
    except Exception as e:
        logger.error("Error listing clefs: %s", e, exc_info=True)
        return {"error": f"Failed to list clefs: {str(e)}", "clefs": []}


async def get_clef(clef_id: str) -> dict[str, object]:
    """Get details about a specific quality check (clef) by ID."""
    try:
        from datetime import datetime

        from datametronome_podium.services.stave_service import deserialize_clef

        executor = get_executor()
        clefs = await executor.query(
            "SELECT * FROM clefs WHERE id = ?", [clef_id]
        )

        if not clefs:
            return {"error": f"Clef not found: {clef_id}"}

        deserialized = deserialize_clef(clefs[0])
        clef_dict = deserialized.model_dump()
        if isinstance(clef_dict.get("created_at"), datetime):
            clef_dict["created_at"] = clef_dict["created_at"].isoformat()
        if isinstance(clef_dict.get("updated_at"), datetime):
            clef_dict["updated_at"] = clef_dict["updated_at"].isoformat()

        return clef_dict
    except Exception as e:
        logger.error("Error getting clef %s: %s", clef_id, e, exc_info=True)
        return {"error": f"Failed to get clef: {str(e)}"}


async def list_checks(
    limit: int = 20,
    status: str | None = None,
    stave_id: str | None = None,
    clef_id: str | None = None,
) -> dict[str, object]:
    """List check execution results."""
    try:

        executor = get_executor()

        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if stave_id:
            conditions.append("stave_id = ?")
            params.append(stave_id)
        if clef_id:
            conditions.append("clef_id = ?")
            params.append(clef_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit])

        checks = await executor.query(
            f"SELECT * FROM checks WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?",
            params,
        )

        return {"checks": checks}
    except Exception as e:
        logger.error("Error listing checks: %s", e, exc_info=True)
        return {"error": f"Failed to list checks: {str(e)}", "checks": []}


async def get_summary_report(days: int = 7) -> dict[str, object]:
    """Get a summary report of DataMetronome system status.

    Args:
        days: Number of days to look back for recent activity. Defaults to 7.
    """
    try:
        from datetime import datetime, timedelta, timezone


        executor = get_executor()

        staves_count = await executor.query(
            "SELECT COUNT(*) as count FROM staves WHERE is_active = TRUE", []
        )
        total_staves = staves_count[0]["count"] if staves_count else 0

        clefs_count = await executor.query(
            "SELECT COUNT(*) as count FROM clefs WHERE is_active = TRUE", []
        )
        total_clefs = clefs_count[0]["count"] if clefs_count else 0

        checks_count = await executor.query(
            "SELECT COUNT(*) as count FROM checks", []
        )
        total_checks = checks_count[0]["count"] if checks_count else 0

        threshold_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        recent_checks = await executor.query(
            "SELECT * FROM checks WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 5",
            [threshold_date],
        )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "summary": {
                "total_staves": total_staves,
                "total_clefs": total_clefs,
                "total_checks": total_checks,
            },
            "recent_activity": recent_checks,
        }
    except Exception as e:
        logger.error("Error generating summary report: %s", e, exc_info=True)
        return {"error": f"Failed to generate summary report: {str(e)}"}


async def get_quality_report(days: int = 7) -> dict[str, object]:
    """Get a quality report showing data quality metrics."""
    try:
        from datetime import datetime, timedelta, timezone


        executor = get_executor()

        threshold_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        period_checks = await executor.query(
            "SELECT * FROM checks WHERE timestamp >= ? ORDER BY timestamp DESC",
            [threshold_date],
        )

        total_checks = len(period_checks)
        passed_checks = sum(
            1 for check in period_checks if check["status"] == "passed"
        )
        failed_checks = total_checks - passed_checks

        quality_score = (
            (passed_checks / total_checks * 100) if total_checks > 0 else 100.0
        )

        anomalies = await executor.query(
            "SELECT * FROM anomalies WHERE detected_at >= ? ORDER BY detected_at DESC",
            [threshold_date],
        )

        return {
            "period_days": days,
            "quality_score": round(quality_score, 1),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "total_anomalies": len(anomalies),
            "anomalies_by_severity": {
                "low": sum(1 for a in anomalies if a["severity"] == "low"),
                "medium": sum(1 for a in anomalies if a["severity"] == "medium"),
                "high": sum(1 for a in anomalies if a["severity"] == "high"),
                "critical": sum(1 for a in anomalies if a["severity"] == "critical"),
            },
        }
    except Exception as e:
        logger.error("Error generating quality report: %s", e, exc_info=True)
        return {"error": f"Failed to generate quality report: {str(e)}"}


# ---------------------------------------------------------------------------
# Private helpers (used internally by suggest_quality_checks + get_table_sample)
# ---------------------------------------------------------------------------


def _analyze_sample_data(sample_data: list[dict]) -> dict:
    """Analyze sample data to identify important fields and patterns."""
    if not sample_data:
        return {"message": "No data to analyze", "important_fields": [], "patterns": {}}

    important_fields = []
    patterns = {}
    field_stats = {}

    columns = list(sample_data[0].keys()) if sample_data else []

    for col in columns:
        col_values = [row.get(col) for row in sample_data if col in row]
        non_null_values = [v for v in col_values if v is not None]
        null_count = len(col_values) - len(non_null_values)
        null_percentage = (null_count / len(col_values) * 100) if col_values else 0

        stats = {
            "total_values": len(col_values),
            "non_null_count": len(non_null_values),
            "null_count": null_count,
            "null_percentage": round(null_percentage, 2),
            "unique_count": len(set(non_null_values)) if non_null_values else 0,
        }

        importance_score = 0
        importance_reasons = []

        if (
            stats["unique_count"] == stats["non_null_count"]
            and stats["non_null_count"] > 0
        ):
            importance_score += 10
            importance_reasons.append("All values are unique (potential key)")

        if null_percentage < 5:
            importance_score += 5
            importance_reasons.append("Very few NULL values")

        if null_percentage > 50:
            importance_score += 3
            importance_reasons.append("High NULL percentage (data quality concern)")

        if non_null_values:
            unique_ratio = stats["unique_count"] / stats["non_null_count"]
            if unique_ratio < 0.1 and stats["non_null_count"] > 10:
                unique_values = list(set(non_null_values))[:20]
                patterns[col] = {
                    "type": "enum_like",
                    "unique_values": unique_values,
                    "unique_count": stats["unique_count"],
                }
                importance_score += 4
                importance_reasons.append("Appears to be an enum/category field")

        numeric_values = []
        for v in non_null_values:
            try:
                if isinstance(v, (int, float)):
                    numeric_values.append(float(v))
                elif isinstance(v, str) and v.replace(".", "").replace("-", "").isdigit():
                    numeric_values.append(float(v))
            except (ValueError, TypeError):
                pass

        if numeric_values:
            stats["is_numeric"] = True
            stats["min"] = min(numeric_values)
            stats["max"] = max(numeric_values)
            stats["avg"] = sum(numeric_values) / len(numeric_values)
            stats["numeric_count"] = len(numeric_values)

            if stats["min"] >= 0 and stats["max"] <= 100 and "percent" in col.lower():
                importance_score += 3
                importance_reasons.append("Numeric field with percentage-like range")

        timestamp_indicators = ["created", "updated", "modified", "date", "time", "at"]
        if any(indicator in col.lower() for indicator in timestamp_indicators):
            importance_score += 6
            importance_reasons.append("Appears to be a timestamp field")

        id_indicators = ["id", "uuid", "key", "pk"]
        if any(indicator in col.lower() for indicator in id_indicators):
            importance_score += 7
            importance_reasons.append("Appears to be an ID/key field")

        if "email" in col.lower() and non_null_values:
            email_like = sum(
                1
                for v in non_null_values[:10]
                if isinstance(v, str) and "@" in v and "." in v
            )
            if email_like > 0:
                importance_score += 5
                importance_reasons.append("Contains email-like values")

        field_stats[col] = stats

        if importance_score >= 5:
            important_fields.append(
                {
                    "field": col,
                    "importance_score": importance_score,
                    "reasons": importance_reasons,
                    "stats": stats,
                }
            )

    important_fields.sort(key=lambda x: x["importance_score"], reverse=True)

    return {
        "message": f"Analyzed {len(sample_data)} rows and {len(columns)} columns",
        "important_fields": important_fields[:10],
        "patterns": patterns,
        "field_stats": {k: v for k, v in list(field_stats.items())[:20]},
    }


def _analyze_table_structure(
    table_name: str, columns: list[dict], data_source_type: str
) -> list[dict]:
    """Analyze table structure and generate quality check suggestions."""
    suggestions = []

    timestamp_patterns = [
        "timestamp", "created_at", "updated_at", "modified_at",
        "date", "time", "_at", "_date", "_time",
    ]
    id_patterns = ["id", "_id", "uuid", "key", "pk"]
    email_patterns = ["email", "e_mail", "email_address"]
    numeric_patterns = [
        "amount", "price", "cost", "quantity", "count",
        "age", "score", "rating", "percent", "percentage",
    ]

    has_timestamp = False

    for col in columns:
        col_name = col.get("column_name", "").lower()
        data_type = str(col.get("data_type", "")).lower()
        is_nullable = col.get("is_nullable", "YES").upper() == "YES"

        is_numeric = any(
            dt in data_type
            for dt in ["int", "numeric", "decimal", "float", "double", "real", "number"]
        )
        is_string = any(
            dt in data_type for dt in ["varchar", "char", "text", "string", "str"]
        )
        is_timestamp = any(
            dt in data_type for dt in ["timestamp", "datetime", "date", "time"]
        )

        if not suggestions:
            suggestions.append(
                {
                    "name": f"{table_name} Row Count Check",
                    "description": f"Monitor row count for {table_name} table",
                    "check_type": "row_count",
                    "config": {"table": table_name},
                    "warn": "< 100",
                    "fail": "< 10",
                    "schedule": "@daily",
                    "priority": "high",
                    "reasoning": "Basic volume check to ensure table has data",
                }
            )

        if is_timestamp or any(pattern in col_name for pattern in timestamp_patterns):
            has_timestamp = True
            suggestions.append(
                {
                    "name": f"{table_name}.{col.get('column_name')} Freshness Check",
                    "description": f"Ensure {col.get('column_name')} is recent",
                    "check_type": "freshness",
                    "config": {
                        "table": table_name,
                        "timestamp_column": col.get("column_name"),
                    },
                    "warn": "> 24 hours",
                    "fail": "> 48 hours",
                    "schedule": "@hourly",
                    "priority": "high",
                    "reasoning": f"Column '{col.get('column_name')}' appears to be a timestamp column",
                }
            )

        is_id_like = (
            col_name == "id"
            or col_name.endswith("_id")
            or col_name in ["uuid", "key", "pk", "primary_key"]
        )

        if is_id_like:
            suggestions.append(
                {
                    "name": f"{table_name}.{col.get('column_name')} Uniqueness Check",
                    "description": f"Ensure {col.get('column_name')} values are unique",
                    "check_type": "column_values",
                    "config": {
                        "table": table_name,
                        "column": col.get("column_name"),
                    },
                    "fail": "if_not_unique > 0",
                    "schedule": "@daily",
                    "priority": "high",
                    "reasoning": f"Column '{col.get('column_name')}' appears to be an ID/primary key column",
                }
            )

        if any(pattern in col_name for pattern in email_patterns):
            suggestions.append(
                {
                    "name": f"{table_name}.{col.get('column_name')} Email Format Check",
                    "description": f"Validate email format for {col.get('column_name')}",
                    "check_type": "column_values",
                    "config": {
                        "table": table_name,
                        "column": col.get("column_name"),
                        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    },
                    "warn": "if_not_matching_pattern > 5%",
                    "fail": "if_not_matching_pattern > 10%",
                    "schedule": "@daily",
                    "priority": "medium",
                    "reasoning": f"Column '{col.get('column_name')}' appears to contain email addresses",
                }
            )

        if is_nullable and not any(pattern in col_name for pattern in id_patterns):
            if any(
                pattern in col_name
                for pattern in email_patterns + numeric_patterns + ["name", "status"]
            ):
                suggestions.append(
                    {
                        "name": f"{table_name}.{col.get('column_name')} NULL Check",
                        "description": f"Monitor NULL values in {col.get('column_name')}",
                        "check_type": "column_values",
                        "config": {
                            "table": table_name,
                            "column": col.get("column_name"),
                        },
                        "warn": "if_null > 5%",
                        "fail": "if_null > 10%",
                        "schedule": "@daily",
                        "priority": "medium",
                        "reasoning": f"Column '{col.get('column_name')}' is nullable and appears important",
                    }
                )

        if is_numeric and any(pattern in col_name for pattern in numeric_patterns):
            min_val = 0
            max_val = None

            if "age" in col_name:
                max_val = 150
            elif "percent" in col_name or "percentage" in col_name:
                max_val = 100
            elif "rating" in col_name or "score" in col_name:
                max_val = 10

            if max_val is not None:
                suggestions.append(
                    {
                        "name": f"{table_name}.{col.get('column_name')} Range Check",
                        "description": f"Validate {col.get('column_name')} is within expected range",
                        "check_type": "column_values",
                        "config": {
                            "table": table_name,
                            "column": col.get("column_name"),
                            "min": min_val,
                            "max": max_val,
                        },
                        "warn": "if_out_of_range > 1%",
                        "fail": "if_out_of_range > 5%",
                        "schedule": "@daily",
                        "priority": "medium",
                        "reasoning": f"Column '{col.get('column_name')}' is numeric and suggests a bounded range",
                    }
                )

        if is_string and col_name in ["status", "state", "type", "category"]:
            suggestions.append(
                {
                    "name": f"{table_name}.{col.get('column_name')} Values Check",
                    "description": f"Monitor allowed values for {col.get('column_name')}",
                    "check_type": "column_values",
                    "config": {
                        "table": table_name,
                        "column": col.get("column_name"),
                    },
                    "warn": "if_not_in: [] > 1%",
                    "fail": "if_not_in: [] > 5%",
                    "schedule": "@daily",
                    "priority": "low",
                    "reasoning": f"Column '{col.get('column_name')}' appears to be an enum/category column.",
                    "note": "You may need to update the config with actual allowed_values after reviewing the data",
                }
            )

    if not has_timestamp:
        for col in columns:
            col_name = col.get("column_name", "").lower()
            if any(
                word in col_name
                for word in ["date", "time", "created", "updated", "modified"]
            ):
                suggestions.append(
                    {
                        "name": f"{table_name} Data Freshness Check",
                        "description": f"Monitor data freshness for {table_name}",
                        "check_type": "freshness",
                        "config": {
                            "table": table_name,
                            "timestamp_column": col.get("column_name"),
                        },
                        "warn": "> 24 hours",
                        "fail": "> 48 hours",
                        "schedule": "@hourly",
                        "priority": "medium",
                        "reasoning": f"Found potential timestamp column '{col.get('column_name')}'",
                    }
                )
                break

    return suggestions


def _enhance_suggestions_with_data(
    schema_suggestions: list[dict],
    data_analysis: dict,
    table_name: str,
) -> list[dict]:
    """Enhance schema-based suggestions with insights from actual data analysis."""
    enhanced = list(schema_suggestions)
    important_fields = data_analysis.get("important_fields", [])
    patterns = data_analysis.get("patterns", {})
    field_stats = data_analysis.get("field_stats", {})

    columns_with_suggestions = set()
    for sug in schema_suggestions:
        config = sug.get("config", {})
        if "column" in config:
            columns_with_suggestions.add(config["column"])

    for field_info in important_fields:
        field_name = field_info["field"]
        if field_name in columns_with_suggestions:
            continue

        importance_score = field_info.get("importance_score", 0)
        stats = field_info.get("stats", {})

        if importance_score >= 8:
            if field_name in patterns:
                pattern_info = patterns[field_name]
                if pattern_info.get("type") == "enum_like":
                    allowed_values = pattern_info.get("unique_values", [])
                    enhanced.append(
                        {
                            "name": f"{table_name}.{field_name} Allowed Values Check",
                            "description": f"Validate {field_name} contains only expected values",
                            "check_type": "column_values",
                            "config": {
                                "table": table_name,
                                "column": field_name,
                                "allowed_values": allowed_values[:50],
                            },
                            "warn": "if_not_in: [] > 1%",
                            "fail": "if_not_in: [] > 5%",
                            "schedule": "@daily",
                            "priority": "high",
                            "reasoning": f"Data analysis shows this field has {pattern_info.get('unique_count')} distinct values (enum-like pattern).",
                        }
                    )

            elif (
                stats.get("is_numeric")
                and stats.get("min") is not None
                and stats.get("max") is not None
            ):
                min_val = stats.get("min", 0)
                max_val = stats.get("max", 100)
                if max_val - min_val < 10000:
                    enhanced.append(
                        {
                            "name": f"{table_name}.{field_name} Range Check",
                            "description": f"Validate {field_name} is within observed data range",
                            "check_type": "column_values",
                            "config": {
                                "table": table_name,
                                "column": field_name,
                                "min": min_val,
                                "max": max_val,
                            },
                            "warn": "if_out_of_range > 1%",
                            "fail": "if_out_of_range > 5%",
                            "schedule": "@daily",
                            "priority": "high",
                            "reasoning": f"Data analysis shows values range from {min_val} to {max_val}.",
                        }
                    )

        if (
            stats.get("null_percentage", 0) > 0
            and stats.get("null_percentage", 0) < 50
        ):
            if importance_score >= 6:
                enhanced.append(
                    {
                        "name": f"{table_name}.{field_name} NULL Check",
                        "description": f"Monitor NULL values in {field_name}",
                        "check_type": "column_values",
                        "config": {"table": table_name, "column": field_name},
                        "warn": f"if_null > {min(10, stats.get('null_percentage', 5) + 2)}%",
                        "fail": f"if_null > {min(20, stats.get('null_percentage', 10) + 5)}%",
                        "schedule": "@daily",
                        "priority": "medium",
                        "reasoning": f"Data analysis shows {stats.get('null_percentage', 0):.1f}% NULL values.",
                    }
                )

    def get_priority(sug):
        priority_map = {"high": 3, "medium": 2, "low": 1}
        return priority_map.get(sug.get("priority", "medium"), 2)

    enhanced.sort(key=get_priority, reverse=True)

    return enhanced


# ---------------------------------------------------------------------------
# Intelligence-specific tools
# ---------------------------------------------------------------------------


async def get_stave_intelligence(stave_id: str) -> dict[str, object]:
    """Get the intelligence profile and latest report for a data source.

    Returns the domain classification, health score, anomalies, suggestions,
    and accumulated knowledge for a stave.
    """
    try:
        from datametronome_podium.core.database import get_executor
        from datametronome_podium.features.insights.repo import InsightsRepo

        repo = InsightsRepo(get_executor())

        profile = await repo.get_profile(stave_id)
        report = await repo.get_latest_report(stave_id)
        suggestions = await repo.list_suggestions(stave_id, status="pending")

        logger.info(
            "get_stave_intelligence(%s): profile=%s, report=%s, suggestions=%d",
            stave_id,
            profile.domain_type if profile else None,
            report.health_score if report else None,
            len(suggestions) if suggestions else 0,
        )

        result: dict[str, object] = {"stave_id": stave_id}

        if profile:
            result["domain_type"] = profile.domain_type
            result["domain_confidence"] = profile.domain_confidence
            result["domain_context"] = profile.domain_context
            result["entity_roles"] = profile.entity_roles
            result["learned_patterns"] = profile.learned_patterns
        else:
            result["profile"] = None
            result["message"] = "No intelligence profile yet. Trigger an analysis first."

        if report:
            result["health_score"] = report.health_score
            result["report_type"] = report.report_type
            result["summary"] = report.summary
            result["key_findings"] = report.key_findings
            result["anomalies"] = report.anomalies
            result["dimensions"] = report.dimensions
            result["last_analyzed"] = report.created_at

        if suggestions:
            result["pending_suggestions"] = [
                {"action": s.action, "priority": s.priority, "reasoning": s.reasoning}
                for s in suggestions
            ]

        return result
    except Exception as e:
        return {"error": str(e), "stave_id": stave_id}


async def trigger_stave_analysis(stave_id: str) -> dict[str, object]:
    """Trigger an on-demand intelligence analysis for a data source.

    Dispatches a background analysis that discovers schema, classifies
    the business domain, captures metrics, and generates an AI insight report.
    Returns immediately with a task ID for status polling.
    """
    try:
        from datametronome_podium.tasks.intelligence_tasks import run_on_demand_analysis

        task = run_on_demand_analysis.delay(stave_id)
        return {
            "status": "queued",
            "task_id": task.id,
            "stave_id": stave_id,
            "message": (
                f"Analysis queued for stave {stave_id}. "
                "Results will be available via get_stave_intelligence once complete."
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Could not dispatch analysis. The Celery worker may not be running.",
        }


# ---------------------------------------------------------------------------
# Exported tool lists (used by sub-agents to register tools)
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    list_staves,
    get_stave,
    create_stave,
    list_stave_tables,
    get_table_sample,
    suggest_quality_checks,
    list_clefs,
    get_clef,
    list_checks,
    get_summary_report,
    get_quality_report,
    get_stave_intelligence,
    trigger_stave_analysis,
]

INSIGHT_TOOLS = [
    list_staves,
    get_stave,
    list_stave_tables,
    get_table_sample,
    suggest_quality_checks,
    list_clefs,
    list_checks,
    get_stave_intelligence,
    trigger_stave_analysis,
]
