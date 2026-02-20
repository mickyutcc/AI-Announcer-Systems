import logging
import os
import shutil
import uuid
import time
from datetime import datetime
from typing import Optional, Any, Dict, cast

from rate_limiter import rate_limit
from sqlalchemy.orm import Session
from database_setup import get_db
from models import Subscription, SubscriptionStatus, User
from config import PLANS
import config
from storage import storage as default_storage
import security_av
import prometheus_metrics
from locales import t

logger = logging.getLogger(__name__)

@rate_limit(key_fn=lambda user_id, *a, **k: f"subscription_submit:user:{user_id}", max_calls=5, period_seconds=3600)
def create_subscription_request(
    user_id: Optional[int] = None,
    plan: str = "",
    payment_ref: str = "",
    file_obj: Any = None,
    db_session: Any = None,
    storage: Any = None,
    source_ip: str = "",
    # Backwards compatibility / Alternative usage
    username: Optional[str] = None,
    plan_key: Optional[str] = None,
    slip_file_path: Optional[str] = None,
    payment_amount: Optional[int] = None
) -> Dict[str, Any]:
    """
    Creates a new subscription request with PENDING status and uploads the payment slip.
    Supports both dependency injection (for testing) and direct usage.
    """
    # 0. Normalize arguments
    if plan_key and not plan:
        plan = plan_key
    
    # Resolve Storage
    storage_svc = storage if storage else default_storage
    
    # Resolve DB Session
    # If db_session is provided, use it. Else create a new one.
    local_session = False
    session = db_session
    if session is None:
        session = next(get_db())
        local_session = True
        
    try:
        # 1. Resolve User ID if not provided
        if user_id is None:
            if not username:
                return {"status": "ERROR", "message": t("err_user_id_req")}
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return {"status": "ERROR", "message": t("err_user_not_found_val").format(username=username)}
            user_id = cast(int, user.id)
        
        # 2. Validate Plan
        if plan not in PLANS:
            return {"status": "ERROR", "message": t("err_invalid_plan").format(plan=plan)}
        
        plan_info = PLANS[plan]
        plan_price = plan_info.get("price_thb")
        
        if not isinstance(plan_price, (int, float)):
            return {"status": "ERROR", "message": t("err_plan_no_manual").format(plan_name=plan_info.get('name', plan))}
        
        final_amount = payment_amount if payment_amount is not None else int(plan_price)
        
        # 3. Check for existing PENDING request
        existing_request = session.query(Subscription).filter_by(
            user_id=user_id,
            status=SubscriptionStatus.PENDING
        ).first()
        
        if existing_request:
             return {"status": "ERROR", "message": t("err_pending_exists")}

        # 4. Handle File Upload
        file_data: Optional[bytes] = None
        original_name = "slip.jpg"
        
        if file_obj:
            if hasattr(file_obj, "read"):
                data = file_obj.read()
                if isinstance(data, str):
                    file_data = data.encode()
                elif isinstance(data, (bytes, bytearray, memoryview)):
                    file_data = bytes(data)
                else:
                    file_data = None
                if hasattr(file_obj, "filename") and file_obj.filename:
                    original_name = file_obj.filename
                elif hasattr(file_obj, "name") and file_obj.name:
                    original_name = os.path.basename(file_obj.name)
            else:
                if isinstance(file_obj, str):
                    file_data = file_obj.encode()
                elif isinstance(file_obj, (bytes, bytearray, memoryview)):
                    file_data = bytes(file_obj)
                else:
                    file_data = None
        elif slip_file_path:
            if os.path.exists(slip_file_path):
                original_name = os.path.basename(slip_file_path)
                with open(slip_file_path, "rb") as f:
                    file_data = f.read()
        
        if not file_data or len(file_data) < 16:
             return {"status": "ERROR", "message": t("err_slip_invalid")}

        # --- Security Scan (Enhanced) ---
        try:
            scan_res = security_av.scan_bytes(file_data)
            status = scan_res.get("status")
            if status == "infected":
                logger.warning("Upload rejected: infected file: %s", scan_res.get("detail"))
                return {"status": "ERROR", "message": t("err_security_virus")}
            elif status == "error":
                logger.warning("AV scan error: %s (strict=%s)", scan_res.get("detail"), getattr(config, "AV_STRICT", False))
                if getattr(config, "AV_STRICT", False):
                    return {"status": "ERROR", "message": t("err_security_error")}
            elif status == "unavailable":
                logger.warning("AV scan unavailable: %s (strict=%s)", scan_res.get("detail"), getattr(config, "AV_STRICT", False))
                if getattr(config, "AV_STRICT", False):
                    return {"status": "ERROR", "message": t("err_security_unavailable")}
            # else clean -> continue
        except Exception as e:
            logger.exception("Unexpected AV scan error")
            if getattr(config, "AV_STRICT", False):
                return {"status": "ERROR", "message": t("err_security_unexpected")}
        # ---------------------

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(original_name)[1].lower()
        if not ext:
            ext = ".jpg"
        
        # Sanitize extension
        if ext not in [".jpg", ".jpeg", ".png", ".pdf"]:
             return {"status": "ERROR", "message": t("err_file_type")}

        unique_name = f"{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
        object_key = f"slips/{user_id}/{unique_name}"
        
        # Upload
        saved_path = storage_svc.upload_bytes(object_key, cast(bytes, file_data))
        
        if not saved_path:
             return {"status": "ERROR", "message": t("err_save_slip_failed")}
            
        # Create Subscription Record
        new_sub = Subscription(
            user_id=user_id,
            plan=plan,
            status=SubscriptionStatus.PENDING,
            payment_amount=final_amount,
            payment_ref=payment_ref,
            proof_path=object_key,
            created_at=datetime.utcnow()
        )
        
        session.add(new_sub)
        session.commit()
        # Refresh to get ID if possible, though mocks might not support it fully
        try:
            session.refresh(new_sub)
        except:
            pass
        
        logger.info(f"Created subscription request for user ID {user_id}, Plan: {plan}")
        
        # Metrics
        prometheus_metrics.PENDING_GAUGE.inc()

        return {
            "status": "PENDING",
            "subscription_id": new_sub.id,
            "message": t("success_sub_submitted")
        }
            
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating subscription request: {e}")
        return {"status": "ERROR", "message": t("err_create_sub").format(error=str(e))}
    finally:
        if local_session:
            session.close()

def approve_subscription(
    subscription_id: int,
    admin_id: int,
    db_session: Any = None,
    user_db_module: Any = None
) -> Dict[str, Any]:
    """
    Approves a pending subscription request.
    """
    local_session = False
    session = db_session
    if session is None:
        session = next(get_db())
        local_session = True
        
    try:
        sub = cast(Any, session.query(Subscription).filter_by(id=subscription_id).with_for_update().one_or_none())
        if not sub:
            return {"status": "ERROR", "message": t("err_sub_not_found")}
            
        if sub.status != SubscriptionStatus.PENDING:
            return {"status": "ERROR", "message": t("err_sub_status_invalid").format(status=sub.status)}
            
        # Update status
        sub.status = SubscriptionStatus.ACTIVE
        sub.approved_by = admin_id
        sub.approved_at = datetime.utcnow()

        # Metrics
        try:
            prometheus_metrics.APPROVE_TOTAL.inc()
            prometheus_metrics.PENDING_GAUGE.dec()
            if sub.created_at:
                latency = (sub.approved_at - sub.created_at).total_seconds()
                prometheus_metrics.APPROVAL_LATENCY.observe(latency)
        except Exception as e:
            logger.error(f"Error recording metrics: {e}")
        
        # Add credits/plan logic here?
        # The user provided DummyUserDB implies we need to update credits
        # We need to access user_db logic.
        
        # If user_db_module is injected, use it. Else import global.
        if user_db_module:
            udb: Any = user_db_module
        else:
            import user_db as default_user_db
            udb = default_user_db
        
        # Add plan credits
        sub_plan = cast(str, sub.plan)
        if sub_plan in PLANS:
            plan_data = PLANS[sub_plan]
            # Handle credit addition
            # Assuming 'gg_amount' in plan data
            gg_amount = plan_data.get("gg_amount", 0)
            if isinstance(gg_amount, int) and gg_amount > 0:
                if hasattr(udb, "increment_credits"):
                    udb.increment_credits(cast(int, sub.user_id), gg_amount)
                elif hasattr(udb, "add_gg"):
                    udb.add_gg(cast(int, sub.user_id), gg_amount, tx_type="subscription_approved", description=t("tx_sub_approved").format(plan=sub_plan))
                else:
                    # Fallback or log error
                    logger.error(f"Cannot add credits: user_db module has no known credit method")
                    return {"status": "ERROR", "message": t("err_credit_method_missing")}
                
            # Update user level/plan in user_db? 
            # user_db usually manages level separately. 
            # We might need to call set_user_level or similar if available.
            # But based on the prompt's mock, only increment_credits is shown.
        
        session.commit()
        
        return {"status": "APPROVED", "subscription_id": sub.id}
        
    except Exception as e:
        session.rollback()
        return {"status": "ERROR", "message": str(e)}
    finally:
        if local_session:
            session.close()
