import gradio as gr 
from locales import t

def render_admin_subscriptions_wired(actions): 
    """ 
    actions: AdminActions instance 
    """ 
    with gr.Column(): 
        gr.Markdown(t("admin_pending_subs")) 
        refresh_btn = gr.Button(t("refresh")) 
        pending_df = gr.Dataframe(headers=[t("col_id"), t("col_username"), t("col_plan"), t("col_submitted_at"), t("col_proof_url")], row_count=10, interactive=False) 
        
        with gr.Row():
            selected_id = gr.Number(label=t("subscription_id"), value=None) 
            view_proof_btn = gr.Button(t("view_proof")) 
        
        with gr.Row():
            approve_btn = gr.Button(t("approve")) 
            reject_btn = gr.Button(t("reject")) 
        
        reject_reason = gr.Textbox(label=t("reject_reason"), lines=2) 
        admin_msg = gr.Markdown("") 


        def load_pending(): 
            rows = [] 
            try:
                pending = actions.list_pending()
                for s in pending: 
                    ts = s.created_at.strftime("%Y-%m-%d %H:%M") if getattr(s, "created_at", None) else "" 
                    rows.append([s.id, s.user_id, s.plan, ts, s.proof_path]) 
            except Exception as e:
                rows.append([0, 0, t("err_label"), str(e), ""])
            return rows 

        def view_proof(sub_id): 
            if not sub_id: 
                return t("msg_enter_sub_id")
            try:
                return actions.get_proof_url(int(sub_id)) 
            except Exception as e:
                return t("err_general").format(error=str(e))

        def do_approve(sub_id): 
            if not sub_id: 
                return t("msg_enter_sub_id")
            try:
                res = actions.approve(admin_id=0, sub_id=int(sub_id)) 
                return t("msg_result").format(result=res)
            except Exception as e:
                return t("err_general").format(error=str(e))

        def do_reject(sub_id, reason): 
            if not sub_id: 
                return t("msg_enter_sub_id")
            if not reason: 
                return t("msg_provide_reason")
            try:
                res = actions.reject(admin_id=0, sub_id=int(sub_id), reason=reason) 
                return t("msg_result").format(result=res)
            except Exception as e:
                return t("err_general").format(error=str(e))

        # Note: The original snippet had lambda: load_pending() for inputs=None. 
        # Gradio inputs=None usually works with a function that takes no args.
        refresh_btn.click(load_pending, inputs=None, outputs=[pending_df]) 
        view_proof_btn.click(view_proof, inputs=[selected_id], outputs=[admin_msg]) 
        approve_btn.click(do_approve, inputs=[selected_id], outputs=[admin_msg]) 
        reject_btn.click(do_reject, inputs=[selected_id, reject_reason], outputs=[admin_msg]) 
    return
