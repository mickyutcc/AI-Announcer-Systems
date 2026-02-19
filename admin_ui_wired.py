import gradio as gr 

def render_admin_subscriptions_wired(actions): 
    """ 
    actions: AdminActions instance 
    """ 
    with gr.Column(): 
        gr.Markdown("## Pending Subscriptions") 
        refresh_btn = gr.Button("Refresh") 
        pending_df = gr.Dataframe(headers=["ID","User","Plan","Submitted At","Proof URL"], row_count=10, interactive=False) 
        
        with gr.Row():
            selected_id = gr.Number(label="Subscription ID", value=None) 
            view_proof_btn = gr.Button("View proof") 
        
        with gr.Row():
            approve_btn = gr.Button("Approve") 
            reject_btn = gr.Button("Reject") 
        
        reject_reason = gr.Textbox(label="Reject reason", lines=2) 
        admin_msg = gr.Markdown("") 

        def load_pending(): 
            rows = [] 
            try:
                pending = actions.list_pending()
                for s in pending: 
                    ts = s.created_at.strftime("%Y-%m-%d %H:%M") if getattr(s, "created_at", None) else "" 
                    rows.append([s.id, s.user_id, s.plan, ts, s.proof_path]) 
            except Exception as e:
                # Fallback if list_pending fails
                rows.append([0, 0, "Error", str(e), ""])
            return rows 

        def view_proof(sub_id): 
            if not sub_id: 
                return "Please enter subscription ID" 
            try:
                return actions.get_proof_url(int(sub_id)) 
            except Exception as e:
                return f"Error: {str(e)}"

        def do_approve(sub_id): 
            if not sub_id: 
                return "Enter subscription ID" 
            try:
                res = actions.approve(admin_id=0, sub_id=int(sub_id)) 
                return f"Result: {res}"
            except Exception as e:
                return f"Error: {str(e)}"

        def do_reject(sub_id, reason): 
            if not sub_id: 
                return "Enter subscription ID" 
            if not reason: 
                return "Provide reason" 
            try:
                res = actions.reject(admin_id=0, sub_id=int(sub_id), reason=reason) 
                return f"Result: {res}"
            except Exception as e:
                return f"Error: {str(e)}"

        # Note: The original snippet had lambda: load_pending() for inputs=None. 
        # Gradio inputs=None usually works with a function that takes no args.
        refresh_btn.click(load_pending, inputs=None, outputs=[pending_df]) 
        view_proof_btn.click(view_proof, inputs=[selected_id], outputs=[admin_msg]) 
        approve_btn.click(do_approve, inputs=[selected_id], outputs=[admin_msg]) 
        reject_btn.click(do_reject, inputs=[selected_id, reject_reason], outputs=[admin_msg]) 
    return
