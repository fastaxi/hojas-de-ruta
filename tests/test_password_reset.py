"""
RutasFast - Password Reset Feature Tests
Tests for admin manual password reset flow:
1. Admin generates temp password (72h expiry)
2. User logs in with temp password
3. User is forced to change password
4. User can access app after password change
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://driver-routes-5.preview.emergentagent.com').rstrip('/')

# Test user data - unique per test run
TEST_USER_EMAIL = f"test_reset_{uuid.uuid4().hex[:8]}@test.com"
TEST_USER_PASSWORD = "TestPass123"
TEST_USER_DATA = {
    "full_name": "Test Reset User",
    "dni_cif": "12345678A",
    "license_number": "LIC-001",
    "license_council": "Oviedo",
    "phone": "+34600000001",
    "email": TEST_USER_EMAIL,
    "password": TEST_USER_PASSWORD,
    "vehicle_brand": "Toyota",
    "vehicle_model": "Prius",
    "vehicle_plate": "1234ABC"
}

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


class TestAdminPasswordReset:
    """Test admin password reset functionality"""
    
    admin_token = None
    test_user_id = None
    temp_password = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get admin token"""
        # Admin login
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        TestAdminPasswordReset.admin_token = response.json()["access_token"]
    
    def test_01_register_test_user(self):
        """Register a test user for password reset testing"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json=TEST_USER_DATA
        )
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "user_id" in data
        TestAdminPasswordReset.test_user_id = data["user_id"]
        print(f"✓ Test user registered: {TEST_USER_EMAIL} (ID: {TestAdminPasswordReset.test_user_id})")
    
    def test_02_approve_test_user(self):
        """Admin approves the test user"""
        assert TestAdminPasswordReset.test_user_id, "No test user ID"
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TestAdminPasswordReset.test_user_id}/approve",
            headers={"Authorization": f"Bearer {TestAdminPasswordReset.admin_token}"}
        )
        assert response.status_code == 200, f"Approval failed: {response.text}"
        print(f"✓ Test user approved")
    
    def test_03_user_can_login_with_original_password(self):
        """Verify user can login with original password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data.get("must_change_password") == False, "Should not require password change yet"
        print(f"✓ User can login with original password")
    
    def test_04_admin_reset_password_temp_endpoint(self):
        """Test POST /api/admin/users/{user_id}/reset-password-temp"""
        assert TestAdminPasswordReset.test_user_id, "No test user ID"
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TestAdminPasswordReset.test_user_id}/reset-password-temp",
            headers={"Authorization": f"Bearer {TestAdminPasswordReset.admin_token}"}
        )
        assert response.status_code == 200, f"Reset password failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "temp_password" in data, "Response should contain temp_password"
        assert "expires_at" in data, "Response should contain expires_at"
        assert "expires_in_hours" in data, "Response should contain expires_in_hours"
        assert "user_email" in data, "Response should contain user_email"
        assert "user_name" in data, "Response should contain user_name"
        
        # Verify values
        assert data["expires_in_hours"] == 72, "Expiry should be 72 hours"
        assert data["user_email"] == TEST_USER_EMAIL
        assert len(data["temp_password"]) >= 14, "Temp password should be at least 14 chars"
        
        TestAdminPasswordReset.temp_password = data["temp_password"]
        print(f"✓ Temp password generated: {TestAdminPasswordReset.temp_password[:4]}...")
        print(f"  Expires at: {data['expires_at']}")
    
    def test_05_old_password_no_longer_works(self):
        """Verify original password no longer works after reset"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 401, f"Old password should not work: {response.text}"
        print(f"✓ Original password correctly rejected")
    
    def test_06_login_with_temp_password_requires_change(self):
        """Login with temp password should set must_change_password=true"""
        assert TestAdminPasswordReset.temp_password, "No temp password"
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TestAdminPasswordReset.temp_password}
        )
        assert response.status_code == 200, f"Login with temp password failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert data.get("must_change_password") == True, "Should require password change"
        assert data["user"]["must_change_password"] == True
        print(f"✓ Login with temp password works, must_change_password=True")
    
    def test_07_change_password_flow(self):
        """Test changing password after temp password login"""
        assert TestAdminPasswordReset.temp_password, "No temp password"
        
        # Login first to get access token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TestAdminPasswordReset.temp_password}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # Change password
        new_password = "NewSecurePass123"
        change_response = requests.post(
            f"{BASE_URL}/api/me/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": TestAdminPasswordReset.temp_password,
                "new_password": new_password
            }
        )
        assert change_response.status_code == 200, f"Change password failed: {change_response.text}"
        print(f"✓ Password changed successfully")
        
        # Verify can login with new password
        new_login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": new_password}
        )
        assert new_login_response.status_code == 200, f"Login with new password failed: {new_login_response.text}"
        
        data = new_login_response.json()
        assert data.get("must_change_password") == False, "Should not require password change after changing"
        print(f"✓ Login with new password works, must_change_password=False")
    
    def test_08_reset_password_requires_admin_auth(self):
        """Verify reset-password-temp requires admin authentication"""
        # Without auth
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TestAdminPasswordReset.test_user_id}/reset-password-temp"
        )
        assert response.status_code == 401, "Should require auth"
        
        # With invalid token
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TestAdminPasswordReset.test_user_id}/reset-password-temp",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401, "Should reject invalid token"
        print(f"✓ Endpoint correctly requires admin authentication")
    
    def test_09_reset_password_nonexistent_user(self):
        """Verify reset-password-temp returns 404 for nonexistent user"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/nonexistent_user_id/reset-password-temp",
            headers={"Authorization": f"Bearer {TestAdminPasswordReset.admin_token}"}
        )
        assert response.status_code == 404, f"Should return 404: {response.text}"
        print(f"✓ Correctly returns 404 for nonexistent user")


class TestPasswordValidation:
    """Test password validation rules"""
    
    def test_password_min_length(self):
        """Password must be at least 8 characters"""
        # First setup: register and approve a user, then reset password
        admin_response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        admin_token = admin_response.json()["access_token"]
        
        # Register user
        test_email = f"test_validation_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "full_name": "Validation Test",
                "dni_cif": "87654321B",
                "license_number": "LIC-VAL",
                "license_council": "Gijón",
                "phone": "+34600000002",
                "email": test_email,
                "password": "ValidPass123",
                "vehicle_brand": "Honda",
                "vehicle_model": "Civic",
                "vehicle_plate": "5678DEF"
            }
        )
        user_id = reg_response.json()["user_id"]
        
        # Approve
        requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Reset password
        reset_response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/reset-password-temp",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        temp_password = reset_response.json()["temp_password"]
        
        # Login with temp password
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_email, "password": temp_password}
        )
        access_token = login_response.json()["access_token"]
        
        # Try to change to short password
        change_response = requests.post(
            f"{BASE_URL}/api/me/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": temp_password,
                "new_password": "Short1"  # Too short
            }
        )
        assert change_response.status_code == 400, f"Should reject short password: {change_response.text}"
        assert "8 caracteres" in change_response.json().get("detail", "")
        print(f"✓ Password minimum length validation works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
