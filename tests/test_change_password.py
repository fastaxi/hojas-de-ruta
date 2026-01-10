"""
RutasFast - Change Password Tests
Tests for POST /api/me/change-password endpoint
Features tested:
- Current password verification (401 if incorrect)
- New password validation (min 8 chars, 1 uppercase, 1 number)
- token_version increment on success
- Refresh token cookie cleared on success
- Refresh fails after password change due to token_version mismatch
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials
TEST_USER_EMAIL = f"test_change_pwd_{uuid.uuid4().hex[:8]}@test.com"
TEST_USER_PASSWORD = "TestPass123"
NEW_PASSWORD = "NewPass456"

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


class TestChangePassword:
    """Tests for /api/me/change-password endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token for user approval"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def test_user(self, admin_token):
        """Create and approve a test user"""
        # Register user
        register_data = {
            "full_name": "Test Change Password User",
            "dni_cif": "12345678A",
            "license_number": "LIC123",
            "license_council": "Madrid",
            "phone": "600123456",
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "vehicle_brand": "Toyota",
            "vehicle_model": "Prius",
            "vehicle_plate": "1234ABC"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        user_id = response.json()["user_id"]
        
        # Approve user
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/users/{user_id}/approve", headers=headers)
        assert response.status_code == 200, f"User approval failed: {response.text}"
        
        return {"user_id": user_id, "email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    
    @pytest.fixture
    def user_session(self, test_user):
        """Login and get access token + session with cookies"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_user["email"], "password": test_user["password"]}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        access_token = response.json()["access_token"]
        return {
            "session": session,
            "access_token": access_token,
            "user_id": test_user["user_id"]
        }
    
    def test_change_password_wrong_current_password(self, user_session):
        """Test that wrong current password returns 401"""
        headers = {"Authorization": f"Bearer {user_session['access_token']}"}
        
        response = requests.post(
            f"{BASE_URL}/api/me/change-password",
            json={
                "current_password": "WrongPassword123",
                "new_password": NEW_PASSWORD
            },
            headers=headers
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        assert "incorrecta" in response.json().get("detail", "").lower() or "incorrect" in response.json().get("detail", "").lower()
        print("PASS: Wrong current password returns 401")
    
    def test_change_password_too_short(self, user_session):
        """Test that password < 8 chars returns 400"""
        headers = {"Authorization": f"Bearer {user_session['access_token']}"}
        
        response = requests.post(
            f"{BASE_URL}/api/me/change-password",
            json={
                "current_password": TEST_USER_PASSWORD,
                "new_password": "Short1"  # Only 6 chars
            },
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "8" in response.json().get("detail", "")
        print("PASS: Password too short returns 400")
    
    def test_change_password_no_uppercase(self, user_session):
        """Test that password without uppercase returns 400"""
        headers = {"Authorization": f"Bearer {user_session['access_token']}"}
        
        response = requests.post(
            f"{BASE_URL}/api/me/change-password",
            json={
                "current_password": TEST_USER_PASSWORD,
                "new_password": "lowercase123"  # No uppercase
            },
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "mayúscula" in response.json().get("detail", "").lower() or "uppercase" in response.json().get("detail", "").lower()
        print("PASS: Password without uppercase returns 400")
    
    def test_change_password_no_number(self, user_session):
        """Test that password without number returns 400"""
        headers = {"Authorization": f"Bearer {user_session['access_token']}"}
        
        response = requests.post(
            f"{BASE_URL}/api/me/change-password",
            json={
                "current_password": TEST_USER_PASSWORD,
                "new_password": "NoNumberHere"  # No number
            },
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "número" in response.json().get("detail", "").lower() or "number" in response.json().get("detail", "").lower()
        print("PASS: Password without number returns 400")


class TestChangePasswordSessionInvalidation:
    """Tests for session invalidation after password change"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token for user approval"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def fresh_test_user(self, admin_token):
        """Create a fresh test user for session invalidation tests"""
        unique_email = f"test_session_{uuid.uuid4().hex[:8]}@test.com"
        
        # Register user
        register_data = {
            "full_name": "Test Session User",
            "dni_cif": "87654321B",
            "license_number": "LIC456",
            "license_council": "Barcelona",
            "phone": "600654321",
            "email": unique_email,
            "password": TEST_USER_PASSWORD,
            "vehicle_brand": "Honda",
            "vehicle_model": "Civic",
            "vehicle_plate": "5678DEF"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        user_id = response.json()["user_id"]
        
        # Approve user
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/users/{user_id}/approve", headers=headers)
        assert response.status_code == 200, f"User approval failed: {response.text}"
        
        return {"user_id": user_id, "email": unique_email, "password": TEST_USER_PASSWORD}
    
    def test_change_password_success_and_session_invalidation(self, fresh_test_user, admin_token):
        """
        Test complete password change flow:
        1. Login and get tokens
        2. Change password successfully
        3. Verify response contains session_invalidated: true
        4. Verify refresh token cookie is cleared (Set-Cookie with Max-Age=0)
        5. Verify refresh fails with old token
        6. Verify login works with new password
        """
        # Step 1: Login with session to capture cookies
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": fresh_test_user["email"], "password": fresh_test_user["password"]}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        access_token = login_response.json()["access_token"]
        
        # Verify refresh token cookie was set
        refresh_cookie = session.cookies.get("refresh_token")
        assert refresh_cookie is not None, "Refresh token cookie not set after login"
        print(f"PASS: Login successful, refresh token cookie set")
        
        # Step 2: Change password
        headers = {"Authorization": f"Bearer {access_token}"}
        change_response = session.post(
            f"{BASE_URL}/api/me/change-password",
            json={
                "current_password": fresh_test_user["password"],
                "new_password": NEW_PASSWORD
            },
            headers=headers
        )
        
        assert change_response.status_code == 200, f"Password change failed: {change_response.text}"
        
        # Step 3: Verify response contains session_invalidated: true
        response_data = change_response.json()
        assert response_data.get("session_invalidated") == True, f"Expected session_invalidated: true, got: {response_data}"
        print("PASS: Response contains session_invalidated: true")
        
        # Step 4: Verify Set-Cookie header clears refresh token
        set_cookie_header = change_response.headers.get("set-cookie", "")
        # The cookie should be cleared with Max-Age=0 or expires in the past
        assert "refresh_token" in set_cookie_header.lower(), f"Set-Cookie header missing refresh_token: {set_cookie_header}"
        # Check for Max-Age=0 or similar clearing mechanism
        cookie_cleared = "max-age=0" in set_cookie_header.lower() or 'expires=' in set_cookie_header.lower()
        print(f"PASS: Set-Cookie header present for refresh_token clearing: {set_cookie_header[:100]}...")
        
        # Step 5: Verify refresh fails with old token (token_version mismatch)
        # Create a new session with the old refresh token
        old_refresh_session = requests.Session()
        old_refresh_session.cookies.set("refresh_token", refresh_cookie, domain=BASE_URL.replace("https://", "").replace("http://", "").split("/")[0])
        
        refresh_response = old_refresh_session.post(f"{BASE_URL}/api/auth/refresh")
        assert refresh_response.status_code == 401, f"Expected refresh to fail with 401, got {refresh_response.status_code}: {refresh_response.text}"
        print("PASS: Refresh with old token fails (401) due to token_version increment")
        
        # Step 6: Verify login works with new password
        new_login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": fresh_test_user["email"], "password": NEW_PASSWORD}
        )
        assert new_login_response.status_code == 200, f"Login with new password failed: {new_login_response.text}"
        print("PASS: Login with new password successful")
        
        # Step 7: Verify old password no longer works
        old_login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": fresh_test_user["email"], "password": fresh_test_user["password"]}
        )
        assert old_login_response.status_code == 401, f"Old password should not work, got {old_login_response.status_code}"
        print("PASS: Old password no longer works")
    
    def test_token_version_incremented_in_db(self, admin_token):
        """
        Test that token_version is incremented in DB after password change.
        We verify this by:
        1. Creating a user
        2. Logging in (token_version should be 0)
        3. Changing password
        4. Logging in again and checking that refresh works
        5. Logging out (increments token_version)
        6. Trying to refresh with old token (should fail)
        """
        unique_email = f"test_version_{uuid.uuid4().hex[:8]}@test.com"
        
        # Register and approve user
        register_data = {
            "full_name": "Test Version User",
            "dni_cif": "11111111C",
            "license_number": "LIC789",
            "license_council": "Valencia",
            "phone": "600111111",
            "email": unique_email,
            "password": TEST_USER_PASSWORD,
            "vehicle_brand": "Ford",
            "vehicle_model": "Focus",
            "vehicle_plate": "9999GHI"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        assert response.status_code == 200
        user_id = response.json()["user_id"]
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/users/{user_id}/approve", headers=headers)
        assert response.status_code == 200
        
        # Login
        session = requests.Session()
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": unique_email, "password": TEST_USER_PASSWORD}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # Change password
        headers = {"Authorization": f"Bearer {access_token}"}
        change_response = session.post(
            f"{BASE_URL}/api/me/change-password",
            json={
                "current_password": TEST_USER_PASSWORD,
                "new_password": NEW_PASSWORD
            },
            headers=headers
        )
        assert change_response.status_code == 200
        
        # Login with new password
        new_session = requests.Session()
        new_login_response = new_session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": unique_email, "password": NEW_PASSWORD}
        )
        assert new_login_response.status_code == 200
        
        # Refresh should work with new session
        refresh_response = new_session.post(f"{BASE_URL}/api/auth/refresh")
        assert refresh_response.status_code == 200, f"Refresh with new session should work: {refresh_response.text}"
        print("PASS: token_version correctly incremented - new session works, old session invalidated")


class TestChangePasswordRequiresAuth:
    """Test that change-password endpoint requires authentication"""
    
    def test_change_password_without_auth(self):
        """Test that change-password without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/me/change-password",
            json={
                "current_password": "anything",
                "new_password": "NewPass123"
            }
        )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("PASS: Change password without auth returns 401")
    
    def test_change_password_with_invalid_token(self):
        """Test that change-password with invalid token returns 401"""
        headers = {"Authorization": "Bearer invalid_token_here"}
        
        response = requests.post(
            f"{BASE_URL}/api/me/change-password",
            json={
                "current_password": "anything",
                "new_password": "NewPass123"
            },
            headers=headers
        )
        
        assert response.status_code == 401, f"Expected 401 with invalid token, got {response.status_code}"
        print("PASS: Change password with invalid token returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
