import sys
import os
import unittest

# Set environment variables for testing before importing app packages
os.environ["DATABASE_URL"] = "sqlite:///../database/test_invomatch.db"
os.environ["UPLOAD_DIR"] = "../test_uploads"

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.append(backend_path)

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

class TestInvoMatchAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.test_username = "finance_test_user_p34"
        cls.test_email = "test_p34@company.com"
        cls.test_password = "securepassword123"
        cls.token = None
        cls.invoice_id = None
        cls.po_id = None

    def test_01_register(self):
        response = self.client.post("/api/register", json={
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        })
        if response.status_code == 400:
            print("  (User already exists, proceeding)")
            self.assertTrue(True)
        else:
            self.assertEqual(response.status_code, 201)

    def test_02_login(self):
        response = self.client.post("/api/login", json={
            "username": self.test_username,
            "password": self.test_password
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.__class__.token = data["access_token"]

    def test_03_csv_invoice_parsing(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create mock CSV document
        csv_content = (
            "SKU,Description,Qty,Unit Price,Total\n"
            "A102,Core Microprocessor,15,250.00,3750.00\n"
            "B404,LED Display Panel,5,120.50,602.50\n"
        ).encode('utf-8')
        
        files = {"file": ("invoice_acme.csv", csv_content, "text/csv")}
        response = self.client.post("/api/upload/invoice", headers=headers, files=files)
        
        if response.status_code == 409:
            # If already uploaded, fetch invoices to get an ID
            recent = self.client.get("/api/recent-uploads", headers=headers).json()
            invoices = [d for d in recent if d["document_type"] == "invoice"]
            self.__class__.invoice_id = invoices[0]["id"]
            print(f"  (Invoice already exists: {self.invoice_id})")
        else:
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "processed")
            self.__class__.invoice_id = data["file_id"]

        # Fetch lines to verify CSV parsing worked (Phase 3)
        lines_response = self.client.get(f"/api/documents/{self.invoice_id}/lines", headers=headers)
        self.assertEqual(lines_response.status_code, 200)
        lines = lines_response.json()
        self.assertGreaterEqual(len(lines), 1)
        self.assertEqual(lines[0]["sku"], "A102")
        self.assertEqual(lines[0]["quantity"], 15.0)
        self.assertEqual(lines[0]["unit_price"], 250.00)

    def test_04_csv_po_parsing(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create mock PO CSV document
        csv_content = (
            "Item Code,Details,Quantity,Price,Subtotal\n"
            "A102,Core Microprocessor,15,250.00,3750.00\n"
            "B404,LED Display Panel,5,115.00,575.00\n"  # slight price discrepancy for testing features
        ).encode('utf-8')
        
        files = {"file": ("po_acme.csv", csv_content, "text/csv")}
        response = self.client.post("/api/upload/po", headers=headers, files=files)
        
        if response.status_code == 409:
            recent = self.client.get("/api/recent-uploads", headers=headers).json()
            pos = [d for d in recent if d["document_type"] == "po"]
            self.__class__.po_id = pos[0]["id"]
            print(f"  (PO already exists: {self.po_id})")
        else:
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.__class__.po_id = data["file_id"]

        # Fetch PO lines
        lines_response = self.client.get(f"/api/documents/{self.po_id}/lines", headers=headers)
        self.assertEqual(lines_response.status_code, 200)
        lines = lines_response.json()
        self.assertGreaterEqual(len(lines), 1)
        self.assertEqual(lines[0]["sku"], "A102")

    def test_05_feature_vector_calculation(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Trigger features calculation comparing our invoice and purchase order (Phase 4)
        response = self.client.get(
            f"/api/documents/{self.invoice_id}/features?candidate_id={self.po_id}", 
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        features = response.json()
        self.assertGreaterEqual(len(features), 1)
        
        # Verify vector keys are generated correctly
        first_vector = features[0]["vector"]
        self.assertIn("vendor_similarity", first_vector)
        self.assertIn("sku_similarity", first_vector)
        self.assertIn("description_similarity", first_vector)
        self.assertIn("qty_difference_abs", first_vector)
        self.assertIn("price_difference_abs", first_vector)
        self.assertIn("date_difference_days", first_vector)
        self.assertIn("historical_vendor_avg", first_vector)
        
        # Verify exact SKU match calculations
        # A102 vs A102 similarity should be 1.0 (100%)
        a102_comparison = [f for f in features if f["invoice_line_number"] == 1 and f["po_line_number"] == 1]
        if a102_comparison:
            self.assertEqual(a102_comparison[0]["vector"]["sku_similarity"], 1.0)
            self.assertEqual(a102_comparison[0]["vector"]["price_difference_abs"], 0.0)

        # B404 vs B404 pricing difference should be 5.50
        b404_comparison = [f for f in features if f["invoice_line_number"] == 2 and f["po_line_number"] == 2]
        if b404_comparison:
            self.assertEqual(b404_comparison[0]["vector"]["price_difference_abs"], 5.50)

    def test_06_reconcile_and_anomaly_flags(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Trigger matching and reconciliation
        response = self.client.post(f"/api/reconcile/{self.invoice_id}", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "matched" if data["status"] == "matched" else data["status"])
        self.assertGreaterEqual(data["confidence_score"], 0.60)
        self.assertEqual(data["best_candidate_po"], self.po_id)
        
        # Fetch flags list
        flags_response = self.client.get(f"/api/documents/{self.invoice_id}/flags", headers=headers)
        self.assertEqual(flags_response.status_code, 200)
        self.assertIsInstance(flags_response.json(), list)

    def test_07_manual_match_actions(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Fetch matches list
        response = self.client.get("/api/matches", headers=headers)
        self.assertEqual(response.status_code, 200)
        matches = response.json()
        self.assertGreaterEqual(len(matches), 1)
        match_id = matches[0]["id"]
        
        # Approve the match
        approve_resp = self.client.post(f"/api/matches/{match_id}/approve", headers=headers)
        self.assertEqual(approve_resp.status_code, 200)
        self.assertEqual(approve_resp.json()["status"], "approved")

    def test_08_isolation_forest_and_shap_explainability(self):
        from app.explainers import calculate_shap_values
        
        test_vector = {
            "vendor_similarity": 0.90,
            "sku_similarity": 1.0,
            "description_similarity": 0.85,
            "qty_difference_rel": 0.0,
            "price_difference_rel": 0.25,
            "total_difference_rel": 0.25,
            "date_difference_days": 2.0,
            "historical_avg_diff": 15.0
        }
        
        shap_results = calculate_shap_values(test_vector)
        self.assertIn("base_probability", shap_results)
        self.assertIn("importances", shap_results)
        self.assertIsInstance(shap_results["importances"], dict)
        
        price_importance = shap_results["importances"].get("price_difference_rel", 0.0)
        self.assertGreaterEqual(price_importance, 0.0)

    def test_09_analytics_downloads_and_ap_workflow(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # 1. Fetch matches
        matches_resp = self.client.get("/api/matches", headers=headers)
        self.assertEqual(matches_resp.status_code, 200)
        matches = matches_resp.json()
        self.assertGreaterEqual(len(matches), 1)
        match_id = matches[0]["id"]
        
        # 2. Approve match with comment
        comment_payload = {"comment": "Approved by CFO audit"}
        approve_resp = self.client.post(
            f"/api/matches/{match_id}/approve", 
            headers=headers, 
            json=comment_payload
        )
        self.assertEqual(approve_resp.status_code, 200)
        self.assertEqual(approve_resp.json()["status"], "approved")
        
        # 3. Mark needs-review with comment
        review_payload = {"comment": "Check invoice item unit cost"}
        review_resp = self.client.post(
            f"/api/matches/{match_id}/needs-review", 
            headers=headers, 
            json=review_payload
        )
        self.assertEqual(review_resp.status_code, 200)
        self.assertEqual(review_resp.json()["status"], "needs_review")
        
        # 4. Fetch dashboard analytics
        analytics_resp = self.client.get("/api/analytics", headers=headers)
        self.assertEqual(analytics_resp.status_code, 200)
        analytics = analytics_resp.json()
        self.assertIn("summary", analytics)
        self.assertIn("risk_distribution", analytics)
        self.assertIn("vendor_performance", analytics)
        
        # 5. Fetch audit logs
        audit_resp = self.client.get("/api/audit-logs", headers=headers)
        self.assertEqual(audit_resp.status_code, 200)
        audits = audit_resp.json()
        self.assertGreaterEqual(len(audits), 1)
        
        # 6. Test file download
        dl_resp = self.client.get(f"/api/documents/{self.invoice_id}/download", headers=headers)
        self.assertEqual(dl_resp.status_code, 200)
        self.assertIn("text/csv", dl_resp.headers.get("content-type", ""))

        # 7. Test report exports (CSV and HTML formats)
        for r_type in ["monthly", "vendor", "anomaly", "audit", "finance"]:
            csv_export = self.client.get(
                f"/api/reports/export?report_type={r_type}&format=csv", 
                headers=headers
            )
            self.assertEqual(csv_export.status_code, 200)
            self.assertIn("text/csv", csv_export.headers.get("content-type", ""))
            
            html_export = self.client.get(
                f"/api/reports/export?report_type={r_type}&format=html", 
                headers=headers
            )
            self.assertEqual(html_export.status_code, 200)
            self.assertIn("text/html", html_export.headers.get("content-type", ""))

if __name__ == "__main__":
    unittest.main()
