#!/usr/bin/env python3
"""
Test admin functionality with provided admin credentials
"""
import requests
import json

def test_admin_functionality():
    """Test admin endpoints with provided credentials"""
    base_url = "https://rutas-staging.preview.emergentagent.com"
    
    # Admin credentials from review request
    admin_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("🔐 Testing admin login...")
    
    # Test admin login
    response = requests.post(f"{base_url}/api/admin/login", json=admin_data)
    
    if response.status_code == 200:
        data = response.json()
        admin_token = data.get('access_token')
        print("✅ Admin login successful")
        
        headers = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}
        
        # Test getting pending users
        print("👥 Testing pending users retrieval...")
        response = requests.get(f"{base_url}/api/admin/users?status=PENDING", headers=headers)
        
        if response.status_code == 200:
            pending_users = response.json()
            print(f"✅ Found {len(pending_users)} pending users")
            
            # Test getting all users
            print("👥 Testing all users retrieval...")
            response = requests.get(f"{base_url}/api/admin/users", headers=headers)
            
            if response.status_code == 200:
                all_users = response.json()
                print(f"✅ Found {len(all_users)} total users")
                
                # Test getting admin route sheets view
                print("📋 Testing admin route sheets view...")
                response = requests.get(f"{base_url}/api/admin/route-sheets", headers=headers)
                
                if response.status_code == 200:
                    admin_sheets = response.json()
                    print(f"✅ Admin can view {len(admin_sheets)} route sheets")
                    
                    # Test getting app configuration
                    print("⚙️ Testing app configuration...")
                    response = requests.get(f"{base_url}/api/admin/config", headers=headers)
                    
                    if response.status_code == 200:
                        config = response.json()
                        print("✅ App configuration retrieved successfully")
                        print(f"   - Hide after months: {config.get('hide_after_months', 'N/A')}")
                        print(f"   - Purge after months: {config.get('purge_after_months', 'N/A')}")
                        return True
                    else:
                        print(f"❌ Config retrieval failed: {response.status_code}")
                else:
                    print(f"❌ Admin route sheets failed: {response.status_code}")
            else:
                print(f"❌ All users retrieval failed: {response.status_code}")
        else:
            print(f"❌ Pending users retrieval failed: {response.status_code}")
    else:
        print(f"❌ Admin login failed: {response.status_code} - {response.text}")
    
    return False

if __name__ == "__main__":
    success = test_admin_functionality()
    if success:
        print("\n🎉 All admin tests passed!")
    else:
        print("\n⚠️ Some admin tests failed")