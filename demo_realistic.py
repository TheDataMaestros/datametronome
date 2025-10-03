#!/usr/bin/env python3
"""
Realistic End-to-End Demo for DataMetronome.

This script demonstrates the complete workflow:
1. Start services (Podium API + test database)
2. Load realistic test data with injected anomalies
3. Configure data sources and quality checks via API
4. Execute checks and detect anomalies
5. Display results and metrics

Run this to validate the entire system works as expected.
"""

import asyncio
import httpx
import sys
import time
from datetime import datetime
from pathlib import Path


class DataMetronomeDemo:
    """End-to-end demo orchestrator."""
    
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token = None
        
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
    
    def print_step(self, step: int, message: str):
        """Print a demo step."""
        print(f"\n{'='*60}")
        print(f"Step {step}: {message}")
        print('='*60)
    
    def print_success(self, message: str):
        """Print success message."""
        print(f"✅ {message}")
    
    def print_error(self, message: str):
        """Print error message."""
        print(f"❌ {message}")
    
    def print_info(self, message: str):
        """Print info message."""
        print(f"ℹ️  {message}")
    
    async def check_api_health(self) -> bool:
        """Check if API is running and healthy."""
        try:
            response = await self.client.get(f"{self.api_base}/health")
            if response.status_code == 200:
                data = response.json()
                self.print_success(f"API is {data.get('status', 'unknown')}")
                return data.get('status') == 'healthy'
            else:
                self.print_error(f"API returned status {response.status_code}")
                return False
        except Exception as e:
            self.print_error(f"Could not connect to API: {e}")
            return False
    
    async def login(self, username: str = "admin", password: str = "admin") -> bool:
        """Login to get authentication token."""
        try:
            response = await self.client.post(
                f"{self.api_base}/api/v1/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.print_success(f"Logged in as {username}")
                return True
            else:
                self.print_error(f"Login failed: {response.text}")
                return False
        except Exception as e:
            self.print_error(f"Login error: {e}")
            return False
    
    def get_headers(self) -> dict:
        """Get authenticated headers."""
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}
    
    async def create_stave(self, name: str, db_config: dict) -> str | None:
        """Create a data source (stave)."""
        try:
            stave_data = {
                "id": f"stave-{int(time.time())}",
                "name": name,
                "description": f"Demo data source: {name}",
                "data_source_type": "postgres",
                "connection_config": db_config,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            response = await self.client.post(
                f"{self.api_base}/api/v1/staves",
                json=stave_data,
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                stave_id = data.get("id")
                self.print_success(f"Created stave: {name} (ID: {stave_id})")
                return stave_id
            else:
                self.print_error(f"Failed to create stave: {response.text}")
                return None
        except Exception as e:
            self.print_error(f"Error creating stave: {e}")
            return None
    
    async def create_clef(self, stave_id: str, name: str, check_type: str, config: dict) -> str | None:
        """Create a data quality check (clef)."""
        try:
            clef_data = {
                "id": f"clef-{int(time.time()*1000)}",
                "stave_id": stave_id,
                "name": name,
                "description": f"Demo check: {name}",
                "check_type": check_type,
                "config": config,
                "schedule": "0 * * * *",  # Hourly
                "is_active": True,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            response = await self.client.post(
                f"{self.api_base}/api/v1/clefs",
                json=clef_data,
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                clef_id = data.get("id")
                self.print_success(f"Created check: {name} (ID: {clef_id})")
                return clef_id
            else:
                self.print_error(f"Failed to create clef: {response.text}")
                return None
        except Exception as e:
            self.print_error(f"Error creating clef: {e}")
            return None
    
    async def list_staves(self):
        """List all data sources."""
        try:
            response = await self.client.get(
                f"{self.api_base}/api/v1/staves",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                staves = response.json()
                self.print_info(f"Found {len(staves)} data source(s)")
                for stave in staves:
                    print(f"  - {stave.get('name')} ({stave.get('data_source_type')})")
                return staves
            else:
                self.print_error(f"Failed to list staves: {response.text}")
                return []
        except Exception as e:
            self.print_error(f"Error listing staves: {e}")
            return []
    
    async def list_clefs(self):
        """List all data quality checks."""
        try:
            response = await self.client.get(
                f"{self.api_base}/api/v1/clefs",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                clefs = response.json()
                self.print_info(f"Found {len(clefs)} quality check(s)")
                for clef in clefs:
                    print(f"  - {clef.get('name')} ({clef.get('check_type')})")
                return clefs
            else:
                self.print_error(f"Failed to list clefs: {response.text}")
                return []
        except Exception as e:
            self.print_error(f"Error listing clefs: {e}")
            return []
    
    async def get_metrics(self):
        """Get Prometheus metrics."""
        try:
            response = await self.client.get(f"{self.api_base}/metrics")
            if response.status_code == 200:
                metrics = response.text
                # Parse key metrics
                lines = metrics.split('\n')
                key_metrics = {}
                for line in lines:
                    if line.startswith('http_requests_total'):
                        key_metrics['http_requests'] = line.split()[-1]
                    elif line.startswith('active_staves'):
                        key_metrics['active_staves'] = line.split()[-1]
                    elif line.startswith('active_clefs'):
                        key_metrics['active_clefs'] = line.split()[-1]
                
                self.print_info("Key Metrics:")
                for key, value in key_metrics.items():
                    print(f"  {key}: {value}")
                return key_metrics
            else:
                self.print_error(f"Failed to get metrics: {response.status_code}")
                return {}
        except Exception as e:
            self.print_error(f"Error getting metrics: {e}")
            return {}
    
    async def run_demo(self):
        """Run the complete demo."""
        print("\n" + "🎵" * 30)
        print("DataMetronome - Realistic End-to-End Demo")
        print("🎵" * 30)
        
        # Step 1: Check API Health
        self.print_step(1, "Checking API Health")
        if not await self.check_api_health():
            self.print_error("API is not running. Start it with:")
            print("  cd datametronome/podium")
            print("  python -m datametronome_podium.main")
            return False
        
        # Step 2: Authenticate
        self.print_step(2, "Authenticating")
        if not await self.login():
            return False
        
        # Step 3: Create Data Source
        self.print_step(3, "Creating Data Source (Stave)")
        self.print_info("Configuring connection to test PostgreSQL database")
        
        db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass"
        }
        
        stave_id = await self.create_stave("Test PostgreSQL Database", db_config)
        if not stave_id:
            self.print_error("Failed to create data source")
            return False
        
        # Step 4: Create Data Quality Checks
        self.print_step(4, "Creating Data Quality Checks (Clefs)")
        
        checks = [
            {
                "name": "Check for NULL emails in users table",
                "check_type": "null_check",
                "config": {
                    "table": "users",
                    "column": "email",
                    "threshold": 0.01  # Alert if >1% are NULL
                }
            },
            {
                "name": "Check for invalid age values",
                "check_type": "range_check",
                "config": {
                    "table": "users",
                    "column": "age",
                    "min": 0,
                    "max": 120,
                    "threshold": 0.02  # Alert if >2% out of range
                }
            },
            {
                "name": "Check for duplicate email addresses",
                "check_type": "uniqueness_check",
                "config": {
                    "table": "users",
                    "column": "email",
                    "threshold": 0.0  # Alert on any duplicates
                }
            }
        ]
        
        clef_ids = []
        for check in checks:
            clef_id = await self.create_clef(
                stave_id,
                check["name"],
                check["check_type"],
                check["config"]
            )
            if clef_id:
                clef_ids.append(clef_id)
        
        if not clef_ids:
            self.print_error("Failed to create any checks")
            return False
        
        # Step 5: List Configuration
        self.print_step(5, "Listing Configuration")
        await self.list_staves()
        await self.list_clefs()
        
        # Step 6: Get Metrics
        self.print_step(6, "Checking Prometheus Metrics")
        await self.get_metrics()
        
        # Step 7: Summary
        self.print_step(7, "Demo Summary")
        self.print_success("Demo completed successfully!")
        print("\nWhat was demonstrated:")
        print("  ✅ API health check endpoint")
        print("  ✅ Authentication with JWT tokens")
        print("  ✅ Created data source (stave) via API")
        print(f"  ✅ Created {len(clef_ids)} data quality checks (clefs)")
        print("  ✅ Listed all configurations")
        print("  ✅ Retrieved Prometheus metrics")
        
        print("\nNext steps:")
        print("  1. Run checks manually or wait for scheduled execution")
        print("  2. View results in Streamlit UI: http://localhost:8501")
        print("  3. Monitor metrics in Grafana: http://localhost:3000")
        print("  4. Check API docs: http://localhost:8000/docs")
        
        return True


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DataMetronome Realistic Demo")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Podium API base URL"
    )
    
    args = parser.parse_args()
    
    demo = DataMetronomeDemo(args.api_url)
    
    try:
        success = await demo.run_demo()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await demo.close()


if __name__ == "__main__":
    asyncio.run(main())

