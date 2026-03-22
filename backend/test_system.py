"""
Test script to verify the SAP O2C Graph System setup
Run this after backend is running to check all endpoints
"""

import requests
import json
import sys
from time import sleep

BASE_URL = "http://localhost:8000"

def print_status(test_name, success, message=""):
    """Print colored test status"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"   {message}")
    print()

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        success = response.status_code == 200 and response.json().get("status") == "healthy"
        print_status("Health Check", success, 
                    f"Status: {response.status_code}, Response: {response.json()}")
        return success
    except Exception as e:
        print_status("Health Check", False, str(e))
        return False

def test_graph_stats():
    """Test graph statistics endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/graph/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            message = f"Nodes: {stats.get('total_nodes')}, Edges: {stats.get('total_edges')}"
            print_status("Graph Stats", True, message)
            return True, stats
        else:
            print_status("Graph Stats", False, f"Status: {response.status_code}")
            return False, None
    except Exception as e:
        print_status("Graph Stats", False, str(e))
        return False, None

def test_graph_data():
    """Test graph data endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/graph/data", timeout=15)
        if response.status_code == 200:
            data = response.json()
            nodes = len(data.get('nodes', []))
            edges = len(data.get('edges', []))
            message = f"Retrieved {nodes} nodes and {edges} edges"
            print_status("Graph Data", True, message)
            return True
        else:
            print_status("Graph Data", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_status("Graph Data", False, str(e))
        return False

def test_query(query_text):
    """Test natural language query"""
    try:
        payload = {
            "query": query_text,
            "conversation_history": []
        }
        response = requests.post(f"{BASE_URL}/api/query", 
                                json=payload, 
                                timeout=30)
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')[:100]
            query_type = result.get('query_type', 'unknown')
            message = f"Type: {query_type}, Answer preview: {answer}..."
            print_status(f"Query: '{query_text[:50]}...'", True, message)
            return True
        else:
            print_status(f"Query: '{query_text}'", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_status(f"Query: '{query_text}'", False, str(e))
        return False

def test_search():
    """Test node search"""
    try:
        response = requests.get(f"{BASE_URL}/api/search/nodes?q=740533", timeout=10)
        if response.status_code == 200:
            results = response.json()
            count = len(results.get('nodes', []))
            message = f"Found {count} matching nodes"
            print_status("Node Search", True, message)
            return True
        else:
            print_status("Node Search", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_status("Node Search", False, str(e))
        return False

def test_broken_flows():
    """Test broken flow analysis"""
    try:
        response = requests.get(f"{BASE_URL}/api/analyze/broken-flows", timeout=20)
        if response.status_code == 200:
            result = response.json()
            summary = result.get('summary', {})
            message = (f"Orders without delivery: {summary.get('orders_without_delivery', 0)}, "
                      f"Deliveries without invoice: {summary.get('deliveries_without_invoice', 0)}")
            print_status("Broken Flow Analysis", True, message)
            return True
        else:
            print_status("Broken Flow Analysis", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_status("Broken Flow Analysis", False, str(e))
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("SAP O2C Graph System - Test Suite")
    print("=" * 60)
    print()
    
    print("Testing backend connection...")
    print()
    
    # Test 1: Health check
    if not test_health():
        print("\n❌ Backend is not responding. Please check:")
        print("   1. Backend server is running (python app.py)")
        print("   2. Server is accessible at http://localhost:8000")
        sys.exit(1)
    
    sleep(1)
    
    # Test 2: Graph statistics
    success, stats = test_graph_stats()
    if not success:
        print("\n⚠️  Graph not loaded. Please check:")
        print("   1. Dataset files exist in correct path")
        print("   2. Backend logs for errors")
        sys.exit(1)
    
    sleep(1)
    
    # Test 3: Graph data retrieval
    test_graph_data()
    sleep(1)
    
    # Test 4: Natural language queries
    print("Testing natural language queries...")
    print()
    test_query("How many sales orders are there?")
    sleep(2)
    
    test_query("Find sales orders without deliveries")
    sleep(2)
    
    # Test 5: Search functionality
    test_search()
    sleep(1)
    
    # Test 6: Broken flow analysis
    test_broken_flows()
    
    print()
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start frontend: cd frontend && npm start")
    print("2. Open browser to http://localhost:3000")
    print("3. Try the chat interface with various queries")
    print()

if __name__ == "__main__":
    main()
