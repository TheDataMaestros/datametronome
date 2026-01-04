"""
ADK Agent Service for DataMetronome.

This service integrates with Google's Agent Development Kit (ADK) to provide
an AI assistant that can query and interact with the DataMetronome API.
Supports both Ollama (via LiteLLM) and Gemini models.
"""

import json
import logging
import re
import uuid

from datametronome_podium.core.config import settings

logger = logging.getLogger(__name__)

# HTTP client timeout settings (in seconds)
HTTP_TIMEOUT = 180.0  # 3 minutes for agent operations
HTTP_TIMEOUT_SHORT = 180.0  # Same for tool calls

# Try to import Google ADK - if not available, fall back to HTTP-based approach
try:
    from google.adk import Agent
    from google.adk.models.lite_llm import LiteLlm

    # Try to import context/input classes if available
    try:
        from google.adk import InvocationContext  # type: ignore[attr-defined]

        INVOCATION_CONTEXT_AVAILABLE = True
    except ImportError:
        INVOCATION_CONTEXT_AVAILABLE = False
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    INVOCATION_CONTEXT_AVAILABLE = False
    logger.warning(
        "Google ADK not available. Install with: pip install google-adk. "
        "Falling back to HTTP-based agent."
    )


class ADKAgent:
    """ADK Agent that can query DataMetronome API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_url: str | None = None,
    ):
        """Initialize the ADK agent.

        Args:
            model: Model identifier (e.g., 'ollama_chat/qwen2.5' for Ollama)
            api_key: API key (not needed for Ollama, required for Gemini)
            api_url: API endpoint URL (not used for Ollama)
        """
        self.model_name = model or settings.adk_model
        self.api_key = api_key or settings.adk_api_key
        self.api_url = api_url or settings.adk_api_url

        # If we have an API key and using a Gemini model, ensure we use the explicit 'gemini/' provider
        # prefix to force using Google AI Studio (API Key) instead of Vertex AI (ADC).
        # Without this, litellm might default to Vertex AI for some model names, causing auth errors
        # if ADC is not set up.
        if (
            self.api_key
            and self.model_name.lower().startswith("gemini")
            and not self.model_name.lower().startswith("gemini/")
        ):
            logger.info(
                f"ℹ️  Auto-prefixing model '{self.model_name}' with 'gemini/' to use AI Studio provider"
            )
            self.model_name = f"gemini/{self.model_name}"

        # Use internal API URL - use the same port as the running server
        import os

        # Get port from environment (PODIUM_PORT is used in start script and takes precedence)
        # Priority: PODIUM_PORT > DATAMETRONOME_PORT > settings.port
        # This ensures we use the same port the server is actually running on
        api_port = (
            os.getenv("PODIUM_PORT")
            or os.getenv("DATAMETRONOME_PORT")
            or str(settings.port)
        )
        api_port = int(api_port)  # Ensure it's an integer

        self.api_base_url = os.getenv(
            "DATAMETRONOME_INTERNAL_API_URL", f"http://127.0.0.1:{api_port}/api/v1"
        )
        logger.info(
            f"🔗 ADK Agent API base URL: {self.api_base_url} (using port {api_port}, PODIUM_PORT={os.getenv('PODIUM_PORT')}, DATAMETRONOME_PORT={os.getenv('DATAMETRONOME_PORT')}, settings.port={settings.port})"
        )

        # Initialize ADK agent if available
        self.agent = None
        if ADK_AVAILABLE:
            try:
                # Configure LiteLLM environment variables (LiteLLM requires env vars, not constructor params)
                self._configure_litellm_environment()

                # Create LiteLLM model - it will read from environment variables we just set
                model_obj = LiteLlm(model=self.model_name)

                # Create the root agent with tools
                # ADK Agent accepts 'instruction' (singular) for system instructions
                self.agent = Agent(
                    model=model_obj,
                    name="datametronome_assistant",
                    description="AI assistant for DataMetronome data quality platform. "
                    "Helps users understand their data quality status, configure checks, "
                    "and troubleshoot issues.",
                    instruction=self._get_system_instructions(),
                    tools=self._get_adk_tools(),
                )
                logger.info(f"✅ ADK Agent initialized with model: {self.model_name}")
                # Log available methods for debugging
                available_methods = [
                    m
                    for m in dir(self.agent)
                    if not m.startswith("_") and callable(getattr(self.agent, m, None))
                ]
                logger.debug(f"ADK Agent available methods: {available_methods}")
            except Exception as e:
                logger.error(f"Failed to initialize ADK agent: {e}", exc_info=True)
                self.agent = None

    def _configure_litellm_environment(self) -> None:
        """Configure LiteLLM by setting required environment variables.

        Note: LiteLLM reads configuration from environment variables (OLLAMA_API_BASE,
        GEMINI_API_KEY, etc.) rather than accepting them as constructor parameters.
        This method ensures the necessary environment variables are set from our
        configuration system before LiteLLM is initialized.

        This is a limitation of the LiteLLM library - we would prefer to pass these
        values directly, but must use environment variables as a workaround.

        We only set the environment variable if it's not already present, to avoid
        overwriting explicit user configuration via environment variables.
        """
        import os

        if self.model_name.startswith("ollama_chat/"):
            # Set OLLAMA_API_BASE if not already set (to avoid overwriting explicit user config)
            if "OLLAMA_API_BASE" not in os.environ:
                os.environ["OLLAMA_API_BASE"] = settings.ollama_api_base
                logger.info(
                    f"🔗 Configured Ollama API base URL: {settings.ollama_api_base}"
                )
            else:
                logger.debug("🔗 Using existing OLLAMA_API_BASE from environment")
        else:
            # For Gemini, set GEMINI_API_KEY if we have one configured
            if self.api_key:
                # Only set if not already present (preserve explicit env var if set)
                if "GEMINI_API_KEY" not in os.environ:
                    os.environ["GEMINI_API_KEY"] = self.api_key
                    logger.info("🔑 Configured Gemini API key from settings")
                else:
                    logger.debug("🔑 Using existing GEMINI_API_KEY from environment")
            else:
                logger.warning(
                    "⚠️  No Gemini API key configured. "
                    "Set DATAMETRONOME_ADK_API_KEY environment variable."
                )

    def _get_system_instructions(self) -> str:
        """Get system instructions for the agent."""
        return """You are a helpful AI assistant for DataMetronome, a data quality monitoring platform.

DataMetronome is a data quality monitoring platform that helps organizations monitor and ensure the quality of their data.

Your role is to help users understand their data quality status, configure checks, and troubleshoot issues.

CRITICAL: CONVERSATION CONTEXT AND MEMORY
- You MUST maintain conversation context throughout the entire conversation
- When a user refers to "this stave", "the stave", "it", "that", or similar phrases, you MUST look in the conversation history to understand what they're referring to
- If a stave name (like "bigquery crime") or stave ID was mentioned earlier in the conversation, you MUST remember it and use it when the user refers to it later
- NEVER ask the user to repeat information that was already provided in the current conversation
- Always check the conversation history before asking for clarification
- If the user says "yes please" or "with the structure" in response to a question about listing tables, use the context from the previous messages to understand which stave they're referring to

Key concepts in DataMetronome:
- Staves: Data sources (databases, data warehouses, etc.) - these are the data sources being monitored
- Clefs: Data quality checks/rules - these define what quality checks to perform on the data
- Checks: Execution results of clefs - these are the actual results from running quality checks

Available tools:
- list_staves: List all data sources (staves) in the system
- get_stave: Get details about a specific data source
- create_stave: Create a new data source (stave)
- list_stave_tables: List all tables in a specific data source, optionally with their structure/schema
- get_table_sample: Get a sample of data from a specific table to analyze data patterns and identify important fields
- suggest_quality_checks: Intelligently suggest quality checks based on table structure, column names, and data types. Can optionally analyze sample data for better suggestions
- list_clefs: List all data quality checks (clefs)
- get_clef: Get details about a specific quality check
- list_checks: List check execution results
- get_summary_report: Get a summary report of system status
- get_quality_report: Get a detailed quality report

When users ask questions about DataMetronome, their data sources, tables, checks, or quality status, use the available tools to query the DataMetronome API and provide helpful, accurate answers.

If a user asks about tables in a datasource, use the list_stave_tables tool with the stave_id to show them what tables are available.

If a user asks for suggestions on what quality checks to create, or wants help setting up quality checks for their tables, use the suggest_quality_checks tool. This tool analyzes table structure (column names, data types, nullable constraints) and optionally sample data to intelligently suggest appropriate quality checks like:
- Row count checks for volume monitoring
- Freshness checks for timestamp columns
- Uniqueness checks for ID columns
- Pattern checks for email/format validation
- NULL checks for important nullable columns
- Range checks for numeric columns
- Allowed values checks for enum-like fields (when sample data shows distinct value sets)

The suggest_quality_checks tool can analyze sample data (use_sample_data=True) to identify important fields based on actual data patterns, not just schema. This helps identify:
- Fields with unique values (potential keys)
- Enum/category fields with limited distinct values
- Numeric fields with actual data ranges
- Fields with data quality concerns (high NULL percentages)

You can also use get_table_sample to get a sample of data from a table and analyze it separately. This is useful when users want to understand their data better before creating quality checks.

Always remember: DataMetronome is the platform you're helping with. It's a real data quality monitoring system, not a hypothetical concept.

Be concise but informative. If a user asks about their data sources, tables, checks, or quality status, use the appropriate tools to get current information."""

    def _get_adk_tools(self):  # type: ignore[return-type]
        """Get ADK tool definitions.

        Returns:
            List of ADK tool definitions
        """
        # ADK tools are defined as functions that the agent can call
        # We'll define them as async functions that the agent can invoke
        return [
            self.list_staves,
            self.get_stave,
            self.create_stave,
            self.list_stave_tables,  # Add table listing tool
            self.get_table_sample,  # Get sample data from a table
            self.suggest_quality_checks,  # Smart quality check suggestions
            self.list_clefs,
            self.get_clef,
            self.list_checks,
            self.get_summary_report,
            self.get_quality_report,
        ]

    async def list_staves(self, limit: int = 100, skip: int = 0) -> dict[str, object]:
        """List all data sources (staves) in DataMetronome."""
        try:
            from datetime import datetime

            from datametronome_podium.core.database import get_db
            from datametronome_podium.services.stave_service import deserialize_stave

            db = await get_db()
            staves = await db.query(
                {
                    "sql": "SELECT * FROM staves ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    "params": [limit, skip],
                }
            )

            staves_list = []
            for stave in staves:
                try:
                    deserialized = deserialize_stave(stave)
                    stave_dict = deserialized.model_dump()
                    # Convert datetime objects to strings for JSON compatibility
                    if isinstance(stave_dict.get("created_at"), datetime):
                        stave_dict["created_at"] = stave_dict["created_at"].isoformat()
                    if isinstance(stave_dict.get("updated_at"), datetime):
                        stave_dict["updated_at"] = stave_dict["updated_at"].isoformat()
                    staves_list.append(stave_dict)
                except Exception as e:
                    logger.warning(
                        f"Failed to deserialize stave {stave.get('id', 'unknown')}: {e}"
                    )
                    continue

            return {"staves": staves_list, "count": len(staves_list)}
        except Exception as e:
            logger.error(f"Error listing staves: {e}", exc_info=True)
            return {"error": f"Failed to list staves: {str(e)}", "staves": []}

    async def get_stave(self, stave_id: str) -> dict[str, object]:
        """Get details about a specific data source (stave) by ID."""
        try:
            from datetime import datetime

            from datametronome_podium.core.database import get_db
            from datametronome_podium.services.stave_service import deserialize_stave

            db = await get_db()
            staves = await db.query(
                {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
            )

            if not staves:
                return {"error": f"Stave not found: {stave_id}"}

            deserialized = deserialize_stave(staves[0])
            stave_dict = deserialized.model_dump()
            # Convert datetime objects to strings for JSON compatibility
            if isinstance(stave_dict.get("created_at"), datetime):
                stave_dict["created_at"] = stave_dict["created_at"].isoformat()
            if isinstance(stave_dict.get("updated_at"), datetime):
                stave_dict["updated_at"] = stave_dict["updated_at"].isoformat()

            return stave_dict
        except Exception as e:
            logger.error(f"Error getting stave {stave_id}: {e}", exc_info=True)
            return {"error": f"Failed to get stave: {str(e)}"}

    async def create_stave(
        self,
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

            from datametronome_podium.core.database import get_db
            from datametronome_podium.services.stave_service import deserialize_stave

            db = await get_db()

            # Generate ID and timestamps
            stave_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat() + "Z"

            # Insert the new stave
            success = await db.write(
                [
                    {
                        "table": "staves",
                        "id": stave_id,
                        "name": name,
                        "description": description,
                        "data_source_type": data_source_type,
                        "connection_config": json.dumps(connection_config),
                        "is_active": is_active,
                        "created_at": now,
                        "updated_at": now,
                    }
                ],
                "staves",
            )

            if not success:
                return {"error": "Failed to create stave in database"}

            # Return the created stave
            staves = await db.query(
                {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
            )
            if not staves:
                return {"error": "Stave created but could not be retrieved"}

            deserialized = deserialize_stave(staves[0])
            stave_dict = deserialized.model_dump()
            # Convert datetime objects to strings for JSON compatibility
            if isinstance(stave_dict.get("created_at"), datetime):
                stave_dict["created_at"] = stave_dict["created_at"].isoformat()
            if isinstance(stave_dict.get("updated_at"), datetime):
                stave_dict["updated_at"] = stave_dict["updated_at"].isoformat()

            return stave_dict
        except Exception as e:
            logger.error(f"Error creating stave: {e}", exc_info=True)
            return {"error": f"Failed to create stave: {str(e)}"}

    async def list_stave_tables(
        self, stave_id: str, include_structure: bool = True
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
            from datametronome_podium.core.database import get_db
            from datametronome_podium.services.connection_tester import ConnectionTester
            from datametronome_podium.services.stave_service import deserialize_stave

            db = await get_db()
            staves = await db.query(
                {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
            )

            if not staves:
                return {"error": f"Stave not found: {stave_id}"}

            stave = deserialize_stave(staves[0])

            # Get connector based on stave type
            tester = ConnectionTester()
            connector = await tester.get_connector(stave, read_only=True)

            # List tables using the connector's list_tables method
            if not hasattr(connector, "list_tables"):
                return {
                    "error": f"list_tables not available for {stave.data_source_type} connector"
                }

            # Call list_tables with appropriate parameters based on data source type
            if stave.data_source_type == "bigquery":
                dataset = stave.connection_config.get("dataset")
                table_names = await connector.list_tables(dataset)
            elif stave.data_source_type in ["postgres", "postgresql"]:
                schema = stave.connection_config.get("schema", "public")
                table_names = await connector.list_tables(schema)
            else:
                table_names = await connector.list_tables()

            # Get structure for each table if requested
            tables = []
            for table_name in table_names:
                table_info = {"name": table_name}
                if include_structure:
                    try:
                        if hasattr(connector, "get_table_info"):
                            structure = await connector.get_table_info(table_name)
                            table_info["structure"] = structure
                    except Exception as e:
                        logger.warning(
                            f"Could not get structure for table {table_name}: {e}"
                        )
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
            logger.error(
                f"Error listing tables for stave {stave_id}: {e}", exc_info=True
            )
            return {"error": f"Failed to list tables: {str(e)}"}
        finally:
            if connector:
                try:
                    await connector.close()
                except:
                    pass

    async def get_table_sample(
        self, stave_id: str, table_name: str, limit: int = 100
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
            from datametronome_podium.core.database import get_db
            from datametronome_podium.services.connection_tester import ConnectionTester
            from datametronome_podium.services.stave_service import deserialize_stave

            db = await get_db()
            staves = await db.query(
                {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
            )

            if not staves:
                return {"error": f"Stave not found: {stave_id}"}

            stave = deserialize_stave(staves[0])

            # Log connection config (without sensitive data) for debugging
            config_for_logging = {
                k: v if k not in ["credentials_json", "password"] else "***REDACTED***"
                for k, v in (stave.connection_config or {}).items()
            }
            logger.info(
                f"Getting connector for stave {stave_id} ({stave.data_source_type}) "
                f"with config keys: {list(config_for_logging.keys())}"
            )

            # Get connector based on stave type
            tester = ConnectionTester()
            connector = await tester.get_connector(stave, read_only=True)

            # Build query based on data source type
            if stave.data_source_type == "bigquery":
                # BigQuery uses backticks for table names and LIMIT syntax
                query = f"SELECT * FROM `{table_name}` LIMIT {limit}"
            elif stave.data_source_type in ["postgres", "postgresql"]:
                # Postgres uses double quotes for identifiers
                query = f'SELECT * FROM "{table_name}" LIMIT {limit}'
            else:
                # SQLite and others
                query = f"SELECT * FROM {table_name} LIMIT {limit}"

            # Execute query
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

            # Analyze the sample data
            analysis = self._analyze_sample_data(sample_data)

            return {
                "success": True,
                "stave_id": stave_id,
                "stave_name": stave.name,
                "data_source_type": stave.data_source_type,
                "table_name": table_name,
                "row_count": len(sample_data),
                "limit": limit,
                "columns": list(sample_data[0].keys()) if sample_data else [],
                "sample_data": sample_data[:10],  # Return first 10 rows for display
                "analysis": analysis,
            }
        except Exception as e:
            logger.error(
                f"Error getting sample data from table {table_name} in stave {stave_id}: {e}",
                exc_info=True,
            )
            return {"error": f"Failed to get sample data: {str(e)}"}
        finally:
            if connector:
                try:
                    await connector.close()
                except:
                    pass

    def _analyze_sample_data(self, sample_data: list[dict]) -> dict:
        """Analyze sample data to identify important fields and patterns.

        Args:
            sample_data: List of dictionaries representing rows

        Returns:
            Dictionary with analysis results including important fields and patterns
        """
        if not sample_data:
            return {
                "message": "No data to analyze",
                "important_fields": [],
                "patterns": {},
            }

        important_fields = []
        patterns = {}
        field_stats = {}

        # Get all column names
        columns = list(sample_data[0].keys()) if sample_data else []

        for col in columns:
            col_values = [row.get(col) for row in sample_data if col in row]
            non_null_values = [v for v in col_values if v is not None]
            null_count = len(col_values) - len(non_null_values)
            null_percentage = (null_count / len(col_values) * 100) if col_values else 0

            # Calculate statistics
            stats = {
                "total_values": len(col_values),
                "non_null_count": len(non_null_values),
                "null_count": null_count,
                "null_percentage": round(null_percentage, 2),
                "unique_count": len(set(non_null_values)) if non_null_values else 0,
            }

            # Determine if field is important based on various criteria
            importance_score = 0
            importance_reasons = []

            # Check for uniqueness (potential key)
            if (
                stats["unique_count"] == stats["non_null_count"]
                and stats["non_null_count"] > 0
            ):
                importance_score += 10
                importance_reasons.append("All values are unique (potential key)")

            # Check for low null percentage (important data)
            if null_percentage < 5:
                importance_score += 5
                importance_reasons.append("Very few NULL values")

            # Check for high null percentage (might indicate data quality issue)
            if null_percentage > 50:
                importance_score += 3
                importance_reasons.append("High NULL percentage (data quality concern)")

            # Check for consistent patterns (enums, categories)
            if non_null_values:
                unique_ratio = stats["unique_count"] / stats["non_null_count"]
                if unique_ratio < 0.1 and stats["non_null_count"] > 10:
                    # Few unique values relative to total - likely enum/category
                    unique_values = list(set(non_null_values))[:20]  # Limit to 20
                    patterns[col] = {
                        "type": "enum_like",
                        "unique_values": unique_values,
                        "unique_count": stats["unique_count"],
                    }
                    importance_score += 4
                    importance_reasons.append("Appears to be an enum/category field")

            # Check for numeric patterns
            numeric_values = []
            for v in non_null_values:
                try:
                    if isinstance(v, (int, float)):
                        numeric_values.append(float(v))
                    elif (
                        isinstance(v, str)
                        and v.replace(".", "").replace("-", "").isdigit()
                    ):
                        numeric_values.append(float(v))
                except (ValueError, TypeError):
                    pass

            if numeric_values:
                stats["is_numeric"] = True
                stats["min"] = min(numeric_values)
                stats["max"] = max(numeric_values)
                stats["avg"] = sum(numeric_values) / len(numeric_values)
                stats["numeric_count"] = len(numeric_values)

                # Check for reasonable ranges
                if (
                    stats["min"] >= 0
                    and stats["max"] <= 100
                    and "percent" in col.lower()
                ):
                    importance_score += 3
                    importance_reasons.append(
                        "Numeric field with percentage-like range"
                    )

            # Check for timestamp-like patterns
            timestamp_indicators = [
                "created",
                "updated",
                "modified",
                "date",
                "time",
                "at",
            ]
            if any(indicator in col.lower() for indicator in timestamp_indicators):
                importance_score += 6
                importance_reasons.append("Appears to be a timestamp field")

            # Check for ID-like patterns
            id_indicators = ["id", "uuid", "key", "pk"]
            if any(indicator in col.lower() for indicator in id_indicators):
                importance_score += 7
                importance_reasons.append("Appears to be an ID/key field")

            # Check for email-like patterns
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

            # Mark as important if score is high enough
            if importance_score >= 5:
                important_fields.append(
                    {
                        "field": col,
                        "importance_score": importance_score,
                        "reasons": importance_reasons,
                        "stats": stats,
                    }
                )

        # Sort important fields by score
        important_fields.sort(key=lambda x: x["importance_score"], reverse=True)

        return {
            "message": f"Analyzed {len(sample_data)} rows and {len(columns)} columns",
            "important_fields": important_fields[:10],  # Top 10 most important
            "patterns": patterns,
            "field_stats": {
                k: v for k, v in list(field_stats.items())[:20]
            },  # Limit stats
        }

    async def suggest_quality_checks(
        self,
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
                           (default: True). When True, analyzes actual data patterns
                           to identify important fields and suggest more accurate checks.
            sample_limit: Number of rows to sample when use_sample_data is True
                        (default: 100)

        Returns:
            Dictionary with suggested quality checks for each table analyzed
        """
        connector = None
        try:
            from datametronome_podium.core.database import get_db
            from datametronome_podium.services.connection_tester import ConnectionTester
            from datametronome_podium.services.stave_service import deserialize_stave

            db = await get_db()
            staves = await db.query(
                {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
            )

            if not staves:
                return {"error": f"Stave not found: {stave_id}"}

            stave = deserialize_stave(staves[0])

            # Log connection config (without sensitive data) for debugging
            config_for_logging = {
                k: v if k not in ["credentials_json", "password"] else "***REDACTED***"
                for k, v in (stave.connection_config or {}).items()
            }
            logger.info(
                f"Getting connector for stave {stave_id} ({stave.data_source_type}) "
                f"with config keys: {list(config_for_logging.keys())}"
            )

            # Get connector based on stave type
            tester = ConnectionTester()
            connector = await tester.get_connector(stave, read_only=True)

            # Get list of tables to analyze
            if table_name:
                tables_to_analyze = [table_name]
            else:
                # List all tables
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
                    # Get table structure
                    if not hasattr(connector, "get_table_info"):
                        continue

                    table_info = await connector.get_table_info(tbl_name)

                    # Handle different return formats
                    if isinstance(table_info, dict):
                        columns = table_info.get("columns", [])
                    elif isinstance(table_info, list):
                        columns = table_info
                    else:
                        continue

                    if not columns:
                        continue

                    # Get sample data if requested
                    sample_analysis = None
                    if use_sample_data:
                        try:
                            # Build query to get sample data
                            if stave.data_source_type == "bigquery":
                                # For BigQuery, we need to qualify the table name with dataset
                                dataset = stave.connection_config.get("dataset")
                                if dataset:
                                    # Handle both "dataset" and "project.dataset" formats
                                    if "." in dataset:
                                        # Dataset already includes project (e.g., "bigquery-public-data.samples")
                                        qualified_table = f"`{dataset}.{tbl_name}`"
                                    else:
                                        # Just dataset name, use project from connector
                                        project_id = stave.connection_config.get(
                                            "project_id"
                                        )
                                        if project_id:
                                            qualified_table = (
                                                f"`{project_id}.{dataset}.{tbl_name}`"
                                            )
                                        else:
                                            qualified_table = f"`{dataset}.{tbl_name}`"
                                else:
                                    # Fallback to just table name (might work if dataset is set in connector)
                                    qualified_table = f"`{tbl_name}`"
                                query = f"SELECT * FROM {qualified_table} LIMIT {sample_limit}"
                            elif stave.data_source_type in ["postgres", "postgresql"]:
                                query = (
                                    f'SELECT * FROM "{tbl_name}" LIMIT {sample_limit}'
                                )
                            else:
                                query = f"SELECT * FROM {tbl_name} LIMIT {sample_limit}"

                            sample_data = await connector.query({"sql": query})
                            if sample_data:
                                sample_analysis = self._analyze_sample_data(sample_data)
                        except Exception as e:
                            logger.warning(
                                f"Could not get sample data for table {tbl_name}: {e}"
                            )
                            sample_analysis = None

                    # Analyze columns and suggest checks (schema-based)
                    table_suggestions = self._analyze_table_structure(
                        tbl_name, columns, stave.data_source_type
                    )

                    # Enhance suggestions with sample data analysis if available
                    if sample_analysis and sample_analysis.get("important_fields"):
                        enhanced_suggestions = self._enhance_suggestions_with_data(
                            table_suggestions, sample_analysis, tbl_name
                        )
                        table_suggestions = enhanced_suggestions

                    if table_suggestions:
                        reasoning = f"Analyzed {len(columns)} columns"
                        if sample_analysis:
                            reasoning += (
                                f" and {sample_analysis.get('message', 'sample data')}"
                            )
                        reasoning += (
                            f" - suggested {len(table_suggestions)} quality checks"
                        )

                        suggestions.append(
                            {
                                "table": tbl_name,
                                "suggested_clefs": table_suggestions,
                                "reasoning": reasoning,
                                "data_analysis_used": sample_analysis is not None,
                                "important_fields": sample_analysis.get(
                                    "important_fields", []
                                )[:5]
                                if sample_analysis
                                else [],
                            }
                        )
                except Exception as e:
                    logger.warning(f"Could not analyze table {tbl_name}: {e}")
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
                f"Error suggesting quality checks for stave {stave_id}: {error_type}: {error_msg}",
                exc_info=True,
            )
            # Provide more helpful error message
            if (
                "credentials" in error_msg.lower()
                or "authentication" in error_msg.lower()
            ):
                return {
                    "error": f"Authentication error: {error_msg}. "
                    f"Please verify the stave's connection configuration has valid credentials."
                }
            return {
                "error": f"Failed to suggest quality checks ({error_type}): {error_msg}"
            }
        finally:
            if connector:
                try:
                    await connector.close()
                except:
                    pass

    def _enhance_suggestions_with_data(
        self,
        schema_suggestions: list[dict],
        data_analysis: dict,
        table_name: str,
    ) -> list[dict]:
        """Enhance schema-based suggestions with insights from actual data analysis.

        Args:
            schema_suggestions: List of suggestions from schema analysis
            data_analysis: Analysis results from sample data
            table_name: Name of the table

        Returns:
            Enhanced list of suggestions
        """
        enhanced = list(schema_suggestions)  # Start with schema suggestions
        important_fields = data_analysis.get("important_fields", [])
        patterns = data_analysis.get("patterns", {})
        field_stats = data_analysis.get("field_stats", {})

        # Track which columns already have suggestions
        columns_with_suggestions = set()
        for sug in schema_suggestions:
            config = sug.get("config", {})
            if "column" in config:
                columns_with_suggestions.add(config["column"])

        # Add suggestions for important fields not yet covered
        for field_info in important_fields:
            field_name = field_info["field"]
            if field_name in columns_with_suggestions:
                continue  # Already has a suggestion

            importance_score = field_info.get("importance_score", 0)
            stats = field_info.get("stats", {})
            reasons = field_info.get("reasons", [])

            # High importance fields get priority suggestions
            if importance_score >= 8:
                # Check if it's an enum-like field
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
                                    "allowed_values": allowed_values[
                                        :50
                                    ],  # Limit to 50 values
                                },
                                "warn": "if_not_in: [] > 1%",
                                "fail": "if_not_in: [] > 5%",
                                "schedule": "@daily",
                                "priority": "high",
                                "reasoning": f"Data analysis shows this field has {pattern_info.get('unique_count')} distinct values (enum-like pattern). "
                                f"Suggested allowed_values: {', '.join(map(str, allowed_values[:10]))}...",
                            }
                        )

                # Check for numeric fields with actual ranges
                elif (
                    stats.get("is_numeric")
                    and stats.get("min") is not None
                    and stats.get("max") is not None
                ):
                    min_val = stats.get("min", 0)
                    max_val = stats.get("max", 100)
                    # Only suggest if range is reasonable
                    if max_val - min_val < 10000:  # Reasonable range
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
                                "warn": f"if_out_of_range > 1%",
                                "fail": f"if_out_of_range > 5%",
                                "schedule": "@daily",
                                "priority": "high",
                                "reasoning": f"Data analysis shows values range from {min_val} to {max_val}. "
                                f"Average: {stats.get('avg', 0):.2f}",
                            }
                        )

            # Add NULL checks for important nullable fields
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
                            "reasoning": f"Data analysis shows {stats.get('null_percentage', 0):.1f}% NULL values. "
                            f"This is an important field based on data patterns.",
                        }
                    )

        # Prioritize suggestions: high priority first, then by importance score
        def get_priority(sug):
            priority_map = {"high": 3, "medium": 2, "low": 1}
            return priority_map.get(sug.get("priority", "medium"), 2)

        enhanced.sort(key=get_priority, reverse=True)

        return enhanced

    def _analyze_table_structure(
        self, table_name: str, columns: list[dict], data_source_type: str
    ) -> list[dict]:
        """Analyze table structure and generate quality check suggestions.

        Args:
            table_name: Name of the table
            columns: List of column dictionaries with structure info
            data_source_type: Type of data source (postgres, bigquery, etc.)

        Returns:
            List of suggested clef configurations
        """
        suggestions = []

        # Common patterns for column names that suggest specific checks
        timestamp_patterns = [
            "timestamp",
            "created_at",
            "updated_at",
            "modified_at",
            "date",
            "time",
            "_at",
            "_date",
            "_time",
        ]
        id_patterns = ["id", "_id", "uuid", "key", "pk"]
        email_patterns = ["email", "e_mail", "email_address"]
        numeric_patterns = [
            "amount",
            "price",
            "cost",
            "quantity",
            "count",
            "age",
            "score",
            "rating",
            "percent",
            "percentage",
        ]

        has_timestamp = False
        has_id_column = False

        for col in columns:
            col_name = col.get("column_name", "").lower()
            data_type = str(col.get("data_type", "")).lower()
            is_nullable = col.get("is_nullable", "YES").upper() == "YES"

            # Normalize data type
            is_numeric = any(
                dt in data_type
                for dt in [
                    "int",
                    "numeric",
                    "decimal",
                    "float",
                    "double",
                    "real",
                    "number",
                ]
            )
            is_string = any(
                dt in data_type for dt in ["varchar", "char", "text", "string", "str"]
            )
            is_timestamp = any(
                dt in data_type for dt in ["timestamp", "datetime", "date", "time"]
            )

            # Suggest row_count check (once per table)
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

            # Timestamp columns -> freshness check
            if is_timestamp or any(
                pattern in col_name for pattern in timestamp_patterns
            ):
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

            # ID columns -> uniqueness check
            # Check if column name suggests it's a primary key or unique identifier
            is_id_like = (
                col_name == "id"
                or col_name.endswith("_id")
                or col_name in ["uuid", "key", "pk", "primary_key"]
            )

            if is_id_like:
                has_id_column = True
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

            # Email columns -> pattern and null checks
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

            # Nullable columns -> null check (if not an ID column)
            if is_nullable and not any(pattern in col_name for pattern in id_patterns):
                # Only suggest for important columns (not every nullable column)
                if any(
                    pattern in col_name
                    for pattern in email_patterns
                    + numeric_patterns
                    + ["name", "status"]
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

            # Numeric columns -> range check
            if is_numeric and any(pattern in col_name for pattern in numeric_patterns):
                # Try to infer reasonable bounds based on column name
                min_val = 0
                max_val = None

                if "age" in col_name:
                    max_val = 150
                elif "percent" in col_name or "percentage" in col_name:
                    max_val = 100
                elif "rating" in col_name or "score" in col_name:
                    max_val = 10  # Common default, but might need adjustment

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
                            "warn": f"if_out_of_range > 1%",
                            "fail": f"if_out_of_range > 5%",
                            "schedule": "@daily",
                            "priority": "medium",
                            "reasoning": f"Column '{col.get('column_name')}' is numeric and suggests a bounded range",
                        }
                    )

            # String columns with common patterns -> pattern check
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
                        "reasoning": f"Column '{col.get('column_name')}' appears to be an enum/category column. "
                        f"Consider specifying allowed_values in the config after reviewing actual data.",
                        "note": "You may need to update the config with actual allowed_values after reviewing the data",
                    }
                )

        # If no timestamp found but table has common timestamp-like columns, suggest freshness
        if not has_timestamp:
            # Check if there are any date/time-like columns we might have missed
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

    async def list_clefs(
        self, limit: int = 100, skip: int = 0, stave_id: str | None = None
    ) -> dict[str, object]:
        """List all data quality checks (clefs) in DataMetronome."""
        try:
            from datetime import datetime

            from datametronome_podium.core.database import get_db
            from datametronome_podium.services.stave_service import deserialize_clef

            db = await get_db()

            # Build query based on filters
            if stave_id:
                clefs = await db.query(
                    {
                        "sql": "SELECT * FROM clefs WHERE stave_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                        "params": [stave_id, limit, skip],
                    }
                )
            else:
                clefs = await db.query(
                    {
                        "sql": "SELECT * FROM clefs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                        "params": [limit, skip],
                    }
                )

            clefs_list = []
            for clef in clefs:
                try:
                    deserialized = deserialize_clef(clef)
                    clef_dict = deserialized.model_dump()
                    # Convert datetime objects to strings for JSON compatibility
                    if isinstance(clef_dict.get("created_at"), datetime):
                        clef_dict["created_at"] = clef_dict["created_at"].isoformat()
                    if isinstance(clef_dict.get("updated_at"), datetime):
                        clef_dict["updated_at"] = clef_dict["updated_at"].isoformat()
                    clefs_list.append(clef_dict)
                except Exception as e:
                    logger.warning(
                        f"Failed to deserialize clef {clef.get('id', 'unknown')}: {e}"
                    )
                    continue

            return {"clefs": clefs_list, "count": len(clefs_list)}
        except Exception as e:
            logger.error(f"Error listing clefs: {e}", exc_info=True)
            return {"error": f"Failed to list clefs: {str(e)}", "clefs": []}

    async def get_clef(self, clef_id: str) -> dict[str, object]:
        """Get details about a specific quality check (clef) by ID."""
        try:
            from datetime import datetime

            from datametronome_podium.core.database import get_db
            from datametronome_podium.services.stave_service import deserialize_clef

            db = await get_db()
            clefs = await db.query(
                {"sql": "SELECT * FROM clefs WHERE id = ?", "params": [clef_id]}
            )

            if not clefs:
                return {"error": f"Clef not found: {clef_id}"}

            deserialized = deserialize_clef(clefs[0])
            clef_dict = deserialized.model_dump()
            # Convert datetime objects to strings for JSON compatibility
            if isinstance(clef_dict.get("created_at"), datetime):
                clef_dict["created_at"] = clef_dict["created_at"].isoformat()
            if isinstance(clef_dict.get("updated_at"), datetime):
                clef_dict["updated_at"] = clef_dict["updated_at"].isoformat()

            return clef_dict
        except Exception as e:
            logger.error(f"Error getting clef {clef_id}: {e}", exc_info=True)
            return {"error": f"Failed to get clef: {str(e)}"}

    async def list_checks(
        self,
        limit: int = 20,
        status: str | None = None,
        stave_id: str | None = None,
        clef_id: str | None = None,
    ) -> dict[str, object]:
        """List check execution results."""
        try:
            from datametronome_podium.core.database import get_db

            db = await get_db()

            # Build query with filters
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

            checks = await db.query(
                {
                    "sql": f"SELECT * FROM checks WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?",
                    "params": params,
                }
            )

            return checks
        except Exception as e:
            logger.error(f"Error listing checks: {e}", exc_info=True)
            return {"error": f"Failed to list checks: {str(e)}", "checks": []}

    async def get_summary_report(self, days: int = 7) -> dict[str, object]:
        """Get a summary report of DataMetronome system status.

        Args:
            days: Number of days to look back for recent activity. Defaults to 7.
        """
        try:
            from datetime import datetime, timedelta

            from datametronome_podium.core.database import get_db

            db = await get_db()

            # Get basic counts
            staves_count = await db.query(
                {
                    "sql": "SELECT COUNT(*) as count FROM staves WHERE is_active = 1",
                    "params": [],
                }
            )
            total_staves = staves_count[0]["count"] if staves_count else 0

            clefs_count = await db.query(
                {
                    "sql": "SELECT COUNT(*) as count FROM clefs WHERE is_active = 1",
                    "params": [],
                }
            )
            total_clefs = clefs_count[0]["count"] if clefs_count else 0

            checks_count = await db.query(
                {"sql": "SELECT COUNT(*) as count FROM checks", "params": []}
            )
            total_checks = checks_count[0]["count"] if checks_count else 0

            # Get recent activity within the specified time period
            threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
            recent_checks = await db.query(
                {
                    "sql": "SELECT * FROM checks WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 5",
                    "params": [threshold_date],
                }
            )

            return {
                "generated_at": datetime.now().isoformat(),
                "period_days": days,
                "summary": {
                    "total_staves": total_staves,
                    "total_clefs": total_clefs,
                    "total_checks": total_checks,
                },
                "recent_activity": recent_checks,
            }
        except Exception as e:
            logger.error(f"Error generating summary report: {e}", exc_info=True)
            return {"error": f"Failed to generate summary report: {str(e)}"}

    async def get_quality_report(self, days: int = 7) -> dict[str, object]:
        """Get a quality report showing data quality metrics."""
        try:
            from datetime import datetime, timedelta

            from datametronome_podium.core.database import get_db

            db = await get_db()

            # Calculate date threshold
            threshold_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Get checks in the time period
            period_checks = await db.query(
                {
                    "sql": "SELECT * FROM checks WHERE timestamp >= ? ORDER BY timestamp DESC",
                    "params": [threshold_date],
                }
            )

            # Calculate quality metrics
            total_checks = len(period_checks)
            passed_checks = sum(
                1 for check in period_checks if check["status"] == "passed"
            )
            failed_checks = total_checks - passed_checks

            quality_score = (
                (passed_checks / total_checks * 100) if total_checks > 0 else 100.0
            )

            # Get anomaly summary
            anomalies = await db.query(
                {
                    "sql": "SELECT * FROM anomalies WHERE detected_at >= ? ORDER BY detected_at DESC",
                    "params": [threshold_date],
                }
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
                    "critical": sum(
                        1 for a in anomalies if a["severity"] == "critical"
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Error generating quality report: {e}", exc_info=True)
            return {"error": f"Failed to generate quality report: {str(e)}"}

    async def process_message(
        self,
        message: str,
        conversation_id: str | None = None,
        context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Process a user message using the ADK agent.

        Args:
            message: User's message
            conversation_id: Optional conversation ID for context
            context: Optional additional context

        Returns:
            Response from the agent with message and optional tool calls
        """
        if not ADK_AVAILABLE or not self.agent:
            # Fallback to HTTP-based approach if ADK is not available
            logger.warning(
                "ADK not available or agent not initialized, using HTTP fallback"
            )
            return await self._process_message_http(message, conversation_id, context)

        try:
            logger.info("Using ADK agent to process message")
            # Use ADK agent to process the message
            # ADK run_async expects a Content object, not a plain string
            # Import types from google.genai to create Content objects
            from google.genai import types

            # Build message with conversation history context if available
            # This ensures the agent remembers previous messages in the conversation
            # IMPORTANT: Put history FIRST so the agent sees it before the current message
            message_with_context = message
            if context and "history" in context:
                history_messages = context["history"]
                if (
                    history_messages
                    and isinstance(history_messages, list)
                    and len(history_messages) > 0
                ):
                    # Limit to last 10 messages to reduce token usage and costs
                    # Recent context is usually more relevant than older messages
                    max_history_messages = 10
                    recent_history = (
                        history_messages[-max_history_messages:]
                        if len(history_messages) > max_history_messages
                        else history_messages
                    )
                    logger.info(
                        f"📚 Including last {len(recent_history)} messages from conversation history (out of {len(history_messages)} total)"
                    )
                    # Build conversation history context with clear formatting
                    history_context = "\n\n" + "=" * 80 + "\n"
                    history_context += (
                        "CONVERSATION HISTORY - READ THIS CAREFULLY BEFORE RESPONDING\n"
                    )
                    history_context += (
                        f"(Showing last {len(recent_history)} messages)\n"
                    )
                    history_context += "=" * 80 + "\n"
                    for hist_msg in recent_history:  # Include only last 10 messages
                        if isinstance(hist_msg, dict):
                            role = hist_msg.get("role", "")
                            content = hist_msg.get("content", "")
                            tool_calls = hist_msg.get("tool_calls")

                            if role and content:
                                role_label = "USER" if role == "user" else "ASSISTANT"
                                history_context += f"\n[{role_label}]\n{content}\n"

                                # Include tool calls information if available
                                # This helps the agent remember what tools were called and their results
                                if tool_calls and isinstance(tool_calls, list):
                                    for tc in tool_calls:
                                        if isinstance(tc, dict):
                                            tool_name = tc.get("name", "")
                                            tool_args = tc.get("arguments", {})
                                            if tool_name:
                                                history_context += (
                                                    f"[Tool called: {tool_name}"
                                                )
                                                if tool_args:
                                                    history_context += (
                                                        f" with args: {tool_args}"
                                                    )
                                                history_context += "]\n"

                    # Extract and highlight any IDs mentioned in the conversation
                    # Use recent_history for extraction to match what we're showing
                    uuid_pattern = (
                        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
                    )
                    mentioned_ids = set()
                    mentioned_stave_names = set()
                    stave_name_to_id = (
                        {}
                    )  # Map stave names to IDs if both are mentioned

                    for hist_msg in recent_history:
                        if isinstance(hist_msg, dict):
                            content = str(hist_msg.get("content", ""))
                            # Extract UUIDs
                            ids_found = re.findall(uuid_pattern, content, re.IGNORECASE)
                            mentioned_ids.update(ids_found)

                            # Extract stave names (look for patterns like "bigquery crime", "the bigquery crime stave", etc.)
                            # Look for quoted strings or phrases after "stave" or before "stave"
                            stave_name_patterns = [
                                r'stave[:\s]+"?([^"]+)"?',
                                r'"([^"]+)"[:\s]+stave',
                                r"stave\s+([a-zA-Z0-9\s]+)",
                                r"([a-zA-Z0-9\s]+)\s+stave",
                                r'stave\s+id\s+for\s+["\']([^"\']+)["\']',  # "stave ID for 'name'"
                                r'["\']([^"\']+)["\']\s+stave',  # "'name' stave"
                                r'stave\s+["\']([^"\']+)["\']',  # "stave 'name'"
                            ]
                            for pattern in stave_name_patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    if isinstance(match, tuple):
                                        match = match[0] if match else ""
                                    match = match.strip().strip('"').strip("'")
                                    # Filter out UUIDs and very short/long strings
                                    if (
                                        match
                                        and len(match) > 2
                                        and len(match) < 100
                                        and not re.match(
                                            uuid_pattern, match, re.IGNORECASE
                                        )
                                    ):
                                        mentioned_stave_names.add(match)

                            # Also look for quoted strings that might be stave names (common pattern: "bigquery crime")
                            quoted_strings = re.findall(
                                r'["\']([^"\']{3,50})["\']', content
                            )
                            for quoted in quoted_strings:
                                # If it's not a UUID and contains letters, it might be a stave name
                                if not re.match(
                                    uuid_pattern, quoted, re.IGNORECASE
                                ) and re.search(r"[a-zA-Z]", quoted):
                                    # Check if it appears in context that suggests it's a stave name
                                    quoted_lower = quoted.lower()
                                    if any(
                                        keyword in content.lower()
                                        for keyword in [
                                            "stave",
                                            "data source",
                                            "datasource",
                                            "bigquery",
                                            "postgres",
                                            "sqlite",
                                        ]
                                    ):
                                        mentioned_stave_names.add(quoted)

                            # Try to map stave names to IDs if they appear together
                            # Look for patterns like "stave ID for 'name' is xxxx-xxxx-xxxx"
                            mapping_pattern = r'(?:stave|id).*?["\']([^"\']+)["\'].*?(?:is|:)\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
                            mappings = re.findall(
                                mapping_pattern, content, re.IGNORECASE
                            )
                            for name, stave_id in mappings:
                                stave_name_to_id[name.strip()] = stave_id

                    history_context += "\n" + "=" * 80 + "\n"
                    history_context += "END OF CONVERSATION HISTORY\n"
                    history_context += "=" * 80 + "\n\n"

                    # Add extracted information section
                    if mentioned_ids or mentioned_stave_names:
                        history_context += (
                            "=== EXTRACTED INFORMATION FROM CONVERSATION ===\n"
                        )
                        if mentioned_stave_names:
                            history_context += "Mentioned Stave Names:\n"
                            for name in mentioned_stave_names:
                                if name in stave_name_to_id:
                                    history_context += (
                                        f"- '{name}' (ID: {stave_name_to_id[name]})\n"
                                    )
                                else:
                                    history_context += f"- '{name}'\n"
                            history_context += "\n"
                        if mentioned_ids:
                            history_context += "Mentioned Stave IDs:\n"
                            for id_val in mentioned_ids:
                                history_context += f"- {id_val}\n"
                            history_context += "\n"
                        history_context += "=== END OF EXTRACTED INFORMATION ===\n\n"
                        logger.info(
                            f"🔍 Extracted {len(mentioned_ids)} IDs and {len(mentioned_stave_names)} stave names from conversation history"
                        )

                    # Extract key topics and actions mentioned in conversation
                    # Use recent_history for topic extraction to match what we're showing
                    key_topics = []
                    if any(
                        "quality check" in str(hist_msg.get("content", "")).lower()
                        or "clef" in str(hist_msg.get("content", "")).lower()
                        for hist_msg in recent_history
                        if isinstance(hist_msg, dict)
                    ):
                        key_topics.append("quality checks/clefs")
                    if any(
                        "table" in str(hist_msg.get("content", "")).lower()
                        for hist_msg in recent_history
                        if isinstance(hist_msg, dict)
                    ):
                        key_topics.append("tables")
                    if any(
                        "suggest" in str(hist_msg.get("content", "")).lower()
                        or "recommend" in str(hist_msg.get("content", "")).lower()
                        for hist_msg in recent_history
                        if isinstance(hist_msg, dict)
                    ):
                        key_topics.append("suggestions/recommendations")

                    history_context += "CRITICAL INSTRUCTIONS - READ CAREFULLY:\n"
                    history_context += "=" * 80 + "\n"
                    history_context += "1. CONVERSATION CONTEXT:\n"
                    history_context += "   - You MUST read and understand the ENTIRE conversation history above\n"
                    history_context += "   - When the user says 'the one you suggested above', 'the one above', 'that one', etc., "
                    history_context += "you MUST look in the conversation history to find what was discussed\n"
                    history_context += "   - If the user asked about quality checks, tables, or other topics earlier, remember those topics\n"
                    if key_topics:
                        history_context += f"   - Topics discussed in this conversation: {', '.join(key_topics)}\n"
                    history_context += "\n"
                    history_context += "2. STAVE REFERENCES:\n"
                    history_context += "   - When the user refers to 'this stave', 'the stave', 'it', 'that stave', or similar phrases, "
                    history_context += "you MUST look in the conversation history above to find which stave they're referring to\n"
                    history_context += "   - If a stave NAME (like 'bigquery crime') was mentioned earlier, use that name to find the corresponding stave ID\n"
                    history_context += "   - Use the stave ID from the 'EXTRACTED INFORMATION' section above, or extract it from the conversation history\n"
                    history_context += "   - Do NOT ask the user for the stave ID or stave name if it was already mentioned in the conversation history\n"
                    history_context += "\n"
                    history_context += "3. USER CONFIRMATIONS:\n"
                    history_context += "   - When the user says 'yes please', 'with the structure', 'okay', or similar confirmations, "
                    history_context += "they are confirming they want you to proceed with the action you just suggested\n"
                    history_context += "   - Use the context from previous messages to understand what action they're confirming\n"
                    history_context += "\n"
                    history_context += "4. GENERAL RULES:\n"
                    history_context += "   - ALWAYS check the conversation history before asking for clarification\n"
                    history_context += "   - NEVER ask the user to repeat information that was already provided\n"
                    history_context += "   - If you're unsure, look in the conversation history first before asking\n"
                    history_context += "=" * 80 + "\n\n"
                    # Prepend history to current message
                    message_with_context = (
                        history_context + f"USER'S CURRENT MESSAGE: {message}"
                    )
                    logger.info(
                        f"✅ Conversation history included in message context (total length: {len(message_with_context)} chars)"
                    )
                    # Log a preview of the message to verify it's being constructed correctly
                    preview_length = min(500, len(message_with_context))
                    logger.debug(
                        f"📝 Message context preview (first {preview_length} chars):\n{message_with_context[:preview_length]}..."
                    )
                else:
                    logger.debug(
                        "No conversation history available or history is empty"
                    )
            else:
                logger.debug("No context or history in context provided")

            # Create a Content object with the user message (including history context)
            user_content = types.Content(
                role="user", parts=[types.Part(text=message_with_context)]
            )

            response_text: str = ""
            tool_calls = []
            last_response = None

            # Use Runner for proper session management
            # Agent.run_async() has different signature, so we use Runner instead
            from google.adk import Runner
            from google.adk.sessions import InMemorySessionService

            # Create session service and runner
            session_service = InMemorySessionService()
            runner = Runner(
                agent=self.agent,
                app_name="datametronome",
                session_service=session_service,
            )

            # Create or get session
            session_id = conversation_id or f"session-{uuid.uuid4().hex[:8]}"
            user_id = "default"

            # Try to get existing session, create if it doesn't exist
            try:
                session = await session_service.get_session(
                    app_name="datametronome", user_id=user_id, session_id=session_id
                )
                if session is None:
                    # Session doesn't exist, create it
                    session = await session_service.create_session(
                        app_name="datametronome", user_id=user_id, session_id=session_id
                    )
            except Exception as e:
                # Create new session if get_session fails
                logger.debug(f"Could not get session, creating new one: {e}")
                session = await session_service.create_session(
                    app_name="datametronome", user_id=user_id, session_id=session_id
                )

            if session is None:
                raise RuntimeError("Failed to create or retrieve session")

            # NOTE: We do NOT replay historical messages to avoid API costs
            # The full conversation history is already included in message_with_context,
            # so the model can see it without needing to replay messages through the API
            # This saves API calls and money while still maintaining full context
            if context and "history" in context:
                history_messages = context["history"]
                if (
                    history_messages
                    and isinstance(history_messages, list)
                    and len(history_messages) > 0
                ):
                    logger.info(
                        f"📚 Conversation history included in message text ({len(history_messages)} messages) - no API replay to save costs"
                    )

            # Call run_async on the runner with proper parameters
            # The session now contains the conversation history, AND the message includes history context
            # This double approach ensures the agent has full context
            async_gen = runner.run_async(
                user_id=user_id, session_id=session.id, new_message=user_content
            )

            # Iterate over the async generator
            # Events from runner.run_async() have a 'content' attribute with 'parts'
            async for event in async_gen:
                last_response = event

                # Extract text from event.content.parts[].text
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts") and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text
                            elif hasattr(part, "function_call"):
                                # This is a tool call, extract it
                                fc = part.function_call
                                tool_calls.append(
                                    {
                                        "id": getattr(
                                            fc, "id", f"call-{len(tool_calls)}"
                                        ),
                                        "name": getattr(fc, "name", ""),
                                        "arguments": getattr(fc, "args", {}),
                                    }
                                )
                    elif hasattr(event.content, "text"):
                        text = getattr(event.content, "text", "")
                        if text:
                            response_text += str(text)

                # Fallback: try direct text attribute
                elif hasattr(event, "text") and event.text:
                    text = getattr(event, "text", "")
                    if text:
                        response_text += str(text)

                # Fallback: try string conversion
                elif isinstance(event, str):
                    response_text += event

                # Collect tool calls from event if available
                if hasattr(event, "tool_calls"):
                    tool_calls_attr = getattr(event, "tool_calls", None)
                    if tool_calls_attr:
                        for tc in tool_calls_attr:
                            tool_calls.append(
                                {
                                    "id": getattr(tc, "id", f"call-{len(tool_calls)}"),
                                    "name": getattr(tc, "name", ""),
                                    "arguments": getattr(tc, "arguments", {}),
                                }
                            )

            # If we didn't get text from events, try to extract from last response
            if not response_text and last_response:
                # Try to extract from event.content.parts[].text
                if hasattr(last_response, "content") and last_response.content:
                    if (
                        hasattr(last_response.content, "parts")
                        and last_response.content.parts
                    ):
                        for part in last_response.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text
                    elif hasattr(last_response.content, "text"):
                        text = getattr(last_response.content, "text", "")
                        response_text = str(text) if text else response_text
                elif hasattr(last_response, "messages") and last_response.messages:
                    # Get the last message from the agent
                    last_message = last_response.messages[-1]
                    if hasattr(last_message, "content") and last_message.content:
                        if (
                            hasattr(last_message.content, "parts")
                            and last_message.content.parts
                        ):
                            for part in last_message.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_text += part.text
                        elif hasattr(last_message.content, "text"):
                            response_text = last_message.content.text
                    elif isinstance(last_message, dict) and "content" in last_message:
                        response_text = last_message["content"]
                elif hasattr(last_response, "text"):
                    text = getattr(last_response, "text", "")
                    response_text = str(text) if text else response_text

            return {
                "message": response_text or "I've processed your request.",
                "toolCalls": tool_calls if tool_calls else None,
                "model": self.model_name,  # Include model name in response
                "finishReason": "stop",  # Default finish reason
            }

        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__

            # Check if it's a rate limit error
            is_rate_limit = (
                "429" in error_str
                or "RateLimit" in error_type
                or "RESOURCE_EXHAUSTED" in error_str
                or "quota" in error_str.lower()
            )

            if is_rate_limit:
                logger.error(
                    f"⚠️ Rate limit error with ADK agent: {error_str}. "
                    f"This may be due to replaying too many historical messages. "
                    f"Consider reducing conversation history or using a model with higher quota limits."
                )
                # Return a helpful error message instead of falling back
                return {
                    "message": "I'm currently experiencing rate limit issues. Please try again in a few moments. "
                    "If this persists, consider starting a new conversation or reducing the conversation history.",
                    "toolCalls": None,
                    "model": self.model_name,
                    "finishReason": "error",
                    "error": "rate_limit",
                }

            logger.error(
                f"Error processing message with ADK agent: {str(e)}", exc_info=True
            )
            # Fallback to HTTP approach on error (but not for rate limits)
            logger.info("Falling back to HTTP-based agent")
            return await self._process_message_http(message, conversation_id, context)

    async def _process_message_http(
        self,
        message: str,
        conversation_id: str | None = None,
        context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Fallback HTTP-based message processing (for when ADK is not available)."""
        # This is the original HTTP-based implementation
        # Kept as fallback for when ADK is not installed
        if not self.api_key and not self.model_name.startswith("ollama_chat/"):
            raise ValueError("ADK API key not configured and not using Ollama")

        import httpx

        # For Ollama, use configured endpoint
        if self.model_name.startswith("ollama_chat/"):
            # Extract model name (e.g., "qwen2.5" from "ollama_chat/qwen2.5")
            model_name = self.model_name.replace("ollama_chat/", "")
            # Get Ollama base URL from settings (which reads from OLLAMA_API_BASE env var)
            ollama_base = settings.ollama_api_base
            base_url = f"{ollama_base}/api/chat"

            # Build conversation history
            # Start with system instructions so the model knows about DataMetronome
            messages = [{"role": "system", "content": self._get_system_instructions()}]

            if context and "history" in context:
                for msg in context["history"][-5:]:
                    messages.append(
                        {
                            "role": msg["role"],
                            "content": msg["content"],
                        }
                    )

            messages.append({"role": "user", "content": message})

            request_data = {
                "model": model_name,
                "messages": messages,
                "stream": False,
            }

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(base_url, json=request_data)
                if response.status_code != 200:
                    raise Exception(
                        f"Ollama API error: {response.status_code} - {response.text}"
                    )

                result = response.json()
                assistant_message = result.get("message", {}).get("content", "")

                return {
                    "message": assistant_message,
                    "toolCalls": None,  # Ollama doesn't support tool calling via this endpoint
                }
        else:
            # Original Gemini HTTP implementation (kept as fallback)
            raise NotImplementedError(
                "HTTP-based Gemini implementation removed. "
                "Please install google-adk: pip install google-adk"
            )
