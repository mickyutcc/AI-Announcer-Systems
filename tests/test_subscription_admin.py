import pytest
import sys
import os

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from types import SimpleNamespace
import handlers_subscription_manual as create_h
import handlers_subscription_admin as admin_h
from models import SubscriptionStatus

# reuse Dummy classes similar to tests/test_subscription_manual.py
class DummyStorage:
    def upload_bytes(self, key, bts, content_type=None):
        return f"https://storage/{key}"

class DummyDBSession:
    def __init__(self):
        self._rows = {}
        self._id = 1
    def add(self, obj):
        obj.id = self._id
        self._rows[self._id] = obj
        self._id += 1
    def commit(self):
        pass
    def rollback(self):
        pass
    def refresh(self, obj):
        pass
    def query(self, model):
        class Q:
            def __init__(self, rows):
                self._rows = rows
            def filter_by(self, **kwargs):
                id_ = kwargs.get("id")
                # If id is not provided, try other filters or just return all?
                # For admin_approve_subscription, we specifically use filter_by(id=subscription_id)
                # For create_subscription_request, we use filter_by(user_id=..., status=...)
                
                # Let's handle both cases simply for this test context
                filtered_rows = []
                
                # Special handling for id lookup (admin handler)
                if id_:
                    res = self._rows.get(id_)
                    class One:
                        def __init__(self, item):
                            self.item = item
                        def with_for_update(self):
                            return self
                        def one_or_none(self):
                            return self.item
                    return One(res)
                
                # Special handling for user_id/status lookup (create handler)
                # create handler calls .first() on result of filter_by
                # We need to return an object that supports .first()
                
                # Naive filter implementation
                candidates = list(self._rows.values())
                for k, v in kwargs.items():
                    candidates = [r for r in candidates if getattr(r, k, None) == v]
                
                class ResultList:
                    def __init__(self, items):
                        self.items = items
                    def first(self):
                        return self.items[0] if self.items else None
                    def with_for_update(self):
                        return self
                    def one_or_none(self):
                        return self.items[0] if len(self.items) == 1 else None

                return ResultList(candidates)

            def with_for_update(self):
                return self
                
        return Q(self._rows)

class DummyFile:
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content
        self.content_type = "image/png"
    def read(self):
        return self._content

class DummyUserDB:
    def __init__(self):
        self.credits = {}
    def increment_credits(self, user_id, amount):
        self.credits[user_id] = self.credits.get(user_id, 0) + amount
    def add_gg(self, user_id, amount, tx_type=None, description=None):
        self.credits[user_id] = self.credits.get(user_id, 0) + amount

def test_full_manual_subscription_approve_flow():
    storage = DummyStorage()
    db = DummyDBSession()
    user_db = DummyUserDB()
    file_obj = DummyFile("slip.png", b"validslipdata_longer_than_16_bytes")

    # create subscription request
    res = create_h.create_subscription_request(user_id=1, plan="standard", payment_ref="REF123", file_obj=file_obj, db_session=db, storage=storage, source_ip="1.1.1.1")
    
    assert res["status"] == "PENDING"
    sid = res["subscription_id"]

    # approve via admin handler
    out = admin_h.admin_approve_subscription(admin_id=99, subscription_id=sid, db_session=db, user_db=user_db)
    assert out["ok"] is True
    
    # Verify subscription state
    sub = db._rows[sid]
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.approved_by == 99
    
    # credits should have been added
    # Standard plan = 2000 GG
    assert user_db.credits.get(1, 0) == 2000
