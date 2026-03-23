import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings, TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


@override_settings()
class FilePermissionTests(TestCase):
    """
    Integration tests for upload -> download permissions for Certificate and License.
    Uses a temporary MEDIA_ROOT so files are written to a temp folder and cleaned up.
    """

    def setUp(self):
        # temp media root
        self._media_dir = tempfile.mkdtemp(prefix="test_media_")
        # override MEDIA_ROOT for the duration of tests
        self.override = override_settings(MEDIA_ROOT=self._media_dir)
        self.override.enable()

        # create two users
        self.user_a = User.objects.create_user(username="user_a", password="passA")
        self.user_b = User.objects.create_user(username="user_b", password="passB")

        # API client
        self.client = APIClient()

    def tearDown(self):
        # cleanup temp media directory
        self.override.disable()
        shutil.rmtree(self._media_dir, ignore_errors=True)

    def _upload_certificate(self, client, title="Test Cert"):
        """
        Helper: upload a small fake PDF for certificate and return created object id.
        """
        content = b"%PDF-1.4 test pdf content\n%%EOF"
        uploaded = SimpleUploadedFile("test_cert.pdf", content, content_type="application/pdf")
        data = {
            "title": title,
            "issued_date": "2020-01-01",
            "file": uploaded
        }
        # POST to certificates endpoint
        resp = client.post("/api/certificates/", data, format="multipart")
        self.assertIn(resp.status_code, (200, 201), msg=f"Unexpected upload status: {resp.status_code}, body: {getattr(resp, 'content', resp.data if hasattr(resp, 'data') else resp)}")
        body = resp.json()
        self.assertIn("id", body, msg=f"Upload response missing id: {body}")
        return body["id"], content

    def _upload_license(self, client, name="Driver License"):
        """
        Helper: upload a small fake PDF for license and return created object id.
        """
        content = b"%PDF-1.4 test license pdf\n%%EOF"
        uploaded = SimpleUploadedFile("test_license.pdf", content, content_type="application/pdf")
        data = {
            "name": name,
            "file": uploaded
        }
        resp = client.post("/api/licenses/", data, format="multipart")
        self.assertIn(resp.status_code, (200, 201), msg=f"Unexpected upload status: {resp.status_code}, body: {getattr(resp, 'content', resp.data if hasattr(resp, 'data') else resp)}")
        body = resp.json()
        self.assertIn("id", body, msg=f"Upload response missing id: {body}")
        return body["id"], content

    def _get_response_bytes(self, resp):
        """
        Utility to extract bytes from both streaming (FileResponse) and regular responses.
        """
        # For streaming responses (FileResponse), use streaming_content iterator
        if hasattr(resp, "streaming_content"):
            # streaming_content may be an iterator of bytes chunks
            return b"".join(chunk for chunk in resp.streaming_content)
        # fallback: regular response
        return getattr(resp, "content", b"")

    def test_certificate_upload_and_access_permissions(self):
        # authenticate as user_a and upload
        self.client.force_authenticate(user=self.user_a)
        cert_id, expected_bytes = self._upload_certificate(self.client)

        # owner download should succeed (200) and bytes should match
        download_url = f"/api/certificates/{cert_id}/download/"
        resp = self.client.get(download_url, format="json")
        self.assertEqual(resp.status_code, 200, msg=f"Owner download failed: {resp.status_code}, body: {getattr(resp, 'content', resp.data if hasattr(resp, 'data') else resp)}")

        content_bytes = self._get_response_bytes(resp)
        self.assertTrue(
            content_bytes.startswith(expected_bytes[:8]) or expected_bytes in content_bytes,
            msg="Downloaded certificate content does not match uploaded content."
        )

        # authenticate as user_b and try to download (should be blocked -> 403 or 404)
        self.client.force_authenticate(user=self.user_b)
        resp2 = self.client.get(download_url, format="json")
        self.assertIn(resp2.status_code, (403, 404), msg=f"Non-owner should be blocked, got {resp2.status_code}")

    def test_license_upload_and_access_permissions(self):
        # authenticate as user_a and upload license
        self.client.force_authenticate(user=self.user_a)
        lic_id, expected_bytes = self._upload_license(self.client)

        # owner download should succeed
        download_url = f"/api/licenses/{lic_id}/download/"
        resp = self.client.get(download_url, format="json")
        self.assertEqual(resp.status_code, 200, msg=f"Owner license download failed: {resp.status_code}, body: {getattr(resp, 'content', resp.data if hasattr(resp, 'data') else resp)}")

        content_bytes = self._get_response_bytes(resp)
        self.assertTrue(
            content_bytes.startswith(expected_bytes[:8]) or expected_bytes in content_bytes,
            msg="Downloaded license content does not match uploaded content."
        )

        # user_b should be blocked (403 or 404)
        self.client.force_authenticate(user=self.user_b)
        resp2 = self.client.get(download_url, format="json")
        self.assertIn(resp2.status_code, (403, 404), msg=f"Non-owner should be blocked for license, got {resp2.status_code}")
