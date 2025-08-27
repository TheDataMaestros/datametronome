import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from metronome_pulse_postgres import PostgresPulse
from metronome_pulse_postgres_psycopg3 import PostgresPsycopg3Pulse
from metronome_pulse_postgres_sqlalchemy import PostgresSQLAlchemyPulse

logger = logging.getLogger(__name__)

class PostgresMonitorService:
    """Service for monitoring PostgreSQL data quality and detecting anomalies."""
    
    def __init__(self, connector_type: str = "asyncpg"):
        """Initialize the monitor service.
        
        Args:
            connector_type: Type of connector to use ('asyncpg', 'psycopg3', 'sqlalchemy')
        """
        self.connector_type = connector_type
        self.connector = None
        
    async def create_connector(self, connection_config: Dict[str, Any]) -> None:
        """Create and configure the appropriate connector."""
        if self.connector_type == "asyncpg":
            self.connector = PostgresPulse(
                host=connection_config["host"],
                port=connection_config.get("port", 5432),
                database=connection_config["database"],
                user=connection_config["user"],
                password=connection_config["password"]
            )
        elif self.connector_type == "psycopg3":
            self.connector = PostgresPsycopg3Pulse(
                host=connection_config["host"],
                port=connection_config.get("port", 5432),
                database=connection_config["database"],
                user=connection_config["user"],
                password=connection_config["password"]
            )
        elif self.connector_type == "sqlalchemy":
            self.connector = PostgresSQLAlchemyPulse(
                host=connection_config["host"],
                port=connection_config.get("port", 5432),
                database=connection_config["database"],
                user=connection_config["user"],
                password=connection_config["password"]
            )
        else:
            raise ValueError(f"Unsupported connector type: {self.connector_type}")
        
        await self.connector.connect()
        logger.info(f"Connected to PostgreSQL using {self.connector_type} connector")
    
    async def close_connector(self) -> None:
        """Close the connector."""
        if self.connector:
            await self.connector.close()
            self.connector = None
    
    async def check_row_count(self, table_name: str, expected_min: int = 0) -> Dict[str, Any]:
        """Check if a table has the expected number of rows."""
        try:
            query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            results = await self.connector.query(query)
            actual_count = results[0]["row_count"] if results else 0
            
            status = "pass"
            if actual_count < expected_min:
                status = "critical" if actual_count == 0 else "warning"
            
            return {
                "table": table_name,
                "expected_min": expected_min,
                "actual_count": actual_count,
                "status": status,
                "message": f"Table {table_name} has {actual_count} rows (expected min: {expected_min})"
            }
        except Exception as e:
            logger.error(f"Error checking row count for table {table_name}: {e}")
            return {
                "table": table_name,
                "status": "error",
                "message": f"Error checking row count: {str(e)}"
            }
    
    async def check_data_freshness(self, table_name: str, timestamp_column: str, max_age_hours: int) -> Dict[str, Any]:
        """Check if the latest data in a table is fresh enough."""
        try:
            query = f"""
                SELECT MAX({timestamp_column}) as latest_timestamp 
                FROM {table_name} 
                WHERE {timestamp_column} IS NOT NULL
            """
            results = await self.connector.query(query)
            
            if not results or not results[0]["latest_timestamp"]:
                return {
                    "table": table_name,
                    "status": "warning",
                    "message": f"Table {table_name} has no timestamp data"
                }
            
            latest_timestamp = results[0]["latest_timestamp"]
            if isinstance(latest_timestamp, str):
                latest_timestamp = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
            
            age_hours = (datetime.now() - latest_timestamp).total_seconds() / 3600
            
            status = "pass"
            if age_hours > max_age_hours:
                status = "critical" if age_hours > max_age_hours * 2 else "warning"
            
            return {
                "table": table_name,
                "latest_timestamp": latest_timestamp.isoformat(),
                "age_hours": round(age_hours, 2),
                "max_age_hours": max_age_hours,
                "status": status,
                "message": f"Table {table_name} latest data is {age_hours:.1f} hours old (max: {max_age_hours})"
            }
        except Exception as e:
            logger.error(f"Error checking data freshness for table {table_name}: {e}")
            return {
                "table": table_name,
                "status": "error",
                "message": f"Error checking data freshness: {str(e)}"
            }
    
    async def check_anomalies(self, table_name: str, anomaly_checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check for data anomalies using custom SQL queries."""
        try:
            anomaly_results = []
            total_anomalies = 0
            
            for check in anomaly_checks:
                check_name = check["name"]
                sql = check["sql"]
                expected_max = check.get("expected_max", 0)
                
                results = await self.connector.query(sql)
                anomaly_count = results[0]["count"] if results else 0
                total_anomalies += anomaly_count
                
                status = "pass"
                if anomaly_count > expected_max:
                    status = "critical" if anomaly_count > expected_max * 2 else "warning"
                
                anomaly_results.append({
                    "check_name": check_name,
                    "anomaly_count": anomaly_count,
                    "expected_max": expected_max,
                    "status": status
                })
            
            overall_status = "pass"
            if total_anomalies > 0:
                overall_status = "warning" if total_anomalies < 10 else "critical"
            
            return {
                "table": table_name,
                "overall_status": overall_status,
                "total_anomalies": total_anomalies,
                "checks": anomaly_results,
                "message": f"Table {table_name} has {total_anomalies} total anomalies"
            }
        except Exception as e:
            logger.error(f"Error checking anomalies for table {table_name}: {e}")
            return {
                "table": table_name,
                "status": "error",
                "message": f"Error checking anomalies: {str(e)}"
            }
    
    async def check_schema_changes(self, table_name: str, expected_columns: List[str]) -> Dict[str, Any]:
        """Check if table schema matches expected columns."""
        try:
            # Get table info using our connector
            table_info = await self.connector.query({
                "type": "table_info",
                "table_name": table_name
            })
            
            actual_columns = [col["column_name"] for col in table_info]
            missing_columns = set(expected_columns) - set(actual_columns)
            extra_columns = set(actual_columns) - set(expected_columns)
            
            status = "pass"
            if missing_columns or extra_columns:
                status = "critical" if missing_columns else "warning"
            
            return {
                "table": table_name,
                "expected_columns": expected_columns,
                "actual_columns": actual_columns,
                "missing_columns": list(missing_columns),
                "extra_columns": list(extra_columns),
                "status": status,
                "message": f"Table {table_name} schema check: {len(missing_columns)} missing, {len(extra_columns)} extra columns"
            }
        except Exception as e:
            logger.error(f"Error checking schema for table {table_name}: {e}")
            return {
                "table": table_name,
                "status": "error",
                "message": f"Error checking schema: {str(e)}"
            }
    
    async def run_comprehensive_check(self, table_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run comprehensive data quality checks for multiple tables."""
        if not self.connector:
            raise RuntimeError("Connector not initialized. Call create_connector() first.")
        
        start_time = datetime.now()
        overall_results = {
            "check_started_at": start_time.isoformat(),
            "connector_type": self.connector_type,
            "tables_checked": len(table_configs),
            "overall_status": "pass",
            "table_results": [],
            "summary": {
                "pass": 0,
                "warning": 0,
                "critical": 0,
                "error": 0
            }
        }
        
        try:
            for table_config in table_configs:
                table_name = table_config["table_name"]
                logger.info(f"Checking table: {table_name}")
                
                table_result = {
                    "table_name": table_name,
                    "checks": [],
                    "overall_status": "pass"
                }
                
                # Row count check
                if "row_count_check" in table_config:
                    row_count_result = await self.check_row_count(
                        table_name, 
                        table_config["row_count_check"].get("expected_min", 0)
                    )
                    table_result["checks"].append(("row_count", row_count_result))
                
                # Data freshness check
                if "freshness_check" in table_config:
                    freshness_result = await self.check_data_freshness(
                        table_name,
                        table_config["freshness_check"]["timestamp_column"],
                        table_config["freshness_check"]["max_age_hours"]
                    )
                    table_result["checks"].append(("freshness", freshness_result))
                
                # Anomaly detection
                if "anomaly_checks" in table_config:
                    anomaly_result = await self.check_anomalies(
                        table_name,
                        table_config["anomaly_checks"]
                    )
                    table_result["checks"].append(("anomalies", anomaly_result))
                
                # Schema check
                if "schema_check" in table_config:
                    schema_result = await self.check_schema_changes(
                        table_name,
                        table_config["schema_check"]["expected_columns"]
                    )
                    table_result["checks"].append(("schema", schema_result))
                
                # Determine overall table status
                table_statuses = [check[1]["status"] for check in table_result["checks"]]
                if "critical" in table_statuses:
                    table_result["overall_status"] = "critical"
                elif "warning" in table_statuses:
                    table_result["overall_status"] = "warning"
                elif "error" in table_statuses:
                    table_result["overall_status"] = "error"
                
                overall_results["table_results"].append(table_result)
                overall_results["summary"][table_result["overall_status"]] += 1
            
            # Determine overall status
            if overall_results["summary"]["critical"] > 0:
                overall_results["overall_status"] = "critical"
            elif overall_results["summary"]["warning"] > 0:
                overall_results["overall_status"] = "warning"
            elif overall_results["summary"]["error"] > 0:
                overall_results["overall_status"] = "error"
            
        except Exception as e:
            logger.error(f"Error during comprehensive check: {e}")
            overall_results["overall_status"] = "error"
            overall_results["error"] = str(e)
        
        overall_results["check_completed_at"] = datetime.now().isoformat()
        overall_results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        return overall_results
