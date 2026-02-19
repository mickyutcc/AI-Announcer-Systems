import gradio as gr
from datetime import datetime

def render_admin_subscriptions(actions):
    """
    actions: dict containing callables:
      - list_pending() -> iterable of subscription objects
      - get_proof_url(sub_id) -> url
      - approve(sub_id) -> dict result
      - reject(sub_id, reason) -> dict result
    """
    with gr.Column():
        gr.Markdown("## Pending Subscriptions")
        refresh_btn = gr.Button("Refresh list")
        pending_df = gr.Dataframe(
            headers=["ID", "User", "Plan", "Submitted At", "Proof URL"],
            datatype=["number", "number", "str", "str", "str"],
            row_count=10,
            interactive=False
        )
        with gr.Row():
            selected_id = gr.Number(label="Subscription ID", value=None, precision=0)
            view_proof_btn = gr.Button("View proof")
        
        with gr.Row():
            approve_btn = gr.Button("Approve", variant="primary")
            reject_btn = gr.Button("Reject", variant="stop")
        
        reject_reason = gr.Textbox(label="Reject reason", lines=2)
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
                rows.append([0, 0, "Error", str(e), ""])
            return rows

        def view_proof(sub_id):
            if not sub_id:
                return "Please enter subscription ID"
            try:
                return actions["get_proof_url"](int(sub_id))
            except Exception as e:
                return f"Error: {str(e)}"

        def do_approve(sub_id):
            if not sub_id:
                return "Enter subscription ID" # Return string for Markdown? The snippet returned dict/string mixed.
            # The snippet had: return actions["approve"](int(sub_id))
            # But the click output is admin_msg (Markdown). Markdown expects string.
            # The handlers return dict {"ok": bool, "msg": str}.
            # I should format it.
            try:
                res = actions["approve"](int(sub_id))
                if isinstance(res, dict) and "msg" in res:
                    return f"**{res.get('status', 'Result')}**: {res['msg']}"
                return str(res)
            except Exception as e:
                return f"Error: {str(e)}"

        def do_reject(sub_id, reason):
            if not sub_id:
                return "Enter subscription ID"
            if not reason:
                return "Provide reason for rejection"
            try:
                res = actions["reject"](int(sub_id), reason)
                if isinstance(res, dict) and "msg" in res:
                    return f"**{res.get('status', 'Result')}**: {res['msg']}"
                return str(res)
            except Exception as e:
                return f"Error: {str(e)}"

        refresh_btn.click(lambda: load_pending(), inputs=None, outputs=[pending_df])
        view_proof_btn.click(view_proof, inputs=[selected_id], outputs=[admin_msg])
        approve_btn.click(do_approve, inputs=[selected_id], outputs=[admin_msg])
        reject_btn.click(do_reject, inputs=[selected_id, reject_reason], outputs=[admin_msg])
        
        # Initial load
        # pending_df.value = load_pending() # Gradio doesn't support this directly usually, need load event.
        # But we can leave it empty until refresh.

    return
