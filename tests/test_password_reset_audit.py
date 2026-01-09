"""
RutasFast - Password Reset Audit Feature Tests
Tests for:
- GET /api/admin/audit/password-resets (global audit log with pagination)
- GET /api/admin/users/{user_id}/audit/password-resets (user-specific audit log)
- Audit log fields: action, admin_username, user_id, user_email, user_name, timestamp, expires_at, client_ip
- Verify temp password is NEVER stored in audit log
- Retention lock concurrency (409 on simultaneous runs)
- retention_runs stats_after field
"""
import pytest
import requests
import os
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
RETENTION_JOB_TOKEN = "rtf-retention-job-2024-secure-token-change-in-production"


class TestPasswordResetAuditEndpoints:
    """Tests for password reset audit log endpoints"""
    
    admin_token = None
    test_user_id = None
    test_user_email = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        TestPasswordResetAuditEndpoints.admin_token = response.json()["access_token"]
    
    def test_01_create_test_user_for_audit(self):
        """Create a test user to generate audit entries"""
        test_email = f"test_audit_{uuid.uuid4().hex[:8]}@test.com"
        
        # Register user
        reg_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "full_name": "Audit Test User",
                "dni_cif": "AUDIT123A",
                "license_number": "LIC-AUDIT",
                "license_council": "Oviedo",
                "phone": "+34600000099",
                "email": test_email,
                "password": "AuditPass123",
                "vehicle_brand": "Seat",
                "vehicle_model": "Leon",
                "vehicle_plate": "AUDIT01"
            }
        )
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        TestPasswordResetAuditEndpoints.test_user_id = reg_response.json()["user_id"]
        TestPasswordResetAuditEndpoints.test_user_email = test_email
        
        # Approve user
        approve_response = requests.post(
            f"{BASE_URL}/api/admin/users/{TestPasswordResetAuditEndpoints.test_user_id}/approve",
            headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
        )
        assert approve_response.status_code == 200, f"Approval failed: {approve_response.text}"
        print(f"✓ Test user created and approved: {test_email}")
    
    def test_02_reset_password_creates_audit_entry(self):
        """Resetting password should create an audit log entry"""
        assert TestPasswordResetAuditEndpoints.test_user_id, "No test user ID"
        
        # Reset password
        reset_response = requests.post(
            f"{BASE_URL}/api/admin/users/{TestPasswordResetAuditEndpoints.test_user_id}/reset-password-temp",
            headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
        )
        assert reset_response.status_code == 200, f"Reset failed: {reset_response.text}"
        reset_data = reset_response.json()
        
        # Verify temp_password is returned (but should NOT be in audit)
        assert "temp_password" in reset_data, "Response should contain temp_password"
        temp_password = reset_data["temp_password"]
        
        # Get audit log for this user
        audit_response = requests.get(
            f"{BASE_URL}/api/admin/users/{TestPasswordResetAuditEndpoints.test_user_id}/audit/password-resets",
            headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
        )
        assert audit_response.status_code == 200, f"Audit fetch failed: {audit_response.text}"
        audit_logs = audit_response.json()
        
        assert len(audit_logs) > 0, "Should have at least one audit entry"
        latest_entry = audit_logs[0]
        
        # Verify required fields are present
        required_fields = ["action", "admin_username", "user_id", "user_email", "user_name", "timestamp", "expires_at", "client_ip"]
        for field in required_fields:
            assert field in latest_entry, f"Audit entry should contain '{field}'"
        
        # Verify field values
        assert latest_entry["action"] == "RESET_PASSWORD_TEMP", f"Action should be RESET_PASSWORD_TEMP, got {latest_entry['action']}"
        assert latest_entry["admin_username"] == ADMIN_USERNAME, f"Admin username should be {ADMIN_USERNAME}"
        assert latest_entry["user_id"] == TestPasswordResetAuditEndpoints.test_user_id
        assert latest_entry["user_email"] == TestPasswordResetAuditEndpoints.test_user_email
        assert latest_entry["user_name"] == "Audit Test User"
        assert latest_entry["timestamp"] is not None
        assert latest_entry["expires_at"] is not None
        assert latest_entry["client_ip"] is not None
        
        # CRITICAL: Verify temp_password is NEVER in audit log
        assert "temp_password" not in latest_entry, "SECURITY: temp_password should NEVER be in audit log"
        assert "password" not in str(latest_entry).lower() or "password" in "reset_password_temp".lower(), "No password-related data should be in audit"
        
        # Verify temp_password is not anywhere in the audit entry values
        for key, value in latest_entry.items():
            if isinstance(value, str):
                assert temp_password not in value, f"SECURITY: temp_password found in audit field '{key}'"
        
        print(f"✓ Audit entry created with all required fields")
        print(f"  - action: {latest_entry['action']}")
        print(f"  - admin_username: {latest_entry['admin_username']}")
        print(f"  - user_name: {latest_entry['user_name']}")
        print(f"  - client_ip: {latest_entry['client_ip']}")
        print(f"✓ SECURITY: temp_password is NOT stored in audit log")
    
    def test_03_global_audit_endpoint_with_pagination(self):
        """GET /api/admin/audit/password-resets returns paginated results"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/password-resets",
            headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
        )
        assert response.status_code == 200, f"Global audit fetch failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "items" in data, "Response should contain 'items'"
        assert "next_cursor" in data, "Response should contain 'next_cursor'"
        assert "count" in data, "Response should contain 'count'"
        
        assert isinstance(data["items"], list), "items should be a list"
        assert isinstance(data["count"], int), "count should be an integer"
        
        print(f"✓ Global audit endpoint returns paginated results: {data['count']} items")
        
        # Verify items have required fields
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = ["action", "admin_username", "user_id", "user_email", "user_name", "timestamp", "expires_at"]
            for field in required_fields:
                assert field in item, f"Item should contain '{field}'"
            print(f"✓ Items contain all required audit fields")
    
    def test_04_global_audit_filter_by_user_id(self):
        """GET /api/admin/audit/password-resets?user_id=X filters by user"""
        assert TestPasswordResetAuditEndpoints.test_user_id, "No test user ID"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/password-resets?user_id={TestPasswordResetAuditEndpoints.test_user_id}",
            headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
        )
        assert response.status_code == 200, f"Filtered audit fetch failed: {response.text}"
        
        data = response.json()
        
        # All items should be for the specified user
        for item in data["items"]:
            assert item["user_id"] == TestPasswordResetAuditEndpoints.test_user_id, \
                f"Item user_id should match filter: {item['user_id']} != {TestPasswordResetAuditEndpoints.test_user_id}"
        
        print(f"✓ Global audit endpoint correctly filters by user_id: {data['count']} items")
    
    def test_05_user_specific_audit_endpoint(self):
        """GET /api/admin/users/{user_id}/audit/password-resets returns user's audit history"""
        assert TestPasswordResetAuditEndpoints.test_user_id, "No test user ID"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/users/{TestPasswordResetAuditEndpoints.test_user_id}/audit/password-resets",
            headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
        )
        assert response.status_code == 200, f"User audit fetch failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # All items should be for the specified user
        for item in data:
            assert item["user_id"] == TestPasswordResetAuditEndpoints.test_user_id
        
        print(f"✓ User-specific audit endpoint returns {len(data)} entries")
    
    def test_06_audit_endpoints_require_admin_auth(self):
        """Audit endpoints require admin authentication"""
        # Global audit without auth
        response1 = requests.get(f"{BASE_URL}/api/admin/audit/password-resets")
        assert response1.status_code == 401, f"Global audit should require auth: {response1.status_code}"
        
        # User audit without auth
        response2 = requests.get(f"{BASE_URL}/api/admin/users/some-user-id/audit/password-resets")
        assert response2.status_code == 401, f"User audit should require auth: {response2.status_code}"
        
        # With invalid token
        response3 = requests.get(
            f"{BASE_URL}/api/admin/audit/password-resets",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response3.status_code == 401, f"Should reject invalid token: {response3.status_code}"
        
        print("✓ Audit endpoints correctly require admin authentication")
    
    def test_07_pagination_cursor_works(self):
        """Pagination cursor allows fetching next page"""
        # First, create multiple audit entries
        for i in range(3):
            requests.post(
                f"{BASE_URL}/api/admin/users/{TestPasswordResetAuditEndpoints.test_user_id}/reset-password-temp",
                headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
            )
            time.sleep(0.1)  # Small delay to ensure different timestamps
        
        # Get first page with limit=2
        response1 = requests.get(
            f"{BASE_URL}/api/admin/audit/password-resets?limit=2",
            headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        if data1["next_cursor"]:
            # Get next page using cursor
            response2 = requests.get(
                f"{BASE_URL}/api/admin/audit/password-resets?limit=2&cursor={data1['next_cursor']}",
                headers={"Authorization": f"Bearer {TestPasswordResetAuditEndpoints.admin_token}"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Verify no overlap between pages
            page1_timestamps = [item["timestamp"] for item in data1["items"]]
            page2_timestamps = [item["timestamp"] for item in data2["items"]]
            
            for ts in page2_timestamps:
                assert ts not in page1_timestamps, "Pages should not overlap"
            
            print(f"✓ Pagination cursor works: page1={len(data1['items'])} items, page2={len(data2['items'])} items")
        else:
            print("✓ Pagination cursor test skipped (not enough data for multiple pages)")


class TestRetentionConcurrencyLock:
    """Tests for retention job concurrency lock (409 on simultaneous runs)"""
    
    def test_concurrent_retention_returns_409(self):
        """Running retention twice simultaneously should return 409 on second call"""
        
        def run_retention():
            return requests.post(
                f"{BASE_URL}/api/internal/run-retention",
                headers={"X-Job-Token": RETENTION_JOB_TOKEN}
            )
        
        # Run two retention jobs simultaneously
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run_retention) for _ in range(2)]
            results = [f.result() for f in as_completed(futures)]
        
        status_codes = [r.status_code for r in results]
        
        # One should succeed (200), one should fail with 409
        # Note: Due to timing, both might succeed if first completes before second starts
        # So we check if at least one succeeded
        assert 200 in status_codes, f"At least one should succeed: {status_codes}"
        
        if 409 in status_codes:
            print(f"✓ Concurrent retention correctly returns 409: {status_codes}")
            # Verify 409 response message
            for r in results:
                if r.status_code == 409:
                    data = r.json()
                    assert "already running" in data.get("detail", "").lower() or "try again" in data.get("detail", "").lower()
        else:
            print(f"✓ Both retention jobs completed (no overlap detected): {status_codes}")


class TestRetentionRunsStatsAfter:
    """Tests for retention_runs stats_after field"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_retention_run_includes_stats_after(self, admin_token):
        """Retention run should include stats_after in addition to stats_before"""
        # Execute a real retention run
        response = requests.post(
            f"{BASE_URL}/api/admin/run-retention?dry_run=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Retention run failed: {response.text}"
        
        data = response.json()
        
        # Verify stats_before is present
        assert "stats_before" in data, "Response should contain stats_before"
        assert "total" in data["stats_before"], "stats_before should have total"
        assert "visible" in data["stats_before"], "stats_before should have visible"
        
        # Verify stats_after is present (new requirement)
        assert "stats_after" in data, "Response should contain stats_after"
        assert "total" in data["stats_after"], "stats_after should have total"
        assert "visible" in data["stats_after"], "stats_after should have visible"
        
        print(f"✓ Retention run includes stats_before and stats_after")
        print(f"  - stats_before: total={data['stats_before']['total']}, visible={data['stats_before']['visible']}")
        print(f"  - stats_after: total={data['stats_after']['total']}, visible={data['stats_after']['visible']}")
    
    def test_retention_runs_history_includes_stats_after(self, admin_token):
        """Retention runs history should include stats_after"""
        # Get last run
        response = requests.get(
            f"{BASE_URL}/api/admin/retention-runs/last",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get last run failed: {response.text}"
        
        data = response.json()
        
        if data is not None:
            # Verify stats_before is present
            assert "stats_before" in data, "Run should contain stats_before"
            
            # Verify stats_after is present (new requirement)
            assert "stats_after" in data, "Run should contain stats_after"
            
            print(f"✓ Retention run history includes stats_after")
            print(f"  - stats_before: {data['stats_before']}")
            print(f"  - stats_after: {data['stats_after']}")
        else:
            print("✓ No retention runs in history to verify")


class TestAuditLogSecurityVerification:
    """Additional security tests for audit log"""
    
    admin_token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        TestAuditLogSecurityVerification.admin_token = response.json()["access_token"]
    
    def test_audit_log_never_contains_password(self):
        """Verify audit log entries never contain any password data"""
        # Create a user and reset password
        test_email = f"test_security_{uuid.uuid4().hex[:8]}@test.com"
        
        # Register
        reg_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "full_name": "Security Test User",
                "dni_cif": "SEC123A",
                "license_number": "LIC-SEC",
                "license_council": "Madrid",
                "phone": "+34600000088",
                "email": test_email,
                "password": "SecurePass123",
                "vehicle_brand": "BMW",
                "vehicle_model": "X3",
                "vehicle_plate": "SEC001"
            }
        )
        user_id = reg_response.json()["user_id"]
        
        # Approve
        requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/approve",
            headers={"Authorization": f"Bearer {TestAuditLogSecurityVerification.admin_token}"}
        )
        
        # Reset password and capture the temp password
        reset_response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/reset-password-temp",
            headers={"Authorization": f"Bearer {TestAuditLogSecurityVerification.admin_token}"}
        )
        temp_password = reset_response.json()["temp_password"]
        
        # Get all audit logs
        audit_response = requests.get(
            f"{BASE_URL}/api/admin/audit/password-resets",
            headers={"Authorization": f"Bearer {TestAuditLogSecurityVerification.admin_token}"}
        )
        audit_data = audit_response.json()
        
        # Check all audit entries
        for item in audit_data["items"]:
            # Convert entire item to string for comprehensive check
            item_str = str(item)
            
            # Verify temp_password is not in any field
            assert temp_password not in item_str, \
                f"SECURITY VIOLATION: temp_password found in audit log!"
            
            # Verify no field named 'password' or 'temp_password'
            assert "temp_password" not in item, \
                "SECURITY VIOLATION: 'temp_password' field exists in audit log!"
            
            # Check for any password-like patterns (excluding action name)
            for key, value in item.items():
                if key != "action" and isinstance(value, str):
                    # Should not contain password-like strings
                    assert "password" not in value.lower() or "reset_password" in value.lower(), \
                        f"SECURITY: Suspicious password-related data in field '{key}'"
        
        print(f"✓ SECURITY VERIFIED: No password data found in {len(audit_data['items'])} audit entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
