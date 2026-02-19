import logging
from datetime import datetime
from typing import Dict, Any, List
import sentry_sdk

from models import Subscription, SubscriptionStatus
from config import PLANS, ASSETS_DIR
from prometheus_metrics import observe_approval_latency, inc_approve, inc_reject
from notifications import notify_admins_new_subscription, notify_user_subscription_approved, notify_user_subscription_rejected

logger = logging.getLogger(__name__)

ALERT_APPROVAL_LATENCY_SECONDS = 24 * 3600  # example: alert if > 24 hours

def list_pending_subscriptions(db_session) -> List[Subscription]:
    return db_session.query(Subscription).filter_by(status=SubscriptionStatus.PENDING).order_by(Subscription.created_at.desc()).all()

def get_proof_url(subscription_id: int, db_session) -> str:
    sub = db_session.query(Subscription).filter_by(id=subscription_id).one_or_none()
    if not sub:
        return "Subscription not found"
    
    if not sub.proof_path:
        return "No proof uploaded"
    
    import os
    abs_path = os.path.join(ASSETS_DIR, sub.proof_path)
    if not os.path.exists(abs_path):
        return f"File not found on server: {sub.proof_path}"
    
    return f"![Proof](/file={abs_path})"

def admin_approve_subscription(admin_id: int, subscription_id: int, db_session, user_db, period_days: int = 30) -> Dict[str, Any]:
    """
    Approve a pending subscription and credit user via user_db.add_gg(...)
    """
    try:
        sub = db_session.query(Subscription).filter_by(id=subscription_id).with_for_update().one_or_none()
        if not sub:
            return {"ok": False, "msg": "Subscription not found"}
        if sub.status != SubscriptionStatus.PENDING:
            return {"ok": False, "msg": f"Subscription not pending (status={sub.status})"}

        # compute approval latency
        now = datetime.utcnow()
        created_at = sub.created_at or now
        latency = (now - created_at).total_seconds()

        # Activate and bookkeeping
        sub.activate_for_period(days=period_days)
        sub.approved_by = admin_id
        sub.approved_at = now

        # Determine credits
        credits = 0
        if sub.plan in PLANS:
            credits = int(PLANS[sub.plan].get("gg_amount", 0))
        else:
            # Fallback map from user snippet
            PLAN_MAP = {
                "standard": {"credits": 2000},
                "pro": {"credits": 6900},
            }
            plan_info = PLAN_MAP.get(sub.plan)
            if plan_info:
                credits = plan_info["credits"]
            else:
                db_session.commit()
                return {"ok": False, "msg": f"Unknown plan: {sub.plan}"}

        # Use your user_db API: add_gg(user_id, amount, tx_type=..., description=...)
        user_db.add_gg(sub.user_id, credits, tx_type="subscription", description=f"{sub.plan} subscription approval")

        db_session.commit()

        # metrics + notifications
        observe_approval_latency(latency)
        inc_approve()

        # if latency exceeds threshold, notify and create Sentry warning
        if latency > ALERT_APPROVAL_LATENCY_SECONDS:
            sentry_sdk.capture_message(f"High subscription approval latency: {latency} sec for sub_id={sub.id}", level="warning")
            # also send slack/email via notifications
            try:
                # proof_path might be None if old record
                proof = sub.proof_path or "No proof"
                notify_admins_new_subscription(sub.id, sub.user_id, sub.plan, proof, note=f"High approval latency: {latency}s")
            except Exception:
                logger.exception("Failed to send high-latency notification")

        notify_user_subscription_approved(sub.user_id, sub.plan, credits)
        logger.info("Subscription approved", extra={"sub_id": sub.id, "user_id": sub.user_id, "credits": credits})
        return {"ok": True, "msg": "Approved"}
    except Exception as exc:
        logger.exception("Failed to approve subscription")
        try:
            db_session.rollback()
        except Exception:
            logger.exception("Failed to rollback after approve error")
        return {"ok": False, "msg": f"Internal error: {exc}"}

def admin_reject_subscription(admin_id: int, subscription_id: int, reason: str, db_session, logger=logging.getLogger(__name__)) -> Dict[str, Any]:
    try:
        sub = db_session.query(Subscription).filter_by(id=subscription_id).one_or_none()
        if not sub:
            return {"ok": False, "msg": "Subscription not found"}
        if sub.status != SubscriptionStatus.PENDING:
            return {"ok": False, "msg": f"Subscription not pending (status={sub.status})"}

        sub.status = SubscriptionStatus.REJECTED
        sub.rejected_by = admin_id
        sub.rejected_at = datetime.utcnow()
        sub.reject_reason = reason

        db_session.commit()

        inc_reject()
        notify_user_subscription_rejected(sub.user_id, reason)
        logger.info("Subscription rejected", extra={"sub_id": sub.id, "user_id": sub.user_id, "reason": reason})
        return {"ok": True, "msg": "Rejected"}
    except Exception as exc:
        logger.exception("Failed to reject subscription")
        try:
            db_session.rollback()
        except Exception:
            logger.exception("Failed to rollback after reject error")
        return {"ok": False, "msg": f"Internal error: {exc}"}
