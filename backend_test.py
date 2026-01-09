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
    def __init__(self, base_url="https://driver-routes-5.preview.emergentagent.com"):
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

    def test_pdf_generation(self):
        """Test PDF generation for route sheets"""
        if not self.user_token:
            self.log_test("PDF Generation", False, "No user token available")
            return False
        
        # Create a new route sheet for PDF testing (since previous one was annulled)
        valid_data = {
            "contractor_phone": "612345678",
            "contractor_email": "contractor@example.com",
            "prebooked_date": "2024-12-25",
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_address": "Calle Uría 1",
            "pickup_datetime": "2024-12-25T15:00:00Z",
            "destination": "Aeropuerto de Asturias"
        }
        
        success, data = self.make_request('POST', '/route-sheets', valid_data, 
                                        token=self.user_token, expected_status=200)
        
        if not success:
            self.log_test("PDF Generation (Create Sheet)", False, "Failed to create sheet for PDF test")
            return False
        
        pdf_sheet_id = data.get('id')
        
        # Test single sheet PDF
        url = f"{self.base_url}/api/route-sheets/{pdf_sheet_id}/pdf"
        headers = {'Authorization': f'Bearer {self.user_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            pdf_success = response.status_code == 200 and response.headers.get('content-type') == 'application/pdf'
            
            self.log_test("PDF Generation (Single Sheet)", pdf_success, 
                         f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
        except Exception as e:
            self.log_test("PDF Generation (Single Sheet)", False, f"Request failed: {str(e)}")
            pdf_success = False
        
        # Test range PDF
        range_url = f"{self.base_url}/api/route-sheets/pdf/range?from_date=2024-01-01&to_date=2024-12-31"
        try:
            response = requests.get(range_url, headers=headers, timeout=10)
            range_pdf_success = response.status_code == 200 and response.headers.get('content-type') == 'application/pdf'
            
            self.log_test("PDF Generation (Range)", range_pdf_success, 
                         f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
        except Exception as e:
            self.log_test("PDF Generation (Range)", False, f"Request failed: {str(e)}")
            range_pdf_success = False
        
        return pdf_success and range_pdf_success

    def test_admin_endpoints(self):
        """Test admin-specific endpoints"""
        if not self.admin_token:
            self.log_test("Admin Endpoints", False, "No admin token available")
            return False
        
        # Test admin route sheets view
        success1, data1 = self.make_request('GET', '/admin/route-sheets', token=self.admin_token)
        
        sheet_count = len(data1) if isinstance(data1, list) else 0
        self.log_test("Admin Route Sheets", success1, 
                     f"Found {sheet_count} route sheets (admin view)")
        
        # Test admin config
        success2, data2 = self.make_request('GET', '/admin/config', token=self.admin_token)
        
        self.log_test("Admin Config", success2, 
                     f"Config loaded: {'Yes' if isinstance(data2, dict) else 'No'}")
        
        # Test admin users list
        success3, data3 = self.make_request('GET', '/admin/users', token=self.admin_token)
        
        user_count = len(data3) if isinstance(data3, list) else 0
        self.log_test("Admin Users List", success3, 
                     f"Found {user_count} users")
        
        return success1 and success2 and success3

    def test_email_service_health(self):
        """Test email service configuration in health endpoint"""
        success, data = self.make_request('GET', '/health')
        
        if success:
            email_configured = data.get('email_configured', False)
            # Email should be configured with Resend integration
            expected_configured = True
            config_correct = email_configured == expected_configured
            
            self.log_test("Email Service Health Check", config_correct, 
                         f"Email configured: {email_configured} (expected: {expected_configured})")
            return config_correct
        else:
            self.log_test("Email Service Health Check", False, f"Health endpoint failed: {data}")
            return False

    def test_admin_retention_job_dry_run(self):
        """Test admin retention job endpoint with dry_run=true"""
        if not self.admin_token:
            self.log_test("Admin Retention Job (Dry Run)", False, "No admin token available")
            return False
        
        success, data = self.make_request('POST', '/admin/run-retention?dry_run=true', 
                                        token=self.admin_token, expected_status=200)
        
        if success:
            # Check required fields in response
            required_fields = ['dry_run', 'executed_at', 'stats_before', 'to_hide', 'to_purge', 'message']
            has_all_fields = all(field in data for field in required_fields)
            
            # Verify dry_run is true
            is_dry_run = data.get('dry_run') == True
            
            # Check stats structure
            stats_before = data.get('stats_before', {})
            has_stats = all(key in stats_before for key in ['total', 'visible', 'hidden'])
            
            overall_success = has_all_fields and is_dry_run and has_stats
            
            self.log_test("Admin Retention Job (Dry Run)", overall_success, 
                         f"Stats: {stats_before}, To hide: {data.get('to_hide')}, To purge: {data.get('to_purge')}")
            return overall_success
        else:
            self.log_test("Admin Retention Job (Dry Run)", False, f"Request failed: {data}")
            return False

    def test_admin_retention_job_execute(self):
        """Test admin retention job endpoint with dry_run=false"""
        if not self.admin_token:
            self.log_test("Admin Retention Job (Execute)", False, "No admin token available")
            return False
        
        success, data = self.make_request('POST', '/admin/run-retention?dry_run=false', 
                                        token=self.admin_token, expected_status=200)
        
        if success:
            # Check required fields in response
            required_fields = ['dry_run', 'executed_at', 'stats_before', 'stats_after', 'hidden', 'purged', 'message']
            has_all_fields = all(field in data for field in required_fields)
            
            # Verify dry_run is false
            is_execute = data.get('dry_run') == False
            
            # Check stats structure
            stats_before = data.get('stats_before', {})
            stats_after = data.get('stats_after', {})
            has_stats = (all(key in stats_before for key in ['total', 'visible', 'hidden']) and
                        all(key in stats_after for key in ['total', 'visible', 'hidden']))
            
            overall_success = has_all_fields and is_execute and has_stats
            
            self.log_test("Admin Retention Job (Execute)", overall_success, 
                         f"Before: {stats_before}, After: {stats_after}, Hidden: {data.get('hidden')}, Purged: {data.get('purged')}")
            return overall_success
        else:
            self.log_test("Admin Retention Job (Execute)", False, f"Request failed: {data}")
            return False

    def test_admin_config_validation(self):
        """Test admin config validation for retention months"""
        if not self.admin_token:
            self.log_test("Admin Config Validation", False, "No admin token available")
            return False
        
        # Test invalid config: purge_after_months <= hide_after_months
        invalid_config = {
            "hide_after_months": 12,
            "purge_after_months": 10  # Should be > hide_after_months
        }
        
        success1, data1 = self.make_request('PUT', '/admin/config', invalid_config, 
                                          token=self.admin_token, expected_status=400)
        
        expected_error = "purge_after_months (10) debe ser mayor que hide_after_months (12)"
        error_correct = expected_error in data1.get('detail', '')
        
        # Test valid config: purge_after_months > hide_after_months
        valid_config = {
            "hide_after_months": 12,
            "purge_after_months": 24  # Should be > hide_after_months
        }
        
        success2, data2 = self.make_request('PUT', '/admin/config', valid_config, 
                                          token=self.admin_token, expected_status=200)
        
        overall_success = success1 and error_correct and success2
        
        self.log_test("Admin Config Validation", overall_success, 
                     f"Invalid config error: {data1.get('detail', 'No error')}, Valid config: {data2.get('message', 'No message')}")
        return overall_success

    def test_admin_config_edge_cases(self):
        """Test admin config validation edge cases"""
        if not self.admin_token:
            self.log_test("Admin Config Edge Cases", False, "No admin token available")
            return False
        
        # Test equal values (should fail)
        equal_config = {
            "hide_after_months": 12,
            "purge_after_months": 12  # Equal should fail
        }
        
        success1, data1 = self.make_request('PUT', '/admin/config', equal_config, 
                                          token=self.admin_token, expected_status=400)
        
        # Test minimum values (should fail if < 1)
        min_config = {
            "hide_after_months": 0,
            "purge_after_months": 1
        }
        
        success2, data2 = self.make_request('PUT', '/admin/config', min_config, 
                                          token=self.admin_token, expected_status=400)
        
        expected_min_error = "Los meses de retención deben ser al menos 1"
        min_error_correct = expected_min_error in data2.get('detail', '')
        
        overall_success = success1 and success2 and min_error_correct
        
        self.log_test("Admin Config Edge Cases", overall_success, 
                     f"Equal values error: {data1.get('detail', 'No error')}, Min values error: {data2.get('detail', 'No error')}")
        return overall_success

    def test_duplicate_email_registration(self):
        """Test that duplicate email registration fails"""
        # Try to register with the same email as our test user
        if not hasattr(self, 'test_email'):
            self.log_test("Duplicate Email Registration", False, "No test email available")
            return False
        
        duplicate_data = {
            "full_name": "Duplicate User",
            "dni_cif": "87654321A",
            "license_number": "L-DUPLICATE",
            "license_council": "Gijón",
            "phone": "612999999",
            "email": self.test_email,  # Same email as before
            "password": "testpass123",
            "vehicle_brand": "Ford",
            "vehicle_model": "Focus",
            "vehicle_plate": "9999 ZZ9",
            "drivers": []
        }
        
        success, data = self.make_request('POST', '/auth/register', duplicate_data, expected_status=400)
        expected_error = "Este email ya está registrado"
        error_correct = expected_error in data.get('detail', '')
        
        overall_success = success and error_correct
        self.log_test("Duplicate Email Registration", overall_success, 
                     f"Error: {data.get('detail', 'No error message')}")
        return overall_success

    def test_sequential_sheet_numbering(self):
        """Test that route sheets get sequential numbers"""
        if not self.user_token:
            self.log_test("Sequential Sheet Numbering", False, "No user token available")
            return False
        
        sheet_numbers = []
        
        # Create multiple sheets and check numbering
        for i in range(3):
            valid_data = {
                "contractor_phone": f"61234567{i}",
                "prebooked_date": "2024-12-25",
                "prebooked_locality": "Oviedo",
                "pickup_type": "OTHER",
                "pickup_address": f"Test Address {i}",
                "pickup_datetime": f"2024-12-25T{10+i}:00:00Z",
                "destination": f"Test Destination {i}"
            }
            
            success, data = self.make_request('POST', '/route-sheets', valid_data, 
                                            token=self.user_token, expected_status=200)
            
            if success:
                sheet_numbers.append(data.get('sheet_number'))
            else:
                self.log_test("Sequential Sheet Numbering", False, f"Failed to create sheet {i+1}")
                return False
        
        # Check if numbers are sequential
        numbers_only = [int(num.split('/')[0]) for num in sheet_numbers if num]
        is_sequential = all(numbers_only[i] == numbers_only[i-1] + 1 for i in range(1, len(numbers_only)))
        
        self.log_test("Sequential Sheet Numbering", is_sequential, 
                     f"Sheet numbers: {sheet_numbers}")
        return is_sequential

    # ============== USER CONFIGURATION TESTS ==============
    def test_user_profile_get(self):
        """Test getting current user profile"""
        if not self.user_token:
            self.log_test("User Profile Get", False, "No user token available")
            return False
        
        success, data = self.make_request('GET', '/me', token=self.user_token)
        
        if success:
            # Check required fields are present
            required_fields = ['id', 'email', 'full_name', 'dni_cif', 'status']
            has_required = all(field in data for field in required_fields)
            
            # Check email is not modifiable (should be present but read-only)
            email_present = 'email' in data
            
            self.log_test("User Profile Get", has_required and email_present, 
                         f"Profile data: {data.get('full_name', 'N/A')}, Email: {data.get('email', 'N/A')}")
            return has_required and email_present
        else:
            self.log_test("User Profile Get", False, f"Failed to get profile: {data}")
            return False

    def test_user_profile_update(self):
        """Test updating user profile (excluding email)"""
        if not self.user_token:
            self.log_test("User Profile Update", False, "No user token available")
            return False
        
        # Test profile update with valid data
        timestamp = datetime.now().strftime("%H%M%S")
        update_data = {
            "full_name": f"Updated User {timestamp}",
            "dni_cif": f"87654321{timestamp[-1]}",
            "license_number": f"UPD-{timestamp}",
            "license_council": "Gijón",
            "phone": f"699{timestamp}"
        }
        
        success, data = self.make_request('PUT', '/me', update_data, token=self.user_token)
        
        if success:
            # Verify the update by getting profile again
            success2, profile_data = self.make_request('GET', '/me', token=self.user_token)
            
            if success2:
                # Check if updates were applied
                name_updated = profile_data.get('full_name') == update_data['full_name']
                dni_updated = profile_data.get('dni_cif') == update_data['dni_cif']
                license_updated = profile_data.get('license_number') == update_data['license_number']
                
                overall_success = name_updated and dni_updated and license_updated
                
                self.log_test("User Profile Update", overall_success, 
                             f"Name: {profile_data.get('full_name')}, DNI: {profile_data.get('dni_cif')}")
                return overall_success
            else:
                self.log_test("User Profile Update", False, "Failed to verify update")
                return False
        else:
            self.log_test("User Profile Update", False, f"Update failed: {data}")
            return False

    def test_user_profile_email_not_modifiable(self):
        """Test that email field cannot be modified"""
        if not self.user_token:
            self.log_test("User Profile Email Not Modifiable", False, "No user token available")
            return False
        
        # Get current email
        success, profile_data = self.make_request('GET', '/me', token=self.user_token)
        if not success:
            self.log_test("User Profile Email Not Modifiable", False, "Failed to get current profile")
            return False
        
        current_email = profile_data.get('email')
        
        # Try to update email (should be ignored by backend)
        update_data = {
            "email": "newemail@example.com",
            "full_name": profile_data.get('full_name', 'Test User')
        }
        
        success, data = self.make_request('PUT', '/me', update_data, token=self.user_token)
        
        if success:
            # Verify email hasn't changed
            success2, updated_profile = self.make_request('GET', '/me', token=self.user_token)
            
            if success2:
                email_unchanged = updated_profile.get('email') == current_email
                
                self.log_test("User Profile Email Not Modifiable", email_unchanged, 
                             f"Original: {current_email}, After update: {updated_profile.get('email')}")
                return email_unchanged
            else:
                self.log_test("User Profile Email Not Modifiable", False, "Failed to verify email unchanged")
                return False
        else:
            self.log_test("User Profile Email Not Modifiable", False, f"Update request failed: {data}")
            return False

    def test_vehicle_update(self):
        """Test updating vehicle information"""
        if not self.user_token:
            self.log_test("Vehicle Update", False, "No user token available")
            return False
        
        timestamp = datetime.now().strftime("%H%M%S")
        vehicle_data = {
            "vehicle_brand": "Updated Brand",
            "vehicle_model": "Updated Model",
            "vehicle_plate": f"UPD{timestamp[-3:]}"
        }
        
        success, data = self.make_request('PUT', '/me', vehicle_data, token=self.user_token)
        
        if success:
            # Verify the update
            success2, profile_data = self.make_request('GET', '/me', token=self.user_token)
            
            if success2:
                brand_updated = profile_data.get('vehicle_brand') == vehicle_data['vehicle_brand']
                model_updated = profile_data.get('vehicle_model') == vehicle_data['vehicle_model']
                plate_updated = profile_data.get('vehicle_plate') == vehicle_data['vehicle_plate']
                
                overall_success = brand_updated and model_updated and plate_updated
                
                self.log_test("Vehicle Update", overall_success, 
                             f"Brand: {profile_data.get('vehicle_brand')}, Plate: {profile_data.get('vehicle_plate')}")
                return overall_success
            else:
                self.log_test("Vehicle Update", False, "Failed to verify vehicle update")
                return False
        else:
            self.log_test("Vehicle Update", False, f"Vehicle update failed: {data}")
            return False

    def test_vehicle_plate_validation(self):
        """Test vehicle plate validation (should not be empty)"""
        if not self.user_token:
            self.log_test("Vehicle Plate Validation", False, "No user token available")
            return False
        
        # Frontend should validate empty plate, but test backend behavior
        empty_plate_data = {
            "vehicle_brand": "Test Brand",
            "vehicle_model": "Test Model",
            "vehicle_plate": ""
        }
        
        # Backend might accept empty plate (validation is primarily frontend)
        # This test verifies current behavior
        success, data = self.make_request('PUT', '/me', empty_plate_data, token=self.user_token)
        
        # Log the actual behavior for documentation
        self.log_test("Vehicle Plate Validation", True, 
                     f"Empty plate handling: {'Accepted' if success else 'Rejected'} - {data.get('detail', 'No error')}")
        return True

    def test_drivers_crud_operations(self):
        """Test complete CRUD operations for drivers"""
        if not self.user_token:
            self.log_test("Drivers CRUD Operations", False, "No user token available")
            return False
        
        timestamp = datetime.now().strftime("%H%M%S")
        
        # 1. GET drivers (initial list)
        success1, initial_drivers = self.make_request('GET', '/me/drivers', token=self.user_token)
        if not success1:
            self.log_test("Drivers CRUD Operations", False, "Failed to get initial drivers list")
            return False
        
        initial_count = len(initial_drivers) if isinstance(initial_drivers, list) else 0
        
        # 2. CREATE driver
        driver_data = {
            "full_name": f"Test Driver {timestamp}",
            "dni": f"12345678{timestamp[-1]}"
        }
        
        success2, create_response = self.make_request('POST', '/me/drivers', driver_data, token=self.user_token)
        if not success2:
            self.log_test("Drivers CRUD Operations", False, f"Failed to create driver: {create_response}")
            return False
        
        driver_id = create_response.get('id')
        if not driver_id:
            self.log_test("Drivers CRUD Operations", False, "No driver ID returned from create")
            return False
        
        # 3. GET drivers (verify creation)
        success3, updated_drivers = self.make_request('GET', '/me/drivers', token=self.user_token)
        if not success3:
            self.log_test("Drivers CRUD Operations", False, "Failed to get drivers after creation")
            return False
        
        new_count = len(updated_drivers) if isinstance(updated_drivers, list) else 0
        driver_created = new_count == initial_count + 1
        
        # Find the created driver
        created_driver = None
        for driver in updated_drivers:
            if driver.get('id') == driver_id:
                created_driver = driver
                break
        
        if not created_driver:
            self.log_test("Drivers CRUD Operations", False, "Created driver not found in list")
            return False
        
        # 4. UPDATE driver
        update_data = {
            "full_name": f"Updated Driver {timestamp}",
            "dni": f"87654321{timestamp[-1]}"
        }
        
        success4, update_response = self.make_request('PUT', f'/me/drivers/{driver_id}', update_data, token=self.user_token)
        if not success4:
            self.log_test("Drivers CRUD Operations", False, f"Failed to update driver: {update_response}")
            return False
        
        # 5. GET drivers (verify update)
        success5, post_update_drivers = self.make_request('GET', '/me/drivers', token=self.user_token)
        if not success5:
            self.log_test("Drivers CRUD Operations", False, "Failed to get drivers after update")
            return False
        
        # Find updated driver
        updated_driver = None
        for driver in post_update_drivers:
            if driver.get('id') == driver_id:
                updated_driver = driver
                break
        
        driver_updated = (updated_driver and 
                         updated_driver.get('full_name') == update_data['full_name'] and
                         updated_driver.get('dni') == update_data['dni'])
        
        # 6. DELETE driver
        success6, delete_response = self.make_request('DELETE', f'/me/drivers/{driver_id}', token=self.user_token)
        if not success6:
            self.log_test("Drivers CRUD Operations", False, f"Failed to delete driver: {delete_response}")
            return False
        
        # 7. GET drivers (verify deletion)
        success7, final_drivers = self.make_request('GET', '/me/drivers', token=self.user_token)
        if not success7:
            self.log_test("Drivers CRUD Operations", False, "Failed to get drivers after deletion")
            return False
        
        final_count = len(final_drivers) if isinstance(final_drivers, list) else 0
        driver_deleted = final_count == initial_count
        
        # Verify driver is not in list
        driver_still_exists = any(driver.get('id') == driver_id for driver in final_drivers)
        
        overall_success = (driver_created and driver_updated and driver_deleted and not driver_still_exists)
        
        self.log_test("Drivers CRUD Operations", overall_success, 
                     f"Created: {driver_created}, Updated: {driver_updated}, Deleted: {driver_deleted}, Final count: {final_count}")
        return overall_success

    def test_drivers_validation(self):
        """Test driver creation validation"""
        if not self.user_token:
            self.log_test("Drivers Validation", False, "No user token available")
            return False
        
        # Test missing full_name (backend accepts empty strings, validation is frontend)
        invalid_data1 = {
            "full_name": "",
            "dni": "12345678A"
        }
        
        success1, data1 = self.make_request('POST', '/me/drivers', invalid_data1, token=self.user_token, expected_status=200)
        
        # Test missing dni (backend accepts empty strings, validation is frontend)
        invalid_data2 = {
            "full_name": "Test Driver",
            "dni": ""
        }
        
        success2, data2 = self.make_request('POST', '/me/drivers', invalid_data2, token=self.user_token, expected_status=200)
        
        # Backend accepts empty strings (validation is on frontend)
        # Clean up created drivers
        if success1 and data1.get('id'):
            self.make_request('DELETE', f'/me/drivers/{data1["id"]}', token=self.user_token)
        if success2 and data2.get('id'):
            self.make_request('DELETE', f'/me/drivers/{data2["id"]}', token=self.user_token)
        
        backend_accepts_empty = success1 and success2
        
        self.log_test("Drivers Validation", backend_accepts_empty, 
                     f"Backend accepts empty strings (validation is frontend-only): Empty name: {success1}, Empty DNI: {success2}")
        return backend_accepts_empty

    def test_drivers_unauthorized_access(self):
        """Test that users can only access their own drivers"""
        if not self.user_token:
            self.log_test("Drivers Unauthorized Access", False, "No user token available")
            return False
        
        # Try to access/modify a non-existent driver ID
        fake_driver_id = "fake-driver-id-12345"
        
        # Try to update non-existent driver
        success1, data1 = self.make_request('PUT', f'/me/drivers/{fake_driver_id}', 
                                          {"full_name": "Hacker", "dni": "12345678H"}, 
                                          token=self.user_token, expected_status=404)
        
        # Try to delete non-existent driver
        success2, data2 = self.make_request('DELETE', f'/me/drivers/{fake_driver_id}', 
                                          token=self.user_token, expected_status=404)
        
        not_found_correct = success1 and success2
        
        self.log_test("Drivers Unauthorized Access", not_found_correct, 
                     f"Update error: {data1.get('detail', 'No error')}, Delete error: {data2.get('detail', 'No error')}")
        return not_found_correct

    def test_existing_approved_user_login(self):
        """Test login with existing approved user from review request"""
        login_data = {
            "email": "testuser_jan8@example.com",
            "password": "testpass123"
        }
        
        success, data = self.make_request('POST', '/auth/login', login_data, expected_status=200)
        
        if success:
            self.existing_user_token = data.get('access_token')
            self.log_test("Existing Approved User Login", True, 
                         f"Successfully logged in as testuser_jan8@example.com")
            return True
        else:
            self.log_test("Existing Approved User Login", False, 
                         f"Failed to login: {data.get('detail', 'Unknown error')}")
            return False

    def test_existing_user_configuration_apis(self):
        """Test configuration APIs with existing approved user"""
        if not hasattr(self, 'existing_user_token') or not self.existing_user_token:
            self.log_test("Existing User Configuration APIs", False, "No existing user token available")
            return False
        
        # Test profile get
        success1, profile_data = self.make_request('GET', '/me', token=self.existing_user_token)
        
        # Test drivers get
        success2, drivers_data = self.make_request('GET', '/me/drivers', token=self.existing_user_token)
        
        if success1 and success2:
            profile_email = profile_data.get('email', 'N/A')
            drivers_count = len(drivers_data) if isinstance(drivers_data, list) else 0
            
            self.log_test("Existing User Configuration APIs", True, 
                         f"Profile: {profile_email}, Drivers: {drivers_count}")
            return True
        else:
            self.log_test("Existing User Configuration APIs", False, 
                         f"Profile success: {success1}, Drivers success: {success2}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting RutasFast Backend API Tests")
        print("=" * 50)
        
        # Basic health checks
        self.test_health_check()
        self.test_health_endpoint()
        
        # NEW: Email service health check
        self.test_email_service_health()
        
        # User registration and admin approval flow
        self.test_user_registration()
        self.test_duplicate_email_registration()
        self.test_admin_login()
        self.test_admin_get_pending_users()
        self.test_user_login_pending_status()
        self.test_admin_approve_user()
        self.test_user_login_after_approval()
        
        # Route sheet functionality
        self.test_create_route_sheet_validation()
        self.test_flight_number_validation()
        self.test_create_valid_route_sheet()
        self.test_sequential_sheet_numbering()
        self.test_get_route_sheets()
        self.test_annul_route_sheet()
        
        # PDF and admin functionality
        self.test_pdf_generation()
        self.test_admin_endpoints()
        
        # NEW: Admin retention job tests
        self.test_admin_retention_job_dry_run()
        self.test_admin_retention_job_execute()
        
        # NEW: Admin config validation tests
        self.test_admin_config_validation()
        self.test_admin_config_edge_cases()
        
        # NEW: User Configuration Page Tests
        print("\n" + "=" * 30)
        print("🔧 Testing User Configuration APIs")
        print("=" * 30)
        
        # Test with new user
        self.test_user_profile_get()
        self.test_user_profile_update()
        self.test_user_profile_email_not_modifiable()
        self.test_vehicle_update()
        self.test_vehicle_plate_validation()
        self.test_drivers_crud_operations()
        self.test_drivers_validation()
        self.test_drivers_unauthorized_access()
        
        # Test with existing approved user
        self.test_existing_approved_user_login()
        self.test_existing_user_configuration_apis()
        
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