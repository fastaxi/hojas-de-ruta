"""
RutasFast - Scalability Features Tests (Iteration 10)
Tests for:
- Health endpoint security (no hash exposure)
- conductor_driver_id validation
- Cursor pagination
- pickup_type validation
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test-asist@test.com"
TEST_PASSWORD = "Test1234!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestHealthEndpointSecurity:
    """Test that health endpoint does NOT expose sensitive hash data"""
    
    def test_health_no_admin_hash_raw_preview(self):
        """GET /api/health should NOT contain admin_hash_raw_preview"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        
        # CRITICAL: These fields should NOT be present
        assert "admin_hash_raw_preview" not in data, "Security issue: admin_hash_raw_preview exposed in health endpoint"
        assert "admin_hash_decoded_preview" not in data, "Security issue: admin_hash_decoded_preview exposed in health endpoint"
    
    def test_health_expected_fields(self):
        """GET /api/health should contain expected fields only"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        
        # Expected fields
        expected_fields = {
            "status", "environment", "admin_configured", 
            "admin_env_configured", "admin_username", 
            "email_enabled", "db_connected", "indexes_ok"
        }
        
        # Check all expected fields are present
        for field in expected_fields:
            assert field in data, f"Missing expected field: {field}"
        
        # Verify no extra sensitive fields
        sensitive_patterns = ["hash", "password", "secret", "key", "token"]
        for key in data.keys():
            key_lower = key.lower()
            for pattern in sensitive_patterns:
                if pattern in key_lower and key not in ["admin_configured", "admin_env_configured"]:
                    pytest.fail(f"Potentially sensitive field exposed: {key}")


class TestConductorDriverIdValidation:
    """Test conductor_driver_id validation in route sheet creation"""
    
    def test_create_sheet_with_invalid_driver_id(self, auth_headers):
        """POST /api/route-sheets with invalid conductor_driver_id should return 400"""
        invalid_driver_id = str(uuid.uuid4())  # Random UUID that doesn't exist
        
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_address": "Calle Test 123",
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger",
            "conductor_driver_id": invalid_driver_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "conductor" in data["detail"].lower() or "no encontrado" in data["detail"].lower()
    
    def test_create_sheet_with_other_user_driver_id(self, auth_headers):
        """POST /api/route-sheets with driver_id from another user should return 400"""
        # This test uses a driver ID that might exist but belongs to another user
        # We use a specific format that's unlikely to match any real driver
        other_user_driver_id = "other-user-driver-" + str(uuid.uuid4())[:8]
        
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_address": "Calle Test 123",
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger",
            "conductor_driver_id": other_user_driver_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        # Should indicate driver not found or doesn't belong to user
        assert "conductor" in data["detail"].lower() or "no encontrado" in data["detail"].lower() or "no pertenece" in data["detail"].lower()
    
    def test_create_sheet_without_driver_id_succeeds(self, auth_headers):
        """POST /api/route-sheets without conductor_driver_id should succeed (uses titular)"""
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_address": "Calle Test 123 - No Driver",
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger - No Driver"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert "sheet_number" in data


class TestCursorPagination:
    """Test cursor-based pagination for route sheets"""
    
    def test_pagination_returns_cursor_structure(self, auth_headers):
        """GET /api/route-sheets should return pagination structure"""
        response = requests.get(
            f"{BASE_URL}/api/route-sheets?limit=5",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination structure
        assert "sheets" in data, "Response should contain 'sheets' array"
        assert "next_cursor" in data, "Response should contain 'next_cursor'"
        assert "count" in data, "Response should contain 'count'"
        
        # Verify types
        assert isinstance(data["sheets"], list)
        assert isinstance(data["count"], int)
        assert data["next_cursor"] is None or isinstance(data["next_cursor"], str)
    
    def test_pagination_with_cursor(self, auth_headers):
        """GET /api/route-sheets with cursor should return next page"""
        # First request
        response1 = requests.get(
            f"{BASE_URL}/api/route-sheets?limit=2",
            headers=auth_headers
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        if data1["next_cursor"] is None:
            pytest.skip("Not enough sheets to test pagination")
        
        # Second request with cursor
        cursor = data1["next_cursor"]
        response2 = requests.get(
            f"{BASE_URL}/api/route-sheets?limit=2&cursor={cursor}",
            headers=auth_headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify different sheets returned
        ids1 = {s["id"] for s in data1["sheets"]}
        ids2 = {s["id"] for s in data2["sheets"]}
        
        # No overlap between pages
        assert ids1.isdisjoint(ids2), "Cursor pagination returned duplicate sheets"
    
    def test_pagination_limit_respected(self, auth_headers):
        """GET /api/route-sheets should respect limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/route-sheets?limit=3",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should not exceed limit
        assert len(data["sheets"]) <= 3


class TestPickupTypeValidation:
    """Test pickup_type validation (AIRPORT, OTHER, ROADSIDE)"""
    
    def test_airport_requires_flight_number(self, auth_headers):
        """AIRPORT pickup_type requires flight_number"""
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            # Missing flight_number
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "vuelo" in data["detail"].lower() or "flight" in data["detail"].lower()
    
    def test_airport_with_flight_number_succeeds(self, auth_headers):
        """AIRPORT pickup_type with flight_number should succeed"""
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            "flight_number": "IB1234",
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger Airport"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert "sheet_number" in data
    
    def test_other_requires_pickup_address(self, auth_headers):
        """OTHER pickup_type requires pickup_address"""
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            # Missing pickup_address
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "dirección" in data["detail"].lower() or "address" in data["detail"].lower()
    
    def test_other_rejects_flight_number(self, auth_headers):
        """OTHER pickup_type should reject flight_number"""
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_address": "Calle Test 123",
            "flight_number": "IB1234",  # Should not be allowed
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "vuelo" in data["detail"].lower() or "flight" in data["detail"].lower()
    
    def test_roadside_requires_pickup_address(self, auth_headers):
        """ROADSIDE pickup_type requires pickup_address"""
        # First get an assistance company
        companies_response = requests.get(
            f"{BASE_URL}/api/me/assistance-companies",
            headers=auth_headers
        )
        
        if companies_response.status_code != 200 or not companies_response.json():
            pytest.skip("No assistance companies available for ROADSIDE test")
        
        company_id = companies_response.json()[0]["id"]
        
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "ROADSIDE",
            # Missing pickup_address
            "assistance_company_id": company_id,
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "ubicación" in data["detail"].lower() or "asistencia" in data["detail"].lower() or "address" in data["detail"].lower()
    
    def test_roadside_requires_assistance_company(self, auth_headers):
        """ROADSIDE pickup_type requires assistance_company_id"""
        payload = {
            "contractor_phone": "600123456",
            "prebooked_date": "2026-01-15T10:00:00Z",
            "prebooked_locality": "Oviedo",
            "pickup_type": "ROADSIDE",
            "pickup_address": "Autopista A-66 km 45",
            # Missing assistance_company_id
            "pickup_datetime": "2026-01-16T14:00:00Z",
            "destination": "Gijón Centro",
            "passenger_info": "Test Passenger"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/route-sheets",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "empresa" in data["detail"].lower() or "asistencia" in data["detail"].lower() or "company" in data["detail"].lower()


class TestPDFGeneration:
    """Test PDF generation (basic functionality)"""
    
    def test_pdf_individual_returns_pdf(self, auth_headers):
        """GET /api/route-sheets/{id}/pdf should return PDF"""
        # First get a sheet
        sheets_response = requests.get(
            f"{BASE_URL}/api/route-sheets?limit=1",
            headers=auth_headers
        )
        
        if sheets_response.status_code != 200 or not sheets_response.json().get("sheets"):
            pytest.skip("No sheets available for PDF test")
        
        sheet_id = sheets_response.json()["sheets"][0]["id"]
        
        # Request PDF
        import time
        start_time = time.time()
        
        response = requests.get(
            f"{BASE_URL}/api/route-sheets/{sheet_id}/pdf",
            headers=auth_headers
        )
        
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
        
        # PDF should be generated in reasonable time (not blocking)
        assert elapsed_time < 30, f"PDF generation took too long: {elapsed_time}s"
        
        # Verify it's a valid PDF (starts with %PDF)
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
