"""
RutasFast - Retention Job Endpoint Tests
Tests for:
- POST /api/internal/run-retention (internal endpoint with X-Job-Token)
- GET /api/admin/retention-runs (retention history)
- GET /api/admin/retention-runs/last (last retention run)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
RETENTION_JOB_TOKEN = "rtf-retention-job-2024-secure-token-change-in-production"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


class TestInternalRetentionEndpoint:
    """Tests for POST /api/internal/run-retention"""
    
    def test_no_token_returns_401(self):
        """Without X-Job-Token header, should return 401"""
        response = requests.post(f"{BASE_URL}/api/internal/run-retention")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "X-Job-Token" in data["detail"] or "required" in data["detail"].lower()
        print("✓ No token returns 401 with proper message")
    
    def test_invalid_token_returns_403(self):
        """With incorrect X-Job-Token, should return 403"""
        response = requests.post(
            f"{BASE_URL}/api/internal/run-retention",
            headers={"X-Job-Token": "wrong-token-value"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower() or "token" in data["detail"].lower()
        print("✓ Invalid token returns 403 with proper message")
    
    def test_valid_token_executes_retention(self):
        """With correct X-Job-Token, should execute retention and return results"""
        response = requests.post(
            f"{BASE_URL}/api/internal/run-retention",
            headers={"X-Job-Token": RETENTION_JOB_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "hidden_count" in data, "Response should contain hidden_count"
        assert "purged_count" in data, "Response should contain purged_count"
        assert "duration_ms" in data, "Response should contain duration_ms"
        assert "run_at" in data, "Response should contain run_at"
        
        # Verify data types
        assert isinstance(data["hidden_count"], int), "hidden_count should be int"
        assert isinstance(data["purged_count"], int), "purged_count should be int"
        assert isinstance(data["duration_ms"], int), "duration_ms should be int"
        assert isinstance(data["run_at"], str), "run_at should be ISO string"
        
        print(f"✓ Valid token executes retention: hidden={data['hidden_count']}, purged={data['purged_count']}, duration={data['duration_ms']}ms")
        return data


class TestAdminRetentionRunsEndpoints:
    """Tests for admin retention-runs endpoints"""
    
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
    
    def test_retention_runs_requires_auth(self):
        """GET /api/admin/retention-runs requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/admin/retention-runs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ retention-runs endpoint requires authentication")
    
    def test_retention_runs_last_requires_auth(self):
        """GET /api/admin/retention-runs/last requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/admin/retention-runs/last")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ retention-runs/last endpoint requires authentication")
    
    def test_get_retention_runs_history(self, admin_token):
        """GET /api/admin/retention-runs returns list of runs"""
        response = requests.get(
            f"{BASE_URL}/api/admin/retention-runs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # If there are runs, verify structure
        if len(data) > 0:
            run = data[0]
            assert "run_at" in run, "Run should have run_at"
            assert "hidden_count" in run, "Run should have hidden_count"
            assert "purged_count" in run, "Run should have purged_count"
            assert "trigger" in run, "Run should have trigger"
            print(f"✓ Got {len(data)} retention runs from history")
        else:
            print("✓ Retention runs history is empty (no runs yet)")
        
        return data
    
    def test_get_last_retention_run(self, admin_token):
        """GET /api/admin/retention-runs/last returns most recent run"""
        response = requests.get(
            f"{BASE_URL}/api/admin/retention-runs/last",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Can be null if no runs exist
        if data is None:
            print("✓ No retention runs exist yet (null response)")
        else:
            assert "run_at" in data, "Run should have run_at"
            assert "hidden_count" in data, "Run should have hidden_count"
            assert "purged_count" in data, "Run should have purged_count"
            assert "trigger" in data, "Run should have trigger"
            print(f"✓ Last retention run: {data['run_at']}, trigger={data['trigger']}")
        
        return data


class TestRetentionRunLogging:
    """Tests to verify retention runs are properly logged"""
    
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
    
    def test_internal_run_creates_log_entry(self, admin_token):
        """Running internal retention should create a log entry"""
        # Get count before
        response_before = requests.get(
            f"{BASE_URL}/api/admin/retention-runs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        count_before = len(response_before.json()) if response_before.status_code == 200 else 0
        
        # Execute retention via internal endpoint
        run_response = requests.post(
            f"{BASE_URL}/api/internal/run-retention",
            headers={"X-Job-Token": RETENTION_JOB_TOKEN}
        )
        assert run_response.status_code == 200, f"Retention run failed: {run_response.text}"
        run_data = run_response.json()
        
        # Get count after
        response_after = requests.get(
            f"{BASE_URL}/api/admin/retention-runs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response_after.status_code == 200
        runs_after = response_after.json()
        
        # Verify new entry was created
        assert len(runs_after) > count_before, "New retention run should be logged"
        
        # Verify the latest entry matches our run
        latest_run = runs_after[0]  # Sorted by run_at desc
        assert latest_run["trigger"] == "internal", "Trigger should be 'internal'"
        assert latest_run["hidden_count"] == run_data["hidden_count"]
        assert latest_run["purged_count"] == run_data["purged_count"]
        
        print(f"✓ Internal retention run properly logged with trigger='internal'")
    
    def test_last_run_matches_most_recent(self, admin_token):
        """Last run endpoint should return the most recent run"""
        # Get all runs
        all_response = requests.get(
            f"{BASE_URL}/api/admin/retention-runs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert all_response.status_code == 200
        all_runs = all_response.json()
        
        # Get last run
        last_response = requests.get(
            f"{BASE_URL}/api/admin/retention-runs/last",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert last_response.status_code == 200
        last_run = last_response.json()
        
        if len(all_runs) > 0 and last_run:
            # Last run should match first in list (most recent)
            assert last_run["run_at"] == all_runs[0]["run_at"], "Last run should match most recent"
            print("✓ Last run endpoint returns most recent run")
        else:
            print("✓ No runs to compare (empty history)")


class TestAdminManualRetention:
    """Tests for admin manual retention endpoint (for comparison)"""
    
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
    
    def test_admin_dry_run(self, admin_token):
        """Admin can run retention in dry_run mode"""
        response = requests.post(
            f"{BASE_URL}/api/admin/run-retention?dry_run=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["dry_run"] == True, "Should be dry_run mode"
        assert "to_hide" in data, "Should show to_hide count"
        assert "to_purge" in data, "Should show to_purge count"
        assert "DRY RUN" in data["message"], "Message should indicate dry run"
        
        print(f"✓ Admin dry run: to_hide={data['to_hide']}, to_purge={data['to_purge']}")
    
    def test_admin_real_run_logs_with_admin_trigger(self, admin_token):
        """Admin real run should log with trigger='admin_manual'"""
        # Execute real run
        response = requests.post(
            f"{BASE_URL}/api/admin/run-retention?dry_run=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Get last run
        last_response = requests.get(
            f"{BASE_URL}/api/admin/retention-runs/last",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert last_response.status_code == 200
        last_run = last_response.json()
        
        assert last_run is not None, "Should have a logged run"
        assert last_run["trigger"] == "admin_manual", f"Trigger should be 'admin_manual', got {last_run['trigger']}"
        
        print(f"✓ Admin real run logged with trigger='admin_manual'")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
