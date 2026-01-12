#!/usr/bin/env python3
"""
Test with the specific approved test user from the review request
"""
import requests
import json
from datetime import datetime

def test_approved_user():
    """Test with the pre-approved test user"""
    base_url = "https://rutasfast-1.preview.emergentagent.com"
    
    # Test user credentials from review request
    login_data = {
        "email": "testuser_jan8@example.com",
        "password": "testpass123"
    }
    
    print("🔐 Testing login with approved test user...")
    
    # Test login
    response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('access_token')
        print("✅ Login successful - token received")
        
        # Test creating a route sheet
        print("📝 Testing route sheet creation...")
        
        sheet_data = {
            "contractor_phone": "612345678",
            "contractor_email": "contractor@example.com",
            "prebooked_date": "2024-12-25",
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            "flight_number": "IB1234",
            "pickup_address": "Terminal T1",
            "pickup_datetime": "2024-12-25T14:30:00Z",
            "destination": "Hotel Reconquista, Oviedo"
        }
        
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = requests.post(f"{base_url}/api/route-sheets", json=sheet_data, headers=headers)
        
        if response.status_code == 200:
            sheet_result = response.json()
            print(f"✅ Route sheet created: {sheet_result.get('sheet_number')}")
            sheet_id = sheet_result.get('id')
            
            # Test getting route sheets
            print("📋 Testing route sheet retrieval...")
            response = requests.get(f"{base_url}/api/route-sheets", headers=headers)
            
            if response.status_code == 200:
                sheets_data = response.json()
                sheet_count = len(sheets_data.get('sheets', []))
                print(f"✅ Retrieved {sheet_count} route sheets")
                
                # Test PDF generation
                print("📄 Testing PDF generation...")
                response = requests.get(f"{base_url}/api/route-sheets/{sheet_id}/pdf", headers=headers)
                
                if response.status_code == 200 and response.headers.get('content-type') == 'application/pdf':
                    print("✅ PDF generation successful")
                    
                    # Test annulling the sheet
                    print("❌ Testing route sheet annulment...")
                    annul_data = {"reason": "Test annulment"}
                    response = requests.post(f"{base_url}/api/route-sheets/{sheet_id}/annul", 
                                           json=annul_data, headers=headers)
                    
                    if response.status_code == 200:
                        print("✅ Route sheet annulled successfully")
                        return True
                    else:
                        print(f"❌ Annulment failed: {response.status_code} - {response.text}")
                else:
                    print(f"❌ PDF generation failed: {response.status_code}")
            else:
                print(f"❌ Route sheet retrieval failed: {response.status_code} - {response.text}")
        else:
            print(f"❌ Route sheet creation failed: {response.status_code} - {response.text}")
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
    
    return False

if __name__ == "__main__":
    success = test_approved_user()
    if success:
        print("\n🎉 All tests with approved user passed!")
    else:
        print("\n⚠️ Some tests failed")