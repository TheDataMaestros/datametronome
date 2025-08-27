#!/usr/bin/env python3
"""
Performance benchmark for DataPulse SQLite connector.

This script benchmarks various operations to demonstrate
the performance characteristics of the SQLite connector.
"""

import asyncio
import tempfile
import os
import time
from pathlib import Path

from metronome_pulse_sqlite import SQLitePulse


async def benchmark_bulk_insert(pulse, table_name, record_count):
    """Benchmark bulk insert performance."""
    print(f"📊 Benchmarking bulk insert of {record_count:,} records...")
    
    # Generate test data
    records = [
        {
            "name": f"User{i}",
            "email": f"user{i}@example.com",
            "age": i % 100,
            "active": bool(i % 2),
            "score": float(i) / 100.0
        }
        for i in range(record_count)
    ]
    
    # Measure insert time
    start_time = time.time()
    await pulse.write(records, table_name)
    end_time = time.time()
    
    duration = end_time - start_time
    rate = record_count / duration
    
    print(f"   ⏱️  Duration: {duration:.2f}s")
    print(f"   🚀 Rate: {rate:,.0f} records/second")
    
    return duration, rate


async def benchmark_query_performance(pulse, table_name, record_count):
    """Benchmark query performance."""
    print(f"🔍 Benchmarking query performance on {record_count:,} records...")
    
    # Test different query types
    queries = [
        ("Simple SELECT", "SELECT * FROM users LIMIT 100"),
        ("COUNT query", "SELECT COUNT(*) as count FROM users"),
        ("WHERE clause", "SELECT * FROM users WHERE active = 1"),
        ("GROUP BY", "SELECT active, COUNT(*) as count FROM users GROUP BY active"),
        ("ORDER BY", "SELECT * FROM users ORDER BY name LIMIT 100"),
        ("Complex JOIN", """
            SELECT u.name, COUNT(e.id) as event_count
            FROM users u
            LEFT JOIN events e ON u.id = e.user_id
            GROUP BY u.id, u.name
            ORDER BY event_count DESC
            LIMIT 50
        """)
    ]
    
    results = []
    
    for query_name, sql in queries:
        try:
            start_time = time.time()
            await pulse.query(sql)
            end_time = time.time()
            
            duration = end_time - start_time
            results.append((query_name, duration))
            
            print(f"   📝 {query_name}: {duration:.4f}s")
            
        except Exception as e:
            print(f"   ❌ {query_name}: Failed - {e}")
            results.append((query_name, None))
    
    return results


async def benchmark_concurrent_operations(pulse, table_name, concurrent_count=10):
    """Benchmark concurrent read operations."""
    print(f"🔄 Benchmarking {concurrent_count} concurrent read operations...")
    
    async def concurrent_read():
        """Single concurrent read operation."""
        start_time = time.time()
        await pulse.query("SELECT * FROM users LIMIT 10")
        end_time = time.time()
        return end_time - start_time
    
    # Run concurrent operations
    start_time = time.time()
    tasks = [concurrent_read() for _ in range(concurrent_count)]
    durations = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    avg_duration = sum(durations) / len(durations)
    throughput = concurrent_count / total_time
    
    print(f"   ⏱️  Total time: {total_time:.2f}s")
    print(f"   📊 Average per operation: {avg_duration:.4f}s")
    print(f"   🚀 Throughput: {throughput:.2f} operations/second")
    
    return total_time, avg_duration, throughput


async def main():
    """Main benchmark function."""
    print("🚀 DataPulse SQLite Connector - Performance Benchmark")
    print("=" * 70)
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        print(f"📁 Using temporary database: {db_path}")
        
        # Initialize connector
        pulse = SQLitePulse(db_path)
        await pulse.connect()
        print("✅ Connected to database")
        
        # Create test tables
        await pulse.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER,
                active BOOLEAN DEFAULT 1,
                score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await pulse.execute("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        print("✅ Created test tables")
        
        # Benchmark 1: Bulk Insert Performance
        print("\n" + "="*70)
        print("🏃‍♂️ BENCHMARK 1: Bulk Insert Performance")
        print("="*70)
        
        record_counts = [1000, 5000, 10000]
        insert_results = []
        
        for count in record_counts:
            duration, rate = await benchmark_bulk_insert(pulse, "users", count)
            insert_results.append((count, duration, rate))
        
        # Benchmark 2: Query Performance
        print("\n" + "="*70)
        print("🏃‍♂️ BENCHMARK 2: Query Performance")
        print("="*70)
        
        # Ensure we have data for querying
        if not insert_results:
            await benchmark_bulk_insert(pulse, "users", 10000)
        
        query_results = await benchmark_query_performance(pulse, "users", 10000)
        
        # Benchmark 3: Concurrent Operations
        print("\n" + "="*70)
        print("🏃‍♂️ BENCHMARK 3: Concurrent Operations")
        print("="*70)
        
        concurrent_results = await benchmark_concurrent_operations(pulse, "users", 20)
        
        # Benchmark 4: Memory and Resource Usage
        print("\n" + "="*70)
        print("🏃‍♂️ BENCHMARK 4: Resource Usage")
        print("="*70)
        
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            print(f"   💾 Memory usage: {memory_info.rss / 1024 / 1024:.1f} MB")
            print(f"   🧠 Virtual memory: {memory_info.vms / 1024 / 1024:.1f} MB")
            
        except ImportError:
            print("   💾 psutil not available - skipping memory metrics")
        
        # Summary
        print("\n" + "="*70)
        print("📊 BENCHMARK SUMMARY")
        print("="*70)
        
        print("Insert Performance:")
        for count, duration, rate in insert_results:
            print(f"   {count:,} records: {duration:.2f}s ({rate:,.0f} rec/s)")
        
        print("\nQuery Performance:")
        for query_name, duration in query_results:
            if duration is not None:
                print(f"   {query_name}: {duration:.4f}s")
        
        print(f"\nConcurrent Operations:")
        print(f"   20 concurrent reads: {concurrent_results[0]:.2f}s total")
        print(f"   Average per operation: {concurrent_results[1]:.4f}s")
        print(f"   Throughput: {concurrent_results[2]:.2f} ops/s")
        
        print("\n🎉 Benchmark completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during benchmark: {e}")
        raise
    finally:
        # Cleanup
        try:
            await pulse.close()
            os.unlink(db_path)
            print(f"🧹 Cleaned up temporary database: {db_path}")
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
