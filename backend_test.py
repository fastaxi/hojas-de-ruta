#!/usr/bin/env python3
"""
RutasFast Backend API Testing
Tests all core functionality including auth, admin, and route sheets
"""
import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class RutasFastAPITester:
    def __init__(self, base_url="https://rutasfast.preview.emergentagent.com"):
        self.base_url = base_url
        self.user_token = None
        self.admin_token = None
        self.test_user_id = None
        self.test_route_sheet_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    token: Optional[str] = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/api{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}
            
            return success, response_data

        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_health_check(self):
        """Test API health check"""
        success, data = self.make_request('GET', '/')
        self.log_test("API Health Check", success, 
                     f"Status: {data.get('status', 'unknown')}")
        return success

    def test_health_endpoint(self):
        """Test dedicated health endpoint"""
        success, data = self.make_request('GET', '/health')
        email_configured = data.get('email_configured', False)
        self.log_test("Health Endpoint", success, 
                     f"Email configured: {email_configured}")
        return success

    def test_user_registration(self):
        """Test user registration flow"""
        timestamp = datetime.now().strftime("%H%M%S")
        test_data = {
            "full_name": f"Test User {timestamp}",
            "dni_cif": f"12345678{timestamp[-1]}",
            "license_number": f"L-{timestamp}",
            "license_council": "Oviedo",
            "phone": f"612{timestamp}",
            "email": f"test{timestamp}@example.com",
            "password": "testpass123",
            "vehicle_brand": "Toyota",
            "vehicle_model": "Prius",
            "vehicle_plate": f"1234 AB{timestamp[-1]}",
            "drivers": []
        }
        
        success, data = self.make_request('POST', '/auth/register', test_data, expected_status=200)
        if success:
            self.test_user_id = data.get('user_id')
            self.test_email = test_data['email']
            self.test_password = test_data['password']
        
        self.log_test("User Registration", success, 
                     f"User ID: {self.test_user_id}" if success else data.get('detail', 'Unknown error'))
        return success

    def test_admin_login(self):
        """Test admin login with admin/admin123"""
        admin_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        success, data = self.make_request('POST', '/admin/login', admin_data, expected_status=200)
        if success:
            self.admin_token = data.get('access_token')
        
        self.log_test("Admin Login", success, 
                     f"Token received: {'Yes' if self.admin_token else 'No'}")
        return success

    def test_admin_get_pending_users(self):
        """Test admin can view pending users"""
        if not self.admin_token:
            self.log_test("Admin Get Pending Users", False, "No admin token available")
            return False
        
        success, data = self.make_request('GET', '/admin/users?status=PENDING', 
                                        token=self.admin_token)
        
        pending_count = len(data) if isinstance(data, list) else 0
        self.log_test("Admin Get Pending Users", success, 
                     f"Found {pending_count} pending users")
        return success

    def test_user_login_pending_status(self):
        """Test user login fails with PENDING status"""
        if not self.test_email:
            self.log_test("User Login (Pending)", False, "No test user available")
            return False
        
        login_data = {
            "email": self.test_email,
            "password": self.test_password
        }
        
        success, data = self.make_request('POST', '/auth/login', login_data, expected_status=403)
        expected_message = "Este usuario aun no ha sido verificado por el administrador."
        message_correct = expected_message in data.get('detail', '')
        
        overall_success = success and message_correct
        self.log_test("User Login (Pending Status)", overall_success, 
                     f"Message: {data.get('detail', 'No message')}")
        return overall_success

    def test_admin_approve_user(self):
        """Test admin can approve user"""
        if not self.admin_token or not self.test_user_id:
            self.log_test("Admin Approve User", False, "Missing admin token or user ID")
            return False
        
        success, data = self.make_request('POST', f'/admin/users/{self.test_user_id}/approve', 
                                        token=self.admin_token, expected_status=200)
        
        self.log_test("Admin Approve User", success, 
                     f"Message: {data.get('message', 'No message')}")
        return success

    def test_user_login_after_approval(self):
        """Test user login succeeds after approval"""
        if not self.test_email:
            self.log_test("User Login (After Approval)", False, "No test user available")
            return False
        
        login_data = {
            "email": self.test_email,
            "password": self.test_password
        }
        
        success, data = self.make_request('POST', '/auth/login', login_data, expected_status=200)
        if success:
            self.user_token = data.get('access_token')
        
        self.log_test("User Login (After Approval)", success, 
                     f"Token received: {'Yes' if self.user_token else 'No'}")
        return success

    def test_create_route_sheet_validation(self):
        """Test route sheet creation with validations"""
        if not self.user_token:
            self.log_test("Route Sheet Validation", False, "No user token available")
            return False
        
        # Test missing contractor info
        invalid_data = {
            "prebooked_date": "2024-12-25",
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_datetime": "2024-12-25T10:00:00Z",
            "destination": "Aeropuerto de Asturias"
        }
        
        success, data = self.make_request('POST', '/route-sheets', invalid_data, 
                                        token=self.user_token, expected_status=400)
        
        expected_error = "Debe proporcionar teléfono o email del contratante"
        error_correct = expected_error in data.get('detail', '')
        
        self.log_test("Route Sheet Validation (Missing Contractor)", success and error_correct, 
                     f"Error: {data.get('detail', 'No error message')}")
        return success and error_correct

    def test_flight_number_validation(self):
        """Test flight number validation for airport pickups"""
        if not self.user_token:
            self.log_test("Flight Number Validation", False, "No user token available")
            return False
        
        # Test missing flight number for airport pickup
        invalid_data = {
            "contractor_phone": "612345678",
            "prebooked_date": "2024-12-25",
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            "pickup_datetime": "2024-12-25T10:00:00Z",
            "destination": "Hotel Reconquista"
        }
        
        success1, data1 = self.make_request('POST', '/route-sheets', invalid_data, 
                                          token=self.user_token, expected_status=400)
        
        # Test invalid flight number format
        invalid_data["flight_number"] = "INVALID123"
        success2, data2 = self.make_request('POST', '/route-sheets', invalid_data, 
                                          token=self.user_token, expected_status=400)
        
        expected_format_error = "Formato de vuelo inválido. Ejemplo: VY1234"
        format_error_correct = expected_format_error in data2.get('detail', '')
        
        overall_success = success1 and success2 and format_error_correct
        self.log_test("Flight Number Validation", overall_success, 
                     f"Missing: {data1.get('detail', '')}, Invalid format: {data2.get('detail', '')}")
        return overall_success

    def test_create_valid_route_sheet(self):
        """Test creating a valid route sheet"""
        if not self.user_token:
            self.log_test("Create Valid Route Sheet", False, "No user token available")
            return False
        
        valid_data = {
            "contractor_phone": "612345678",
            "contractor_email": "contractor@example.com",
            "prebooked_date": "2024-12-25",
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            "flight_number": "VY1234",
            "pickup_address": "Terminal T1",
            "pickup_datetime": "2024-12-25T10:00:00Z",
            "destination": "Hotel Reconquista"
        }
        
        success, data = self.make_request('POST', '/route-sheets', valid_data, 
                                        token=self.user_token, expected_status=200)
        
        if success:
            self.test_route_sheet_id = data.get('id')
        
        self.log_test("Create Valid Route Sheet", success, 
                     f"Sheet ID: {self.test_route_sheet_id}, Number: {data.get('sheet_number', 'N/A')}")
        return success

    def test_get_route_sheets(self):
        """Test getting user's route sheets with filters"""
        if not self.user_token:
            self.log_test("Get Route Sheets", False, "No user token available")
            return False
        
        # Test basic get
        success, data = self.make_request('GET', '/route-sheets', token=self.user_token)
        
        if success and isinstance(data, dict):
            sheet_count = len(data.get('sheets', []))
            self.log_test("Get Route Sheets", success, 
                         f"Found {sheet_count} route sheets")
        else:
            self.log_test("Get Route Sheets", False, f"Unexpected response format: {data}")
            return False
        
        # Test date filtering
        from_date = "2024-01-01"
        to_date = "2024-12-31"
        success2, data2 = self.make_request('GET', f'/route-sheets?from_date={from_date}&to_date={to_date}', 
                                          token=self.user_token)
        
        if success2 and isinstance(data2, dict):
            filtered_count = len(data2.get('sheets', []))
            self.log_test("Get Route Sheets (Date Filter)", success2, 
                         f"Found {filtered_count} sheets in date range")
        else:
            self.log_test("Get Route Sheets (Date Filter)", False, f"Date filter failed: {data2}")
            return False
        
        return success and success2

    def test_annul_route_sheet(self):
        """Test annulling a route sheet"""
        if not self.user_token or not self.test_route_sheet_id:
            self.log_test("Annul Route Sheet", False, "Missing user token or route sheet ID")
            return False
        
        annul_data = {
            "reason": "Test annulment"
        }
        
        success, data = self.make_request('POST', f'/route-sheets/{self.test_route_sheet_id}/annul', 
                                        annul_data, token=self.user_token, expected_status=200)
        
        self.log_test("Annul Route Sheet", success, 
                     f"Message: {data.get('message', 'No message')}")
        
        # Test that we can't annul twice
        if success:
            success2, data2 = self.make_request('POST', f'/route-sheets/{self.test_route_sheet_id}/annul', 
                                              annul_data, token=self.user_token, expected_status=400)
            expected_error = "La hoja ya está anulada"
            error_correct = expected_error in data2.get('detail', '')
            
            self.log_test("Annul Route Sheet (Double Annul)", success2 and error_correct, 
                         f"Error: {data2.get('detail', 'No error message')}")
            return success and success2 and error_correct
        
        return success

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting RutasFast Backend API Tests")
        print("=" * 50)
        
        # Basic health checks
        self.test_health_check()
        self.test_health_endpoint()
        
        # User registration and admin approval flow
        self.test_user_registration()
        self.test_admin_login()
        self.test_admin_get_pending_users()
        self.test_user_login_pending_status()
        self.test_admin_approve_user()
        self.test_user_login_after_approval()
        
        # Route sheet functionality
        self.test_create_route_sheet_validation()
        self.test_flight_number_validation()
        self.test_create_valid_route_sheet()
        self.test_get_route_sheets()
        self.test_annul_route_sheet()
        
        # Summary
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

    def get_test_summary(self):
        """Get detailed test summary"""
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "test_results": self.test_results
        }

def main():
    tester = RutasFastAPITester()
    exit_code = tester.run_all_tests()
    
    # Save detailed results
    summary = tester.get_test_summary()
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())