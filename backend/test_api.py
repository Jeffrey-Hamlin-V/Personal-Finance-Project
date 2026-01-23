"""
Quick API test script
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_dashboard():
    """Test dashboard endpoint"""
    print("\n🔍 Testing dashboard...")
    response = requests.get(f"{BASE_URL}/api/dashboard?user_id=demo_user")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total spending: €{data['summary']['total_spending']:.2f}")
        print(f"✅ Insights: {len(data['insights'])}")
        print(f"✅ Anomalies: {data['anomaly_count']}")
    else:
        print(f"❌ Error: {response.text}")

def test_transactions():
    """Test transactions endpoint"""
    print("\n🔍 Testing transactions...")
    response = requests.get(f"{BASE_URL}/api/transactions?user_id=demo_user&page=1&page_size=10")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total transactions: {data['total']}")
        print(f"✅ Returned: {len(data['transactions'])}")
        
        if data['transactions']:
            txn = data['transactions'][0]
            print(f"\nSample transaction:")
            print(f"  Merchant: {txn['merchant']}")
            print(f"  Amount: €{txn['amount']}")
            print(f"  Category: {txn['category']}")
    else:
        print(f"❌ Error: {response.text}")

def test_analytics():
    """Test analytics endpoint"""
    print("\n🔍 Testing analytics...")
    response = requests.get(f"{BASE_URL}/api/analytics?user_id=demo_user")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total spent: €{data['total_spent']:.2f}")
        print(f"✅ Categories: {len(data['by_category'])}")
        print(f"\nTop 3 categories:")
        for cat in data['by_category'][:3]:
            print(f"  {cat['category']}: €{cat['total']:.2f} ({cat['pct_of_total']:.1f}%)")
    else:
        print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    print("🧪 Testing Personal Finance API")
    print("=" * 50)
    
    try:
        test_health()
        test_dashboard()
        test_transactions()
        test_analytics()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("   Make sure the server is running: uvicorn api.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")