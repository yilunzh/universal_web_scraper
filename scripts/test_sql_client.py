#!/usr/bin/env python
"""
Test script for SQL Client functionality.

This script tests the execution of various SQL queries using the
exec_sql function in Supabase. It verifies that different types of
queries work as expected and provides diagnostic information.

Usage:
    python scripts/test_sql_client.py [test_name]

Arguments:
    test_name: (Optional) Run only the specified test.
               Options: simple, aggregate, changan, complex, all

Requirements:
    - python-dotenv
    - httpx
    - Python 3.8+
"""

import os
import sys
import asyncio
import time
from dotenv import load_dotenv
import httpx
import json

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the SQL client
from src.db.sql_client import execute_sql_query
from src.db.supabase_client import get_supabase_client

# Load environment variables
load_dotenv()
load_dotenv('.env.local')

async def test_direct_query():
    """Test direct database query without using exec_sql function"""
    print("\n=== Initializing Supabase Client ===")
    supabase = get_supabase_client()
    
    # Test with a simple direct table query
    try:
        response = supabase.table('china_auto_sales').select('*').limit(1).execute()
        if response:
            print("✓ Supabase client created")
            print("✓ Test query successful")
        return True
    except Exception as e:
        print(f"Error initializing Supabase client: {str(e)}")
        return False

async def setup():
    """Set up the testing environment"""
    print("Initializing Supabase client...")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: Missing Supabase credentials")
        return False
        
    print(f"URL: {supabase_url}")
    print(f"Key length: {len(supabase_key) if supabase_key else 0}")
    
    # We'll skip the creation step since the function should already exist
    print("Skipping exec_sql function creation as it's already created in Supabase.")
    return True

async def test_simple_query():
    """Test a simple query to retrieve records from the china_auto_sales table"""
    print("\n=== Testing Simple Query ===")
    query = "SELECT * FROM china_auto_sales LIMIT 5"
    
    data, columns, error = await execute_sql_query(query)
    
    if error:
        print(f"Error: {error}")
        return False
    
    print(f"Retrieved {len(data)} records with {len(columns)} columns")
    if len(data) > 0:
        print("Sample record:")
        print(json.dumps(data[0], indent=2, ensure_ascii=False))
    
    return len(data) > 0

async def test_aggregate_query():
    """Test an aggregate query that counts records and sums total units sold by manufacturer"""
    print("\n=== Testing Aggregate Query ===")
    query = "SELECT manufacturer_name, COUNT(*) as record_count, SUM(total_units_sold) as total_sales FROM china_auto_sales GROUP BY manufacturer_name ORDER BY total_sales DESC LIMIT 10"
    
    data, columns, error = await execute_sql_query(query)
    
    if error:
        print(f"Error: {error}")
        return False
    
    print(f"Retrieved {len(data)} manufacturers")
    if len(data) > 0:
        print("Top manufacturers by sales:")
        for idx, record in enumerate(data[:5], 1):
            print(f"{idx}. {record['manufacturer_name']}: {record['total_sales']:,} units ({record['record_count']} records)")
    
    return len(data) > 0

async def test_sum_by_manufacturer():
    """Test a specific query to sum units sold for Chang'an in 2021"""
    print("\n=== Testing Sum by Manufacturer ===")
    query = "SELECT SUM(total_units_sold) AS annual_total FROM china_auto_sales WHERE manufacturer_name = '长安汽车' AND year = 2021"
    
    data, columns, error = await execute_sql_query(query)
    
    if error:
        print(f"Error: {error}")
        return False
    
    print(f"Retrieved {len(data)} records")
    if len(data) > 0:
        annual_total = data[0].get('annual_total')
        print(f"Chang'an (长安汽车) 2021 annual sales: {annual_total:,} units")
    
    return len(data) > 0

async def test_complex_query():
    """Test a more complex query involving subqueries and window functions"""
    print("\n=== Testing Complex Query ===")
    query = """SELECT manufacturer_name, annual_total, peak_month_sales, sales_rank FROM (
SELECT manufacturer_name, annual_total, peak_month_sales, RANK() OVER (ORDER BY annual_total DESC) as sales_rank FROM (
SELECT manufacturer_name, SUM(monthly_total) as annual_total, MAX(monthly_total) as peak_month_sales FROM (
SELECT manufacturer_name, year, month, SUM(total_units_sold) as monthly_total FROM china_auto_sales 
WHERE year = 2021 GROUP BY manufacturer_name, year, month) as monthly_sales
GROUP BY manufacturer_name) as manufacturer_totals) as ranked_manufacturers
WHERE sales_rank <= 5 ORDER BY sales_rank"""
    
    data, columns, error = await execute_sql_query(query)
    
    if error:
        print(f"Error: {error}")
        return False
    
    print(f"Retrieved {len(data)} manufacturers")
    if len(data) > 0:
        print("Top 5 manufacturers by 2021 sales:")
        for record in data:
            print(f"{record['sales_rank']}. {record['manufacturer_name']}: {record['annual_total']:,} units (peak: {record['peak_month_sales']:,})")
    
    return len(data) > 0

async def main():
    """Main function to run all tests or a specific test"""
    # Check if a specific test was requested
    test_name = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    
    # Make sure the environment is set up
    if not await test_direct_query():
        print("❌ Failed to initialize Supabase client. Please check your credentials.")
        return
    
    if not await setup():
        print("❌ Failed to set up testing environment.")
        return
    
    # Initialize test results
    test_results = {}
    
    # Run the requested tests
    if test_name in ["simple", "all"]:
        test_results["simple"] = await test_simple_query()
    
    if test_name in ["aggregate", "all"]:
        test_results["aggregate"] = await test_aggregate_query()
    
    if test_name in ["changan", "all"]:
        test_results["changan"] = await test_sum_by_manufacturer()
    
    if test_name in ["complex", "all"]:
        test_results["complex"] = await test_complex_query()
    
    # Print a summary of the test results
    print("\n=== Test Summary ===")
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    print(f"Tests passed: {passed}/{total}")
    
    for name, result in test_results.items():
        status = "✓" if result else "❌"
        print(f"{status} {name}")
    
    if passed == total:
        print("\n✓ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed. Please check the error messages.")

if __name__ == "__main__":
    asyncio.run(main()) 