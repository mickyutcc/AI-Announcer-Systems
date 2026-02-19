
import unittest
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from database_setup import engine, SessionLocal
from models import Subscription, SubscriptionStatus
import user_db

class TestSubscriptionModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create tables
        from database_setup import Base
        Base.metadata.create_all(bind=engine)
        
        # Ensure a test user exists
        user_db.init_db()
        success, msg = user_db.register_user("test_sub_user", "password123", "Test User", "test@example.com")
        if not success and "already exists" not in msg and "ใช้แล้ว" not in msg:
             # If failed for other reasons, we might have issues, but let's try login anyway
             pass
        
        user_id, _ = user_db.login_user("test_sub_user", "password123")
        cls.user_id = user_id
        if not cls.user_id:
            raise Exception("Could not login test user")
        
        cls.session = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        # Clean up test user (optional, might affect other tests if running in suite)
        # But for this script, it's fine.

    def test_create_subscription(self):
        # Create a subscription
        sub = Subscription(
            user_id=self.user_id,
            plan="pro",
            status=SubscriptionStatus.PENDING,
            payment_amount=1000,
            payment_ref="TX123456",
            proof_path="/path/to/slip.jpg"
        )
        self.session.add(sub)
        self.session.commit()
        self.session.refresh(sub)
        
        self.assertIsNotNone(sub.id)
        self.assertEqual(sub.user_id, self.user_id)
        self.assertEqual(sub.plan, "pro")
        self.assertEqual(sub.status, SubscriptionStatus.PENDING)
        
        self.sub_id = sub.id

    def test_activate_subscription(self):
        # Retrieve the subscription created in previous test
        # Since tests might run in any order, better to create a new one here or rely on DB state
        # But for simplicity, let's create a new one
        sub = Subscription(
            user_id=self.user_id,
            plan="standard",
            status=SubscriptionStatus.PENDING
        )
        self.session.add(sub)
        self.session.commit()
        
        # Activate
        sub.activate_for_period(days=30)
        self.session.commit()
        self.session.refresh(sub)
        
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        self.assertIsNotNone(sub.current_period_start)
        self.assertIsNotNone(sub.current_period_end)
        
        # Check duration
        duration = sub.current_period_end - sub.current_period_start
        self.assertAlmostEqual(duration.total_seconds(), 30 * 24 * 3600, delta=60)

    def test_query_subscription(self):
        # Create a subscription first to ensure one exists for query
        sub_new = Subscription(
            user_id=self.user_id,
            plan="easy",
            status=SubscriptionStatus.ACTIVE
        )
        self.session.add(sub_new)
        self.session.commit()

        # Query existing subscription
        sub = self.session.query(Subscription).filter_by(user_id=self.user_id, plan="easy").first()
        self.assertIsNotNone(sub)
        if sub:
            self.assertEqual(sub.user_id, self.user_id)

if __name__ == "__main__":
    unittest.main()
