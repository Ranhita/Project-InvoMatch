import requests

# 1. Login to get token
login_url = "http://127.0.0.1:8000/api/login"
login_payload = {
    "username": "web_agent",
    "password": "webAgentPassword123!"
}
response = requests.post(login_url, json=login_payload)
if response.status_code != 200:
    # Try form data login as backup
    response = requests.post(login_url, data=login_payload)

if response.status_code != 200:
    print(f"Login failed: {response.status_code} - {response.text}")
    exit(1)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Upload Invoice
invoice_path = r"c:\Users\ranhi\.gemini\antigravity-ide\scratch\test_files\INV-9999_ACME.csv"
with open(invoice_path, "rb") as f:
    files = {"file": ("INV-9999_ACME.csv", f, "text/csv")}
    upload_response = requests.post("http://127.0.0.1:8000/api/upload/invoice", headers=headers, files=files)
    print("Invoice Upload:", upload_response.status_code, upload_response.text)

# 3. Upload PO
po_path = r"c:\Users\ranhi\.gemini\antigravity-ide\scratch\test_files\PO-9999_ACME.csv"
with open(po_path, "rb") as f:
    files = {"file": ("PO-9999_ACME.csv", f, "text/csv")}
    upload_response = requests.post("http://127.0.0.1:8000/api/upload/po", headers=headers, files=files)
    print("PO Upload:", upload_response.status_code, upload_response.text)
