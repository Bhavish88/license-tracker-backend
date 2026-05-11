# 📘 License & Certificate Tracker

A secure full-stack web application for uploading, organizing, and tracking licenses and certificates with expiry reminders and owner-based access control.

## 🚀 Features

- JWT Authentication using SimpleJWT
- Upload and manage certificates/licenses
- Owner-based secure file access
- Expiry tracking and reminders
- Dashboard summary APIs
- Swagger & Redoc API documentation
- Integration testing for file permissions
- Secure file validation and storage

---

## 🛠 Tech Stack

| Area | Technology |
|------|-------------|
| Backend | Django, Django REST Framework |
| Authentication | SimpleJWT |
| Database | MySQL |
| API Docs | drf-spectacular |
| Testing | Django TestCase |

---

## 📂 API Documentation

| Tool | URL |
|------|-----|
| Swagger UI | `/api/docs/` |
| Redoc | `/api/redoc/` |
| OpenAPI Schema | `/api/schema/` |

---

## ▶️ Running the Project

### Install dependencies

```bash
pip install -r requirements.txt
```

### Apply migrations

```bash
python manage.py migrate
```

### Run server

```bash
python manage.py runserver
```

Server runs at:

```text
http://localhost:8000/api/
```

---

## 🔐 Authentication

Generate JWT token:

```http
POST /api/token/
```

Use token in requests:

```http
Authorization: Bearer <access_token>
```

---

## 📤 Secure File Access

Only the owner of a document can access or download uploaded files.

Unauthorized users receive:

```http
403 Forbidden
```

---

## 🧪 Running Tests

```bash
python manage.py test tracker.tests.test_file_permissions -v2
```

---

## 🎯 Key Highlights

- Secure owner-scoped permissions
- Private file storage
- Production-style API structure
- Automatic OpenAPI documentation
- Modular serializers and viewsets
- Industry-style backend architecture
