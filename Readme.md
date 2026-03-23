📘 License & Certificate Tracker — Backend Documentation

This project is a secure, full-stack web application for uploading, organizing, and tracking personal licenses and certificates. The backend is built using Django + Django REST Framework (DRF) with a MySQL database and includes owner-based permissions, private file storage, expiry reminders, and API documentation.

🚀 Features
🔐 Authentication

JWT authentication (/api/token/)

Secure, user-scoped API access

📁 Upload & Manage Documents

Upload certificates and licenses

Strict file validation (PDF/PNG/JPG only, max 10MB)

Private storage paths (per-user directories)

Automatic assignment of owner field

🔒 Secure File Access

Only the owning user can download files

Non-owners receive 403 Forbidden

⏰ Expiry Reminders

Background reminder system

Notification model + dashboard summary

📊 Dashboard API

Shows:

Total certificates

Expired

Expiring soon

Category breakdown

📘 Automatic API Docs (Swagger + Redoc)

Available at:

Swagger UI: /api/docs/

OpenAPI JSON: /api/schema/

Redoc: /api/redoc/

🧪 Integration Test Included

test_file_permissions.py verifies:

Owner can download

Non-owner cannot

📦 Tech Stack
Area	Technology
Backend	Django, Django REST Framework
Auth	SimpleJWT
Database	MySQL
Storage	Django FileStorage (local)
Docs	drf-spectacular (Swagger, Redoc)
Testing	Django TestCase

▶️ How to Run the Backend
1. Install dependencies
pip install -r requirements.txt

2. Run migrations
python manage.py migrate

3. Start server
python manage.py runserver


API will be available at:

http://localhost:8000/api/

🧭 API Documentation

Once the server is running:

✔ Swagger UI
http://localhost:8000/api/docs/

✔ Redoc
http://localhost:8000/api/redoc/

✔ OpenAPI Schema (JSON)
http://localhost:8000/api/schema/


These automatically update whenever you modify serializers, viewsets, or endpoints.

🔑 Authentication (JWT)

Use this endpoint to get an access token:

POST /api/token/


Example body:

{
  "username": "your_username",
  "password": "your_password"
}


Use the returned access token in all secured requests:

Authorization: Bearer <access_token>

📤 Uploading a Certificate (Example)
POST /api/certificates/
Content-Type: multipart/form-data
Authorization: Bearer <token>


Fields:

title

issued_date

file (PDF, PNG, JPEG)

📥 Secure Download (Owner Only)
GET /api/certificates/<id>/download/
Authorization: Bearer <token>


Returns a FileResponse only if the logged-in user is the owner.
Otherwise returns 403 Forbidden.

Same applies for licenses:

GET /api/licenses/<id>/download/

🧪 Running Tests
python manage.py test tracker.tests.test_file_permissions -v2

🧰 Postman Collection

A full Postman collection is available inside:

docs/postman_collection_license_tracker.json


Import it into Postman to test:

Login

Upload certificate

Upload license

Owner download

Permission blocking

🎓 Why This Project Is Industry-Level

Owner-scoped permissions (real security)

Streaming file downloads (efficient)

Fully validated uploads

Automatic API documentation (OpenAPI)

Integration testing

Clean folder structure

Modular serializers & viewsets

Production-ready patterns