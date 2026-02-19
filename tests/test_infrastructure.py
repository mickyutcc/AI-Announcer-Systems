import os
import unittest
from unittest.mock import patch, MagicMock
from cache_helper import InMemoryCache, get_cache
from storage import get_storage, LocalStorage
from notifications import send_slack, send_email

class TestInfrastructure(unittest.TestCase):
    def test_in_memory_cache(self):
        cache = InMemoryCache()
        cache.set("foo", "bar", ttl=1)
        self.assertEqual(cache.get("foo"), "bar")
        
        # Test delete
        cache.delete("foo")
        self.assertIsNone(cache.get("foo"))

    def test_get_storage_fallback(self):
        # Ensure we get LocalStorage when S3 is not configured
        with patch.dict(os.environ, {"STORAGE_TYPE": "s3", "S3_BUCKET": ""}):
            # Should warn and fallback
            s = get_storage()
            self.assertIsInstance(s, LocalStorage)
            
    def test_send_slack_no_url(self):
        # Should return False if URL is not set
        with patch("notifications.SLACK_WEBHOOK_URL", ""):
            res = send_slack("hello")
            self.assertFalse(res)

    @patch("notifications.requests.post")
    def test_send_slack_success(self, mock_post):
        mock_post.return_value.status_code = 200
        with patch("notifications.SLACK_WEBHOOK_URL", "http://fake"):
            res = send_slack("hello")
            self.assertTrue(res)

    def test_send_email_missing_config(self):
        # Should return False if config is missing
        with patch("notifications.SMTP_HOST", ""):
            res = send_email("test@example.com", "Subj", "Body")
            self.assertFalse(res)
