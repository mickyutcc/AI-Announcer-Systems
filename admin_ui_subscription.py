import gradio as gr
from datetime import datetime
from locales import t

def render_admin_subscriptions(actions):
    """
    actions: dict containing callables:
      - list_pending() -> iterable of subscription objects
      - get_proof_url(sub_id) -> url
      - approve(sub_id) -> dict result
      - reject(sub_id, reason) -> dict result
    """
    with gr.Column():
        gr.Markdown(t("admin_pending_subs"))
        refresh_btn = gr.Button(t("refresh_list"))
        pending_df = gr.Dataframe(
            headers=[t("col_id"), t("col_username"), t("col_plan"), t("col_submitted_at"), t("col_proof_url")],
            datatype=["number", "number", "str", "str", "str"],
            row_count=10,
            interactive=False
        )
        with gr.Row():
            selected_id = gr.Number(label=t("subscription_id"), value=None, precision=0)
            view_proof_btn = gr.Button(t("view_proof"))
        
        with gr.Row():
            approve_btn = gr.Button(t("approve"), variant="primary")
            reject_btn = gr.Button(t("reject"), variant="stop")
        
        reject_reason = gr.Textbox(label=t("reject_reason"), lines=2)
        admin_msg = gr.Markdown("")

        def load_pending():
            rows = []
            try:
                subscriptions = actions["list_pending"]()
                for s in subscriptions:
                    ts = s.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(s, "created_at") and s.created_at else ""
                    # s.proof_path might be None
                    proof = s.proof_path if s.proof_path else ""
                    rows.append([s.id, s.user_id, s.plan, ts, proof])
            except Exception as e:
                rows.append([0, 0, t("err_label"), str(e), ""])
            return rows

        def view_proof(sub_id):
            if not sub_id:
                return t("msg_enter_sub_id")
            try:
                return actions["get_proof_url"](int(sub_id))
            except Exception as e:
                return t("err_general").format(error=str(e))

        def do_approve(sub_id):
            if not sub_id:
                return t("msg_enter_sub_id")
            # The snippet had: return actions["approve"](int(sub_id))
            # But the click output is admin_msg (Markdown). Markdown expects string.
            # The handlers return dict {"ok": bool, "msg": str}.
            # I should format it.
            try:
                res = actions["approve"](int(sub_id))
                if isinstance(res, dict) and "msg" in res:
                    return f"**{res.get('status', t('result_label'))}**: {res['msg']}"
                return str(res)
            except Exception as e:
                return t("err_general").format(error=str(e))

        def do_reject(sub_id, reason):
            if not sub_id:
                return t("msg_enter_sub_id")
            if not reason:
                return t("msg_provide_reason")
            try:
                res = actions["reject"](int(sub_id), reason)
                if isinstance(res, dict) and "msg" in res:
                    return f"**{res.get('status', t('result_label'))}**: {res['msg']}"
                return str(res)
            except Exception as e:
                return t("err_general").format(error=str(e))

        refresh_btn.click(lambda: load_pending(), inputs=None, outputs=[pending_df])
        view_proof_btn.click(view_proof, inputs=[selected_id], outputs=[admin_msg])
        approve_btn.click(do_approve, inputs=[selected_id], outputs=[admin_msg])
        reject_btn.click(do_reject, inputs=[selected_id, reject_reason], outputs=[admin_msg])
        
        # Initial load
        # pending_df.value = load_pending() # Gradio doesn't support this directly usually, need load event.
        # But we can leave it empty until refresh.

    return
