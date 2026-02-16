"""
Test suite for Assistance Companies CRUD and ROADSIDE route sheets
Tests the new 'Asistencia en carretera' feature for RutasFast
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from environment (do NOT hardcode)
TEST_EMAIL = os.environ.get('TEST_USER_EMAIL', '')
TEST_PASSWORD = os.environ.get('TEST_USER_PASSWORD', '')


class TestAssistanceCompanies:
    """Test CRUD operations for assistance companies"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.status_code} - {response.text}")
        
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup: delete test companies created during tests
        try:
            companies = self.session.get(f"{BASE_URL}/api/me/assistance-companies").json()
            for company in companies:
                if company.get("name", "").startswith("TEST_"):
                    self.session.delete(f"{BASE_URL}/api/me/assistance-companies/{company['id']}")
        except:
            pass
    
    def test_get_assistance_companies(self):
        """GET /api/me/assistance-companies - should return list"""
        response = self.session.get(f"{BASE_URL}/api/me/assistance-companies")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} assistance companies")
    
    def test_create_assistance_company_with_phone(self):
        """POST /api/me/assistance-companies - create with phone"""
        payload = {
            "name": "TEST_Asistencia Test Phone",
            "cif": "B12345678",
            "contact_phone": "612345678",
            "contact_email": None
        }
        
        response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data.get("message") == "Empresa de asistencia añadida"
        print(f"Created company with ID: {data['id']}")
        
        # Verify it was created
        companies = self.session.get(f"{BASE_URL}/api/me/assistance-companies").json()
        created = next((c for c in companies if c["id"] == data["id"]), None)
        assert created is not None
        assert created["name"] == payload["name"]
        assert created["cif"] == payload["cif"]
        assert created["contact_phone"] == payload["contact_phone"]
    
    def test_create_assistance_company_with_email(self):
        """POST /api/me/assistance-companies - create with email"""
        payload = {
            "name": "TEST_Asistencia Test Email",
            "cif": "B87654321",
            "contact_phone": None,
            "contact_email": "test@asistencia.com"
        }
        
        response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"Created company with email: {data['id']}")
    
    def test_create_assistance_company_with_both_contacts(self):
        """POST /api/me/assistance-companies - create with phone and email"""
        payload = {
            "name": "TEST_Asistencia Both Contacts",
            "cif": "B11111111",
            "contact_phone": "699999999",
            "contact_email": "both@asistencia.com"
        }
        
        response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"Created company with both contacts: {data['id']}")
    
    def test_create_assistance_company_missing_contact_fails(self):
        """POST /api/me/assistance-companies - should fail without phone or email"""
        payload = {
            "name": "TEST_No Contact",
            "cif": "B99999999",
            "contact_phone": None,
            "contact_email": None
        }
        
        response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=payload)
        
        assert response.status_code == 422  # Validation error
        print(f"Correctly rejected company without contact: {response.json()}")
    
    def test_create_assistance_company_missing_name_fails(self):
        """POST /api/me/assistance-companies - should fail without name"""
        payload = {
            "name": "",
            "cif": "B22222222",
            "contact_phone": "611111111"
        }
        
        response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=payload)
        
        assert response.status_code == 422
        print(f"Correctly rejected company without name: {response.json()}")
    
    def test_create_assistance_company_missing_cif_fails(self):
        """POST /api/me/assistance-companies - should fail without CIF"""
        payload = {
            "name": "TEST_No CIF",
            "cif": "",
            "contact_phone": "611111111"
        }
        
        response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=payload)
        
        assert response.status_code == 422
        print(f"Correctly rejected company without CIF: {response.json()}")
    
    def test_update_assistance_company(self):
        """PUT /api/me/assistance-companies/{id} - update company"""
        # First create a company
        create_payload = {
            "name": "TEST_Update Original",
            "cif": "B33333333",
            "contact_phone": "633333333"
        }
        create_response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=create_payload)
        assert create_response.status_code == 200
        company_id = create_response.json()["id"]
        
        # Update it
        update_payload = {
            "name": "TEST_Update Modified",
            "cif": "B44444444",
            "contact_phone": "644444444",
            "contact_email": "updated@test.com"
        }
        update_response = self.session.put(f"{BASE_URL}/api/me/assistance-companies/{company_id}", json=update_payload)
        
        assert update_response.status_code == 200
        assert update_response.json().get("message") == "Empresa actualizada"
        
        # Verify update
        companies = self.session.get(f"{BASE_URL}/api/me/assistance-companies").json()
        updated = next((c for c in companies if c["id"] == company_id), None)
        assert updated is not None
        assert updated["name"] == update_payload["name"]
        assert updated["cif"] == update_payload["cif"]
        assert updated["contact_phone"] == update_payload["contact_phone"]
        assert updated["contact_email"] == update_payload["contact_email"]
        print(f"Successfully updated company {company_id}")
    
    def test_update_nonexistent_company_fails(self):
        """PUT /api/me/assistance-companies/{id} - should fail for non-existent"""
        update_payload = {
            "name": "TEST_Nonexistent",
            "cif": "B55555555",
            "contact_phone": "655555555"
        }
        response = self.session.put(f"{BASE_URL}/api/me/assistance-companies/nonexistent-id", json=update_payload)
        
        assert response.status_code == 404
        print(f"Correctly returned 404 for non-existent company")
    
    def test_delete_assistance_company(self):
        """DELETE /api/me/assistance-companies/{id} - delete company"""
        # First create a company
        create_payload = {
            "name": "TEST_Delete Me",
            "cif": "B66666666",
            "contact_phone": "666666666"
        }
        create_response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=create_payload)
        assert create_response.status_code == 200
        company_id = create_response.json()["id"]
        
        # Delete it
        delete_response = self.session.delete(f"{BASE_URL}/api/me/assistance-companies/{company_id}")
        
        assert delete_response.status_code == 200
        assert delete_response.json().get("message") == "Empresa eliminada"
        
        # Verify deletion
        companies = self.session.get(f"{BASE_URL}/api/me/assistance-companies").json()
        deleted = next((c for c in companies if c["id"] == company_id), None)
        assert deleted is None
        print(f"Successfully deleted company {company_id}")
    
    def test_delete_nonexistent_company_fails(self):
        """DELETE /api/me/assistance-companies/{id} - should fail for non-existent"""
        response = self.session.delete(f"{BASE_URL}/api/me/assistance-companies/nonexistent-id")
        
        assert response.status_code == 404
        print(f"Correctly returned 404 for non-existent company")


class TestRouteSheetROADSIDE:
    """Test route sheet creation with ROADSIDE pickup type"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.status_code} - {response.text}")
        
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Create a test assistance company for ROADSIDE tests
        company_payload = {
            "name": "TEST_ROADSIDE Company",
            "cif": "B77777777",
            "contact_phone": "677777777"
        }
        company_response = self.session.post(f"{BASE_URL}/api/me/assistance-companies", json=company_payload)
        if company_response.status_code == 200:
            self.test_company_id = company_response.json()["id"]
        else:
            # Try to find existing test company
            companies = self.session.get(f"{BASE_URL}/api/me/assistance-companies").json()
            test_company = next((c for c in companies if c.get("name", "").startswith("TEST_ROADSIDE")), None)
            if test_company:
                self.test_company_id = test_company["id"]
            else:
                pytest.skip("Could not create or find test assistance company")
        
        yield
        
        # Cleanup
        try:
            companies = self.session.get(f"{BASE_URL}/api/me/assistance-companies").json()
            for company in companies:
                if company.get("name", "").startswith("TEST_"):
                    self.session.delete(f"{BASE_URL}/api/me/assistance-companies/{company['id']}")
        except:
            pass
    
    def test_create_roadside_route_sheet_success(self):
        """POST /api/route-sheets - create ROADSIDE sheet with assistance company"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "ROADSIDE",
            "pickup_address": "A-66 km 15, Llanera",
            "pickup_datetime": tomorrow,
            "destination": "Taller Mecánico Central, Gijón",
            "passenger_info": "Conductor averiado - Juan García",
            "assistance_company_id": self.test_company_id
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "sheet_number" in data
        print(f"Created ROADSIDE sheet: {data['sheet_number']}")
        
        # Verify the sheet has assistance_company_snapshot
        sheet_response = self.session.get(f"{BASE_URL}/api/route-sheets/{data['id']}")
        assert sheet_response.status_code == 200
        sheet = sheet_response.json()
        
        assert sheet["pickup_type"] == "ROADSIDE"
        assert sheet.get("assistance_company_snapshot") is not None
        snapshot = sheet["assistance_company_snapshot"]
        assert snapshot["name"] == "TEST_ROADSIDE Company"
        assert snapshot["cif"] == "B77777777"
        print(f"Verified assistance_company_snapshot: {snapshot}")
    
    def test_create_roadside_without_company_fails(self):
        """POST /api/route-sheets - ROADSIDE without assistance_company_id should fail"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "ROADSIDE",
            "pickup_address": "A-66 km 15, Llanera",
            "pickup_datetime": tomorrow,
            "destination": "Taller Mecánico Central, Gijón",
            "passenger_info": "Conductor averiado",
            "assistance_company_id": None
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 400
        assert "empresa de asistencia" in response.json().get("detail", "").lower()
        print(f"Correctly rejected ROADSIDE without company: {response.json()}")
    
    def test_create_roadside_without_address_fails(self):
        """POST /api/route-sheets - ROADSIDE without pickup_address should fail"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "ROADSIDE",
            "pickup_address": "",
            "pickup_datetime": tomorrow,
            "destination": "Taller Mecánico Central, Gijón",
            "passenger_info": "Conductor averiado",
            "assistance_company_id": self.test_company_id
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 400
        assert "ubicación" in response.json().get("detail", "").lower() or "asistencia" in response.json().get("detail", "").lower()
        print(f"Correctly rejected ROADSIDE without address: {response.json()}")
    
    def test_create_roadside_with_flight_number_fails(self):
        """POST /api/route-sheets - ROADSIDE with flight_number should fail"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "ROADSIDE",
            "pickup_address": "A-66 km 15, Llanera",
            "pickup_datetime": tomorrow,
            "destination": "Taller Mecánico Central, Gijón",
            "passenger_info": "Conductor averiado",
            "assistance_company_id": self.test_company_id,
            "flight_number": "VY1234"
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 400
        assert "vuelo" in response.json().get("detail", "").lower()
        print(f"Correctly rejected ROADSIDE with flight_number: {response.json()}")
    
    def test_create_roadside_with_invalid_company_fails(self):
        """POST /api/route-sheets - ROADSIDE with non-existent company should fail"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "ROADSIDE",
            "pickup_address": "A-66 km 15, Llanera",
            "pickup_datetime": tomorrow,
            "destination": "Taller Mecánico Central, Gijón",
            "passenger_info": "Conductor averiado",
            "assistance_company_id": "nonexistent-company-id"
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 400
        assert "no encontrada" in response.json().get("detail", "").lower()
        print(f"Correctly rejected ROADSIDE with invalid company: {response.json()}")


class TestRouteSheetAIRPORT:
    """Test route sheet creation with AIRPORT pickup type validations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.status_code} - {response.text}")
        
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_create_airport_without_flight_number_fails(self):
        """POST /api/route-sheets - AIRPORT without flight_number should fail"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            "pickup_address": "Aeropuerto de Asturias",
            "pickup_datetime": tomorrow,
            "destination": "Hotel Reconquista, Oviedo",
            "passenger_info": "Turista - María López",
            "flight_number": None
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 400
        assert "vuelo" in response.json().get("detail", "").lower()
        print(f"Correctly rejected AIRPORT without flight_number: {response.json()}")
    
    def test_create_airport_with_invalid_flight_format_fails(self):
        """POST /api/route-sheets - AIRPORT with invalid flight format should fail"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            "pickup_address": "Aeropuerto de Asturias",
            "pickup_datetime": tomorrow,
            "destination": "Hotel Reconquista, Oviedo",
            "passenger_info": "Turista - María López",
            "flight_number": "INVALID"
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 400
        assert "formato" in response.json().get("detail", "").lower() or "inválido" in response.json().get("detail", "").lower()
        print(f"Correctly rejected AIRPORT with invalid flight format: {response.json()}")
    
    def test_create_airport_success(self):
        """POST /api/route-sheets - AIRPORT with valid flight_number should succeed"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "AIRPORT",
            "pickup_datetime": tomorrow,
            "destination": "Hotel Reconquista, Oviedo",
            "passenger_info": "Turista - María López",
            "flight_number": "VY1234"
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "sheet_number" in data
        print(f"Created AIRPORT sheet: {data['sheet_number']}")
        
        # Verify the sheet
        sheet_response = self.session.get(f"{BASE_URL}/api/route-sheets/{data['id']}")
        assert sheet_response.status_code == 200
        sheet = sheet_response.json()
        
        assert sheet["pickup_type"] == "AIRPORT"
        assert sheet["flight_number"] == "VY1234"
        assert sheet["pickup_address"] == "Aeropuerto de Asturias"
        print(f"Verified AIRPORT sheet with flight: {sheet['flight_number']}")


class TestRouteSheetOTHER:
    """Test route sheet creation with OTHER pickup type"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.status_code} - {response.text}")
        
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_create_other_without_address_fails(self):
        """POST /api/route-sheets - OTHER without pickup_address should fail"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_address": "",
            "pickup_datetime": tomorrow,
            "destination": "Hotel Reconquista, Oviedo",
            "passenger_info": "Cliente - Pedro Sánchez"
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 400
        assert "dirección" in response.json().get("detail", "").lower() or "recogida" in response.json().get("detail", "").lower()
        print(f"Correctly rejected OTHER without address: {response.json()}")
    
    def test_create_other_with_flight_number_fails(self):
        """POST /api/route-sheets - OTHER with flight_number should fail"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_address": "Calle Uría 10, Oviedo",
            "pickup_datetime": tomorrow,
            "destination": "Hotel Reconquista, Oviedo",
            "passenger_info": "Cliente - Pedro Sánchez",
            "flight_number": "VY1234"
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 400
        assert "vuelo" in response.json().get("detail", "").lower()
        print(f"Correctly rejected OTHER with flight_number: {response.json()}")
    
    def test_create_other_success(self):
        """POST /api/route-sheets - OTHER with valid data should succeed"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "contractor_phone": "612345678",
            "prebooked_date": datetime.now().strftime("%Y-%m-%d"),
            "prebooked_locality": "Oviedo",
            "pickup_type": "OTHER",
            "pickup_address": "Calle Uría 10, Oviedo",
            "pickup_datetime": tomorrow,
            "destination": "Hotel Reconquista, Oviedo",
            "passenger_info": "Cliente - Pedro Sánchez"
        }
        
        response = self.session.post(f"{BASE_URL}/api/route-sheets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "sheet_number" in data
        print(f"Created OTHER sheet: {data['sheet_number']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
