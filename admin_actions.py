import logging 
from typing import List, Callable, Dict, Any 

from models_subscription import Subscription, SubscriptionStatus 
from handlers_subscription_admin import admin_approve_subscription, admin_reject_subscription 

logger = logging.getLogger(__name__) 

class AdminActions: 
    def __init__(self, db_session_factory: Callable[[], Any], storage, user_db, notify=None): 
        self.db_session_factory = db_session_factory 
        self.storage = storage 
        self.user_db = user_db 
        self.notify = notify or (lambda *a, **k: None) 

    def list_pending(self) -> List[Subscription]: 
        sess = self.db_session_factory() 
        try: 
            return sess.query(Subscription).filter_by(status=SubscriptionStatus.PENDING).all() 
        finally: 
            sess.close() 

    def get_proof_url(self, sub_id: int) -> str: 
        sess = self.db_session_factory() 
        try: 
            sub = sess.query(Subscription).filter_by(id=sub_id).one_or_none() 
            if not sub: 
                return "Not found" 
            if hasattr(self.storage, "get_signed_url"): 
                return self.storage.get_signed_url(sub.proof_path, expires=3600) 
            return sub.proof_path 
        finally: 
            sess.close() 

    def approve(self, admin_id: int, sub_id: int) -> Dict[str, Any]: 
        sess = self.db_session_factory() 
        try: 
            res = admin_approve_subscription(admin_id=admin_id, subscription_id=sub_id, db_session=sess, user_db=self.user_db) 
            return res 
        finally: 
            try: 
                sess.close() 
            except Exception: 
                pass 

    def reject(self, admin_id: int, sub_id: int, reason: str) -> Dict[str, Any]: 
        sess = self.db_session_factory() 
        try: 
            res = admin_reject_subscription(admin_id=admin_id, subscription_id=sub_id, reason=reason, db_session=sess) 
            return res 
        finally: 
            try: 
                sess.close() 
            except Exception: 
                pass
