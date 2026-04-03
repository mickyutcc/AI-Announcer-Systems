import pytest 
from types import SimpleNamespace 
import sys
import os

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import handlers_subscription_manual as h 

class DummyStorage: 
    def upload_bytes(self, key, data, content_type=None): 
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
    def refresh(self, obj):
        pass
    def query(self, model): 
        class Q: 
            def __init__(self, rows): 
                self._rows = rows 
            def filter_by(self, **kwargs): 
                # Basic mock for filter_by(id=...)
                id_ = kwargs.get("id") 
                if id_ is not None:
                    res = self._rows.get(id_) 
                    class One: 
                        def one_or_none(self): 
                            return res 
                    return One()
                
                # Mock for filter_by(user_id=..., status=...) used in create_subscription_request
                # This needs to return an object with .first()
                class ResultList:
                    def first(self):
                        return None # Simulate no existing pending request
                    def one_or_none(self):
                        return None

                return ResultList()

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
    def add_gg(self, user_id, amount, tx_type=None, description=None): 
        self.credits[user_id] = self.credits.get(user_id, 0) + amount 

def test_create_subscription_request_success():
    storage = DummyStorage()
    db = DummyDBSession()
    file_obj = DummyFile("slip.png", b"validslipdata_longer_than_16_bytes")
    res = h.create_subscription_request(user_id=1, plan="standard", payment_ref="REF123", file_obj=file_obj, db_session=db, storage=storage, source_ip="1.1.1.1") 
    assert "subscription_id" in res 
    assert res["status"] == "PENDING"
