"""
Test PDF Rate Limiting, Caching, and Config Version Features

Tests:
1. Rate limit PDF individual: 30 requests/10min -> 429 on 31st
2. Rate limit PDF range: 10 requests/10min -> 429 on 11th
3. PDF cache: first download X-Cache: MISS, second X-Cache: HIT
4. pdf_config_version exists in app_config (default 1)
5. PUT /api/admin/config increments pdf_config_version only if header_* or legend_text changes
6. PUT /api/admin/config does NOT increment pdf_config_version if only hide_after_months changes
7. Cache invalidation: changing pdf_config_version makes next PDF MISS
8. Headers: Content-Type application/pdf, Content-Disposition attachment, X-Content-Type-Options nosniff
"""
import pytest
import requests
import os
import time
from datetime import datetime, date

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://asturia-taxi.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


class TestSetup:
    """Setup fixtures and helper methods"""
    
    @staticmethod
    def get_admin_token():
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @staticmethod
    def create_test_user(suffix=""):
        """Create and approve a test user, return access token"""
        timestamp = int(time.time())
        email = f"test_pdf_{timestamp}{suffix}@test.com"
        
        # Register user
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": f"Test PDF User {timestamp}",
            "dni_cif": f"TEST{timestamp}",
            "license_number": f"LIC{timestamp}",
            "license_council": "Test Council",
            "phone": f"+34600{timestamp % 1000000:06d}",
            "email": email,
            "password": "TestPass123",
            "vehicle_brand": "Test Brand",
            "vehicle_model": "Test Model",
            "vehicle_plate": f"TEST{timestamp % 10000:04d}"
        })
        
        if register_response.status_code != 200:
            print(f"Register failed: {register_response.text}")
            return None, None
        
        user_id = register_response.json().get("user_id")
        
        # Approve user with admin
        admin_token = TestSetup.get_admin_token()
        if not admin_token:
            print("Failed to get admin token")
            return None, None
        
        approve_response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if approve_response.status_code != 200:
            print(f"Approve failed: {approve_response.text}")
            return None, None
        
        # Login to get access token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": "TestPass123"
        })
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.text}")
            return None, None
        
        access_token = login_response.json().get("access_token")
        return user_id, access_token
    
    @staticmethod
    def create_route_sheet(access_token):
        """Create a route sheet for testing PDF generation"""
        tomorrow = date.today().isoformat()
        pickup_datetime = f"{tomorrow}T10:00:00"
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "contractor_phone": "+34600123456",
                "prebooked_date": tomorrow,
                "prebooked_locality": "Test City",
                "pickup_type": "OTHER",
                "pickup_address": "Test Address 123",
                "pickup_datetime": pickup_datetime,
                "destination": "Test Destination"
            }
        )
        
        if response.status_code == 200:
            return response.json().get("id")
        print(f"Create route sheet failed: {response.text}")
        return None


class TestPdfConfigVersion:
    """Test pdf_config_version in app_config"""
    
    def test_pdf_config_version_exists(self):
        """Test that pdf_config_version exists in app_config (default 1)"""
        admin_token = TestSetup.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Get config failed: {response.text}"
        config = response.json()
        
        assert "pdf_config_version" in config, "pdf_config_version not found in config"
        assert isinstance(config["pdf_config_version"], int), "pdf_config_version should be int"
        assert config["pdf_config_version"] >= 1, "pdf_config_version should be >= 1"
        print(f"✓ pdf_config_version exists: {config['pdf_config_version']}")
    
    def test_config_update_header_increments_version(self):
        """Test that updating header_* fields increments pdf_config_version"""
        admin_token = TestSetup.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        # Get current config
        response = requests.get(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        initial_version = response.json().get("pdf_config_version", 1)
        
        # Update header_title (should increment version)
        timestamp = int(time.time())
        update_response = requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"header_title": f"HOJA DE RUTA TEST {timestamp}"}
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        # Check version incremented
        response = requests.get(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        new_version = response.json().get("pdf_config_version", 1)
        
        assert new_version == initial_version + 1, f"Version should increment: {initial_version} -> {new_version}"
        print(f"✓ header_title update incremented version: {initial_version} -> {new_version}")
        
        # Restore original header_title
        requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"header_title": "HOJA DE RUTA"}
        )
    
    def test_config_update_legend_increments_version(self):
        """Test that updating legend_text increments pdf_config_version"""
        admin_token = TestSetup.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        # Get current config
        response = requests.get(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        initial_version = response.json().get("pdf_config_version", 1)
        original_legend = response.json().get("legend_text")
        
        # Update legend_text (should increment version)
        timestamp = int(time.time())
        update_response = requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"legend_text": f"Test legend text {timestamp}"}
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        # Check version incremented
        response = requests.get(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        new_version = response.json().get("pdf_config_version", 1)
        
        assert new_version == initial_version + 1, f"Version should increment: {initial_version} -> {new_version}"
        print(f"✓ legend_text update incremented version: {initial_version} -> {new_version}")
        
        # Restore original legend_text
        if original_legend:
            requests.put(
                f"{BASE_URL}/api/admin/config",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"legend_text": original_legend}
            )
    
    def test_config_update_hide_months_no_version_increment(self):
        """Test that updating hide_after_months does NOT increment pdf_config_version"""
        admin_token = TestSetup.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        # Get current config
        response = requests.get(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        config = response.json()
        initial_version = config.get("pdf_config_version", 1)
        original_hide = config.get("hide_after_months", 14)
        
        # Update hide_after_months (should NOT increment version)
        new_hide = 15 if original_hide != 15 else 13
        update_response = requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"hide_after_months": new_hide}
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        # Check version NOT incremented
        response = requests.get(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        new_version = response.json().get("pdf_config_version", 1)
        
        assert new_version == initial_version, f"Version should NOT change: {initial_version} -> {new_version}"
        print(f"✓ hide_after_months update did NOT increment version: {initial_version} (unchanged)")
        
        # Restore original hide_after_months
        requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"hide_after_months": original_hide}
        )


class TestPdfHeaders:
    """Test PDF response headers"""
    
    def test_pdf_headers_correct(self):
        """Test PDF has correct headers: Content-Type, Content-Disposition, X-Content-Type-Options"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_headers")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Get PDF
        response = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200, f"PDF request failed: {response.text}"
        
        # Check headers
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Content-Type should be application/pdf, got: {content_type}"
        
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, f"Content-Disposition should contain 'attachment', got: {content_disposition}"
        
        x_content_type_options = response.headers.get("X-Content-Type-Options", "")
        assert x_content_type_options == "nosniff", f"X-Content-Type-Options should be 'nosniff', got: {x_content_type_options}"
        
        x_cache = response.headers.get("X-Cache", "")
        assert x_cache in ["HIT", "MISS"], f"X-Cache should be HIT or MISS, got: {x_cache}"
        
        print(f"✓ PDF headers correct: Content-Type={content_type}, Content-Disposition={content_disposition[:30]}..., X-Content-Type-Options={x_content_type_options}, X-Cache={x_cache}")


class TestPdfCache:
    """Test PDF caching with X-Cache header"""
    
    def test_pdf_cache_miss_then_hit(self):
        """Test first PDF download is MISS, second is HIT"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_cache")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # First request - should be MISS
        response1 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response1.status_code == 200, f"First PDF request failed: {response1.text}"
        x_cache_1 = response1.headers.get("X-Cache", "")
        assert x_cache_1 == "MISS", f"First request should be MISS, got: {x_cache_1}"
        print(f"✓ First PDF request: X-Cache={x_cache_1}")
        
        # Second request - should be HIT
        response2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response2.status_code == 200, f"Second PDF request failed: {response2.text}"
        x_cache_2 = response2.headers.get("X-Cache", "")
        assert x_cache_2 == "HIT", f"Second request should be HIT, got: {x_cache_2}"
        print(f"✓ Second PDF request: X-Cache={x_cache_2}")
    
    def test_cache_invalidation_on_config_change(self):
        """Test that changing pdf_config_version invalidates cache (next PDF is MISS)"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_invalidate")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # First request - populate cache
        response1 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response1.status_code == 200
        print(f"✓ Initial PDF request: X-Cache={response1.headers.get('X-Cache')}")
        
        # Second request - should be HIT
        response2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response2.status_code == 200
        assert response2.headers.get("X-Cache") == "HIT", "Second request should be HIT"
        print(f"✓ Second PDF request (before config change): X-Cache={response2.headers.get('X-Cache')}")
        
        # Change config to increment pdf_config_version
        admin_token = TestSetup.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        timestamp = int(time.time())
        update_response = requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"header_title": f"HOJA DE RUTA INVALIDATE {timestamp}"}
        )
        assert update_response.status_code == 200
        print(f"✓ Config updated (pdf_config_version incremented)")
        
        # Third request - should be MISS (cache invalidated due to version change)
        response3 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response3.status_code == 200
        x_cache_3 = response3.headers.get("X-Cache", "")
        assert x_cache_3 == "MISS", f"After config change, request should be MISS, got: {x_cache_3}"
        print(f"✓ Third PDF request (after config change): X-Cache={x_cache_3}")
        
        # Restore original header_title
        requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"header_title": "HOJA DE RUTA"}
        )


class TestPdfRateLimitIndividual:
    """Test PDF individual rate limiting: 30 requests/10min"""
    
    def test_rate_limit_individual_allows_30(self):
        """Test that 30 individual PDF requests are allowed"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_rate30")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Make 30 requests - all should succeed
        success_count = 0
        for i in range(30):
            response = requests.get(
                f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"Request {i+1} failed with status {response.status_code}")
                break
        
        assert success_count == 30, f"Expected 30 successful requests, got {success_count}"
        print(f"✓ 30 individual PDF requests succeeded")
    
    def test_rate_limit_individual_blocks_31st(self):
        """Test that 31st individual PDF request returns 429"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_rate31")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Make 30 requests first
        for i in range(30):
            response = requests.get(
                f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert response.status_code == 200, f"Request {i+1} should succeed"
        
        print(f"✓ First 30 requests succeeded")
        
        # 31st request should be blocked with 429
        response_31 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response_31.status_code == 429, f"31st request should return 429, got {response_31.status_code}"
        
        # Check error message
        error_detail = response_31.json().get("detail", "")
        assert "30" in error_detail, f"Error should mention limit of 30: {error_detail}"
        assert "10" in error_detail, f"Error should mention 10 minutes: {error_detail}"
        
        print(f"✓ 31st request blocked with 429: {error_detail}")


class TestPdfRateLimitRange:
    """Test PDF range rate limiting: 10 requests/10min"""
    
    def test_rate_limit_range_allows_10(self):
        """Test that 10 range PDF requests are allowed"""
        # Create test user
        user_id, access_token = TestSetup.create_test_user("_range10")
        assert access_token, "Failed to create test user"
        
        # Create a route sheet so there's data
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        today = date.today().isoformat()
        
        # Make 10 requests - all should succeed (or 404 if no sheets in range, but not 429)
        success_count = 0
        for i in range(10):
            response = requests.get(
                f"{BASE_URL}/api/route-sheets/pdf/range",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"from_date": today, "to_date": today}
            )
            if response.status_code in [200, 404]:  # 404 is ok if no sheets in range
                success_count += 1
            elif response.status_code == 429:
                print(f"Request {i+1} rate limited with 429")
                break
            else:
                print(f"Request {i+1} failed with status {response.status_code}: {response.text}")
        
        assert success_count == 10, f"Expected 10 successful requests, got {success_count}"
        print(f"✓ 10 range PDF requests succeeded (or 404 for no data)")
    
    def test_rate_limit_range_blocks_11th(self):
        """Test that 11th range PDF request returns 429"""
        # Create test user
        user_id, access_token = TestSetup.create_test_user("_range11")
        assert access_token, "Failed to create test user"
        
        # Create a route sheet so there's data
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        today = date.today().isoformat()
        
        # Make 10 requests first
        for i in range(10):
            response = requests.get(
                f"{BASE_URL}/api/route-sheets/pdf/range",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"from_date": today, "to_date": today}
            )
            assert response.status_code in [200, 404], f"Request {i+1} should succeed or 404"
        
        print(f"✓ First 10 range requests succeeded")
        
        # 11th request should be blocked with 429
        response_11 = requests.get(
            f"{BASE_URL}/api/route-sheets/pdf/range",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"from_date": today, "to_date": today}
        )
        
        assert response_11.status_code == 429, f"11th request should return 429, got {response_11.status_code}"
        
        # Check error message
        error_detail = response_11.json().get("detail", "")
        assert "10" in error_detail, f"Error should mention limit of 10: {error_detail}"
        
        print(f"✓ 11th range request blocked with 429: {error_detail}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
