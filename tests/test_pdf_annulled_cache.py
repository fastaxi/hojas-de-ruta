"""
Test PDF Caching for ANNULLED Sheets

Tests the extended PDF caching feature that now includes ANNULLED sheets:
1. PDF ACTIVE: first download X-Cache: MISS, second X-Cache: HIT
2. Annul sheet: only invalidates ACTIVE cache, not ANNULLED
3. PDF ANNULLED: first download after annul X-Cache: MISS, second X-Cache: HIT
4. PDF ANNULLED maintains watermark/ANULADA mark
5. Invalidation by pdf_config_version affects both ACTIVE and ANNULLED
6. Index pdf_cache is unique on (sheet_id, config_version, status)

Key: Cache key is now (sheet_id, config_version, status) - same sheet can have 2 cache entries
"""
import pytest
import requests
import os
import time
import io
from datetime import datetime, date
from PyPDF2 import PdfReader

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rutasfast-1.preview.emergentagent.com').rstrip('/')

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
        print(f"Admin login failed: {response.status_code} - {response.text}")
        return None
    
    @staticmethod
    def create_test_user(suffix=""):
        """Create and approve a test user, return access token"""
        timestamp = int(time.time())
        email = f"test_annul_{timestamp}{suffix}@test.com"
        
        # Register user
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": f"Test Annul User {timestamp}",
            "dni_cif": f"ANNUL{timestamp}",
            "license_number": f"LIC{timestamp}",
            "license_council": "Test Council",
            "phone": f"+34600{timestamp % 1000000:06d}",
            "email": email,
            "password": "TestPass123",
            "vehicle_brand": "Test Brand",
            "vehicle_model": "Test Model",
            "vehicle_plate": f"ANNUL{timestamp % 10000:04d}"
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
    
    @staticmethod
    def annul_route_sheet(access_token, sheet_id, reason="Test annulment"):
        """Annul a route sheet"""
        response = requests.post(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/annul",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"reason": reason}
        )
        return response.status_code == 200


class TestActivePdfCache:
    """Test PDF caching for ACTIVE sheets"""
    
    def test_active_pdf_cache_miss_then_hit(self):
        """Test ACTIVE PDF: first download X-Cache: MISS, second X-Cache: HIT"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_active_cache")
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
        assert x_cache_1 == "MISS", f"First ACTIVE request should be MISS, got: {x_cache_1}"
        print(f"✓ First ACTIVE PDF request: X-Cache={x_cache_1}")
        
        # Second request - should be HIT
        response2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response2.status_code == 200, f"Second PDF request failed: {response2.text}"
        x_cache_2 = response2.headers.get("X-Cache", "")
        assert x_cache_2 == "HIT", f"Second ACTIVE request should be HIT, got: {x_cache_2}"
        print(f"✓ Second ACTIVE PDF request: X-Cache={x_cache_2}")


class TestAnnulInvalidatesOnlyActiveCache:
    """Test that annulling a sheet only invalidates ACTIVE cache"""
    
    def test_annul_invalidates_active_cache_only(self):
        """Test: Annul sheet only invalidates ACTIVE cache, not ANNULLED"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_annul_inv")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # First request - populate ACTIVE cache
        response1 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response1.status_code == 200
        assert response1.headers.get("X-Cache") == "MISS", "First request should be MISS"
        print(f"✓ ACTIVE cache populated: X-Cache=MISS")
        
        # Second request - verify ACTIVE cache HIT
        response2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response2.status_code == 200
        assert response2.headers.get("X-Cache") == "HIT", "Second request should be HIT"
        print(f"✓ ACTIVE cache verified: X-Cache=HIT")
        
        # Annul the sheet
        annul_success = TestSetup.annul_route_sheet(access_token, sheet_id, "Testing cache invalidation")
        assert annul_success, "Failed to annul route sheet"
        print(f"✓ Sheet annulled successfully")
        
        # Request PDF again - now it's ANNULLED, should be MISS (new cache entry)
        response3 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response3.status_code == 200
        x_cache_3 = response3.headers.get("X-Cache", "")
        assert x_cache_3 == "MISS", f"First ANNULLED request should be MISS, got: {x_cache_3}"
        print(f"✓ First ANNULLED PDF request: X-Cache={x_cache_3}")


class TestAnnulledPdfCache:
    """Test PDF caching for ANNULLED sheets"""
    
    def test_annulled_pdf_cache_miss_then_hit(self):
        """Test ANNULLED PDF: first download after annul X-Cache: MISS, second X-Cache: HIT"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_annul_cache")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Annul the sheet first
        annul_success = TestSetup.annul_route_sheet(access_token, sheet_id, "Testing ANNULLED cache")
        assert annul_success, "Failed to annul route sheet"
        print(f"✓ Sheet annulled successfully")
        
        # First request for ANNULLED PDF - should be MISS
        response1 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response1.status_code == 200, f"First ANNULLED PDF request failed: {response1.text}"
        x_cache_1 = response1.headers.get("X-Cache", "")
        assert x_cache_1 == "MISS", f"First ANNULLED request should be MISS, got: {x_cache_1}"
        print(f"✓ First ANNULLED PDF request: X-Cache={x_cache_1}")
        
        # Second request for ANNULLED PDF - should be HIT
        response2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response2.status_code == 200, f"Second ANNULLED PDF request failed: {response2.text}"
        x_cache_2 = response2.headers.get("X-Cache", "")
        assert x_cache_2 == "HIT", f"Second ANNULLED request should be HIT, got: {x_cache_2}"
        print(f"✓ Second ANNULLED PDF request: X-Cache={x_cache_2}")


class TestAnnulledPdfWatermark:
    """Test that ANNULLED PDF maintains watermark/ANULADA mark"""
    
    def test_annulled_pdf_contains_watermark(self):
        """Test PDF ANNULLED maintains watermark/marca ANULADA"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_watermark")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Annul the sheet
        annul_success = TestSetup.annul_route_sheet(access_token, sheet_id, "Testing watermark")
        assert annul_success, "Failed to annul route sheet"
        
        # Get ANNULLED PDF
        response = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200, f"PDF request failed: {response.text}"
        
        # Check PDF content
        pdf_content = response.content
        assert len(pdf_content) > 0, "PDF content is empty"
        
        # PDF should be valid (starts with %PDF)
        assert pdf_content[:4] == b'%PDF', "Response is not a valid PDF"
        
        # Extract text from PDF using PyPDF2
        pdf_reader = PdfReader(io.BytesIO(pdf_content))
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() or ""
        
        # Check for ANULADA markers in extracted text
        has_hoja_anulada = 'HOJA ANULADA' in extracted_text
        has_motivo = 'MOTIVO' in extracted_text
        has_annul_reason = 'Testing watermark' in extracted_text
        
        assert has_hoja_anulada, "ANNULLED PDF should contain 'HOJA ANULADA' header"
        assert has_motivo, "ANNULLED PDF should contain 'MOTIVO DE ANULACIÓN' section"
        assert has_annul_reason, "ANNULLED PDF should contain the annul reason"
        
        print(f"✓ ANNULLED PDF contains watermark/ANULADA mark")
        print(f"  PDF size: {len(pdf_content)} bytes")
        print(f"  Has 'HOJA ANULADA': {has_hoja_anulada}")
        print(f"  Has 'MOTIVO': {has_motivo}")
        print(f"  Has annul reason: {has_annul_reason}")


class TestConfigVersionInvalidatesBothCaches:
    """Test that pdf_config_version invalidation affects both ACTIVE and ANNULLED"""
    
    def test_config_version_invalidates_active_cache(self):
        """Test: Changing pdf_config_version invalidates ACTIVE cache"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_cfg_active")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Populate ACTIVE cache
        response1 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response1.status_code == 200
        print(f"✓ ACTIVE cache populated: X-Cache={response1.headers.get('X-Cache')}")
        
        # Verify cache HIT
        response2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response2.status_code == 200
        assert response2.headers.get("X-Cache") == "HIT"
        print(f"✓ ACTIVE cache verified: X-Cache=HIT")
        
        # Change config to increment pdf_config_version
        admin_token = TestSetup.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        timestamp = int(time.time())
        update_response = requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"header_title": f"HOJA DE RUTA CFG {timestamp}"}
        )
        assert update_response.status_code == 200
        print(f"✓ Config updated (pdf_config_version incremented)")
        
        # Request PDF again - should be MISS (config version changed)
        response3 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response3.status_code == 200
        x_cache_3 = response3.headers.get("X-Cache", "")
        assert x_cache_3 == "MISS", f"After config change, ACTIVE should be MISS, got: {x_cache_3}"
        print(f"✓ After config change, ACTIVE PDF: X-Cache={x_cache_3}")
        
        # Restore config
        requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"header_title": "HOJA DE RUTA"}
        )
    
    def test_config_version_invalidates_annulled_cache(self):
        """Test: Changing pdf_config_version invalidates ANNULLED cache"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_cfg_annul")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Annul the sheet
        annul_success = TestSetup.annul_route_sheet(access_token, sheet_id, "Testing config invalidation")
        assert annul_success, "Failed to annul route sheet"
        print(f"✓ Sheet annulled")
        
        # Populate ANNULLED cache
        response1 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response1.status_code == 200
        print(f"✓ ANNULLED cache populated: X-Cache={response1.headers.get('X-Cache')}")
        
        # Verify cache HIT
        response2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response2.status_code == 200
        assert response2.headers.get("X-Cache") == "HIT"
        print(f"✓ ANNULLED cache verified: X-Cache=HIT")
        
        # Change config to increment pdf_config_version
        admin_token = TestSetup.get_admin_token()
        assert admin_token, "Failed to get admin token"
        
        timestamp = int(time.time())
        update_response = requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"header_title": f"HOJA DE RUTA ANNUL {timestamp}"}
        )
        assert update_response.status_code == 200
        print(f"✓ Config updated (pdf_config_version incremented)")
        
        # Request PDF again - should be MISS (config version changed)
        response3 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response3.status_code == 200
        x_cache_3 = response3.headers.get("X-Cache", "")
        assert x_cache_3 == "MISS", f"After config change, ANNULLED should be MISS, got: {x_cache_3}"
        print(f"✓ After config change, ANNULLED PDF: X-Cache={x_cache_3}")
        
        # Restore config
        requests.put(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"header_title": "HOJA DE RUTA"}
        )


class TestCacheKeyUniqueness:
    """Test that cache key (sheet_id, config_version, status) allows separate entries"""
    
    def test_same_sheet_can_have_active_and_annulled_cache(self):
        """Test: Same sheet_id can have 2 cache entries with different status"""
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_dual_cache")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Step 1: Populate ACTIVE cache
        response_active_1 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response_active_1.status_code == 200
        assert response_active_1.headers.get("X-Cache") == "MISS"
        print(f"✓ ACTIVE cache populated: X-Cache=MISS")
        
        # Step 2: Verify ACTIVE cache HIT
        response_active_2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response_active_2.status_code == 200
        assert response_active_2.headers.get("X-Cache") == "HIT"
        print(f"✓ ACTIVE cache verified: X-Cache=HIT")
        
        # Step 3: Annul the sheet (this invalidates ACTIVE cache only)
        annul_success = TestSetup.annul_route_sheet(access_token, sheet_id, "Testing dual cache")
        assert annul_success, "Failed to annul route sheet"
        print(f"✓ Sheet annulled (ACTIVE cache invalidated)")
        
        # Step 4: Request ANNULLED PDF - should be MISS (new cache entry for ANNULLED)
        response_annulled_1 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response_annulled_1.status_code == 200
        assert response_annulled_1.headers.get("X-Cache") == "MISS"
        print(f"✓ ANNULLED cache populated: X-Cache=MISS")
        
        # Step 5: Verify ANNULLED cache HIT
        response_annulled_2 = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response_annulled_2.status_code == 200
        assert response_annulled_2.headers.get("X-Cache") == "HIT"
        print(f"✓ ANNULLED cache verified: X-Cache=HIT")
        
        print(f"✓ Same sheet has independent ACTIVE and ANNULLED cache entries")


class TestCacheIndexUniqueness:
    """Test the unique index on pdf_cache collection"""
    
    def test_cache_index_unique_on_sheet_config_status(self):
        """Test: Index pdf_cache is unique on (sheet_id, config_version, status)"""
        # This test verifies the behavior by checking that:
        # 1. Same sheet with same status always returns same cache (HIT after first MISS)
        # 2. Different status creates new cache entry (MISS)
        
        # Create test user and route sheet
        user_id, access_token = TestSetup.create_test_user("_index_test")
        assert access_token, "Failed to create test user"
        
        sheet_id = TestSetup.create_route_sheet(access_token)
        assert sheet_id, "Failed to create route sheet"
        
        # Multiple requests for ACTIVE - all should use same cache entry
        responses_active = []
        for i in range(3):
            response = requests.get(
                f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert response.status_code == 200
            responses_active.append(response.headers.get("X-Cache"))
        
        # First should be MISS, rest should be HIT
        assert responses_active[0] == "MISS", "First ACTIVE request should be MISS"
        assert responses_active[1] == "HIT", "Second ACTIVE request should be HIT"
        assert responses_active[2] == "HIT", "Third ACTIVE request should be HIT"
        print(f"✓ ACTIVE cache uses single entry: {responses_active}")
        
        # Annul and test ANNULLED cache
        annul_success = TestSetup.annul_route_sheet(access_token, sheet_id, "Index test")
        assert annul_success
        
        responses_annulled = []
        for i in range(3):
            response = requests.get(
                f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert response.status_code == 200
            responses_annulled.append(response.headers.get("X-Cache"))
        
        # First should be MISS (new status), rest should be HIT
        assert responses_annulled[0] == "MISS", "First ANNULLED request should be MISS"
        assert responses_annulled[1] == "HIT", "Second ANNULLED request should be HIT"
        assert responses_annulled[2] == "HIT", "Third ANNULLED request should be HIT"
        print(f"✓ ANNULLED cache uses single entry: {responses_annulled}")
        
        print(f"✓ Index uniqueness verified: (sheet_id, config_version, status)")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
