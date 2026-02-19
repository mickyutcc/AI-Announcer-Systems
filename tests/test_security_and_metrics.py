import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import logging
from datetime import datetime
import time

# Add project root to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules to test
from handlers_subscription_manual import create_subscription_request, approve_subscription
from models import Subscription, SubscriptionStatus, User
import prometheus_metrics
from rate_limiter import rate_limit

# Configure logging to suppress output during tests
logging.basicConfig(level=logging.CRITICAL)

class TestSecurityAndMetrics(unittest.TestCase):
    
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_user = User(id=1, username="testuser")
        # Don't set global query return values here to avoid conflicts
        
        # Reset rate limiter store for each test
        from rate_limiter import _rate_store
        _rate_store.clear()

    def test_av_scan_infected(self):
        """Test that infected files are rejected."""
        # EICAR test string (standard antivirus test file)
        eicar_str = r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        
        with patch("handlers_subscription_manual.security_av.scan_bytes") as mock_scan:
            mock_scan.return_value = {"status": "infected", "detail": "Eicar-Test-Signature"}
            
            mock_file = MagicMock()
            mock_file.read.return_value = eicar_str.encode('utf-8')
            mock_file.filename = "eicar.com"
            
            # Ensure no existing pending request
            self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
            
            # Patch get_db to return our mock session
            with patch("handlers_subscription_manual.get_db", return_value=iter([self.mock_session])):
                result = create_subscription_request(
                    user_id=1,
                    plan="standard",
                    file_obj=mock_file,
                    db_session=self.mock_session,
                    payment_ref="ref123"
                )
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("status"), "ERROR")
            msg = result.get("message", "")
            self.assertIn("Security check failed", msg)
            self.assertIn("Virus detected", msg)
            
            # Verify scan was called
            mock_scan.assert_called_once()

    def test_rate_limiter_memory(self):
        """Test in-memory rate limiter enforcement."""
        # Define a dummy decorated function
        # limit: 2 calls per 60 seconds
        @rate_limit(key_fn=lambda *args: "test_key", max_calls=2, period_seconds=60)
        def dummy_func():
            return {"status": "OK"}

        # Force in-memory by mocking _get_redis_client to return None
        with patch("rate_limiter._get_redis_client", return_value=None):
            # 1st call -> ok
            self.assertEqual(dummy_func().get("status"), "OK")
            # 2nd call -> ok
            self.assertEqual(dummy_func().get("status"), "OK")
            # 3rd call -> error
            res = dummy_func()
            self.assertIsInstance(res, dict)
            self.assertEqual(res.get("status"), "ERROR")
            self.assertIn("Rate limit exceeded", res.get("message", ""))

    def test_metrics_approve(self):
        """Test that approval metrics are incremented."""
        # Get initial counter value
        initial_approve = list(prometheus_metrics.APPROVE_TOTAL.collect())[0].samples[0].value
        initial_pending = list(prometheus_metrics.PENDING_GAUGE.collect())[0].samples[0].value
        
        # Setup mock subscription
        mock_sub = Subscription(
            id=101,
            user_id=1,
            plan="standard",
            status=SubscriptionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        self.mock_session.query.return_value.filter_by.return_value.with_for_update.return_value.one_or_none.return_value = mock_sub
        
        # Call approve
        mock_user_db = MagicMock()
        with patch("handlers_subscription_manual.get_db", return_value=iter([self.mock_session])):
            result = approve_subscription(
                subscription_id=101,
                admin_id=999,
                db_session=self.mock_session,
                user_db_module=mock_user_db
            )
        
        self.assertEqual(result.get("status"), "APPROVED")
        
        # Check metrics after
        final_approve = list(prometheus_metrics.APPROVE_TOTAL.collect())[0].samples[0].value
        final_pending = list(prometheus_metrics.PENDING_GAUGE.collect())[0].samples[0].value
        
        self.assertEqual(final_approve, initial_approve + 1)
        self.assertEqual(final_pending, initial_pending - 1)

if __name__ == "__main__":
    unittest.main()
