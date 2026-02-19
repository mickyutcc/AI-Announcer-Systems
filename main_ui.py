import os
import functools
import time
from typing import Optional

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

import gradio as gr
from gradio.themes import Soft

import config
import handlers
import ui_components
import user_db
import prometheus_metrics
import os

if config.SENTRY_DSN and sentry_sdk:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )



def create_main_ui():
    # Start Prometheus metrics server
    # Note: If running via app.py (FastAPI), metrics are exposed via Instrumentator on the main port.
    # We only start the standalone metrics server if METRICS_PORT is explicitly set and we are NOT in FastAPI mode.
    # But since create_main_ui doesn't know about FastAPI mode easily, let's just make it conditional or rely on app.py handling it.
    # For now, we disable the standalone server here to avoid port conflicts or dual-serving if app.py is the entry point.
    # metrics_port = int(os.getenv("METRICS_PORT", 8000))
    # prometheus_metrics.start_metrics_server(port=metrics_port)

    # Ensure DB and Default User are initialized
    handlers.on_load()

    # Use a base theme that is close to what we want, then override
    theme = Soft(
        primary_hue="violet",
        secondary_hue="indigo",
        neutral_hue="slate",
    ).set(
        body_background_fill="#0f172a",
        block_background_fill="#1e293b",
        block_border_width="1px",
        block_border_color="#334155",
        input_background_fill="#020617",
        button_primary_background_fill="linear-gradient(90deg, #6366f1, #a855f7)",
        button_primary_background_fill_hover="linear-gradient(90deg, #4f46e5, #9333ea)",
        button_primary_text_color="#ffffff",
        button_secondary_background_fill="#334155",
        button_secondary_text_color="#f8fafc",
    )

    css = """
    /* --- Modern Clean Dark Theme (High Contrast) --- */
    
    body {
        background-color: #0f172a; /* Slate 900 - Solid Dark Background */
        color: #f8fafc; /* Slate 50 - High Contrast Text */
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    .gradio-container {
        background-color: #0f172a !important;
        color: #f8fafc !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em;
    }

    /* Cards / Blocks */
    .gradio-container .block, .gradio-container .panel {
        background-color: #1e293b !important; /* Slate 800 */
        border: 1px solid #334155 !important; /* Slate 700 */
        border-radius: 16px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    /* Inputs */
    input, textarea, select, .gr-input {
        background-color: #020617 !important; /* Slate 950 */
        border: 1px solid #475569 !important; /* Slate 600 */
        color: #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }

    .gradio-container .gr-dropdown,
    .gradio-container .gr-dropdown .wrap,
    .gradio-container .gr-dropdown .single-value,
    .gradio-container .gr-dropdown .multi-value__label,
    .gradio-container .gr-dropdown .multi-value,
    .gradio-container .gr-dropdown input {
        color: #ffffff !important;
    }

    label,
    .gradio-container label,
    .gradio-container .gr-label,
    .gradio-container .gr-form-label,
    .gradio-container .gr-text,
    .gradio-container .gr-radio label,
    .gradio-container .gr-dropdown label {
        color: #cbd5e1 !important;
    }
    
    input::placeholder, textarea::placeholder {
        color: #94a3b8 !important; /* Slate 400 */
    }

    input:focus, textarea:focus, select:focus {
        border-color: #a855f7 !important; /* Purple 500 */
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(168, 85, 247, 0.2) !important;
    }

    /* Buttons */
    button.primary, .primary-btn {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: opacity 0.2s ease;
    }
    
    button.primary:hover {
        opacity: 0.9;
        box-shadow: 0 10px 15px -3px rgba(168, 85, 247, 0.3);
    }

    button.secondary {
        background-color: #334155 !important;
        color: #f1f5f9 !important;
        border: 1px solid #475569 !important;
    }

    .gradio-container input,
    .gradio-container textarea,
    .gradio-container select,
    .gradio-container .gr-input,
    .gradio-container .gr-dropdown,
    .gradio-container .gr-radio,
    .gradio-container .gr-button {
        pointer-events: auto !important;
    }

    .gradio-container .gr-dropdown .wrap,
    .gradio-container .gr-dropdown .options,
    .gradio-container .gr-dropdown .options-container {
        z-index: 9999 !important;
    }

    /* Tabs */
    .tabs {
        border-bottom: 1px solid #334155;
    }
    .tab-nav button {
        color: #94a3b8 !important;
        font-weight: 500;
    }
    .tab-nav button.selected {
        color: #a855f7 !important;
        border-bottom: 2px solid #a855f7 !important;
        font-weight: 700;
    }

    /* Tables */
    table {
        border-collapse: separate;
        border-spacing: 0;
        width: 100%;
        border: 1px solid #334155;
        border-radius: 8px;
        overflow: hidden;
    }
    th {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        font-weight: 600;
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #334155;
    }
    td {
        background-color: #1e293b !important;
        color: #e2e8f0 !important;
        padding: 12px;
        border-bottom: 1px solid #334155;
    }
    tr:last-child td {
        border-bottom: none;
    }
    tr:hover td {
        background-color: #334155 !important;
    }

    /* Login Specifics */
    #login-view {
        max-width: 500px !important;
        margin: 60px auto !important;
        width: 100% !important;
    }
    #login-card {
        padding: 40px !important;
        border: 1px solid #334155;
        background-color: #1e293b;
    }
    #hero-badge {
        background-color: #312e81;
        color: #c7d2fe;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 10px;
        display: inline-block;
    }
    #brand-logo {
        margin-bottom: 20px;
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.3));
    }
    
    /* Footer Hidden */
    footer { visibility: hidden; }
    
    #auth-tabs button {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
    }

    /* --- Responsive / Fit to Screen --- */
    @media only screen and (max-width: 768px) {
        #login-view, #dashboard-view, #musegen-view {
            max-width: 95% !important;
            margin: 10px auto !important;
            padding: 0 !important;
        }
        #login-card, .dashboard-card, #musegen-shell {
            padding: 20px !important;
        }
        .gradio-container {
            padding: 5px !important;
        }
        /* Adjust logo for mobile to fit screen */
        #brand-logo, #musegen-brand {
            height: auto !important;
            max-height: 150px !important;
            width: auto !important;
            max-width: 80% !important;
            margin: 0 auto 20px auto !important;
            display: block !important;
        }
        /* Ensure inputs and buttons are easy to tap */
        input, button, select, .gr-input, .gr-button {
            min-height: 48px !important;
            font-size: 16px !important;
        }
        
        /* Fix Table Scrolling on Mobile */
        .table-wrap, .dataframe, .gr-dataframe {
            overflow-x: auto !important;
            display: block !important;
        }
        
        /* Adjust Headings */
        h1 { font-size: 1.8rem !important; }
        h2 { font-size: 1.5rem !important; }
        h3 { font-size: 1.3rem !important; }
        
        /* Tabs navigation on mobile */
        .tabs {
            flex-wrap: wrap !important;
        }
        .tab-nav button {
            flex: 1 1 45% !important;
            margin-bottom: 5px !important;
        }
        
        /* Stack columns on mobile */
        .gr-row {
            flex-direction: column !important;
        }
        .gr-col {
            width: 100% !important;
            min-width: 100% !important;
        }
    }
    
    /* General Card Styling for Dashboard & Tabs */
    .dashboard-card, #musegen-shell, #musegen-history-card, #musegen-admin-card, #musegen-topup-card {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 16px !important;
        padding: 30px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .dashboard-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        border-color: #a855f7 !important;
    }
    
    .dashboard-card-disabled {
        opacity: 0.6;
        cursor: not-allowed;
        background-color: #0f172a !important;
    }

    /* Enhanced Tab Styling */
    .tabs {
        border-bottom: 2px solid #334155;
        margin-bottom: 20px;
        background: transparent !important;
    }
    .tab-nav {
        background: transparent !important;
    }
    .tab-nav button {
        background: transparent !important;
        border: none !important;
        color: #94a3b8 !important;
        font-weight: 600 !important;
        padding: 12px 20px !important;
        transition: all 0.2s ease;
    }
    .tab-nav button:hover {
        color: #e2e8f0 !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px 8px 0 0;
    }
    .tab-nav button.selected {
        color: #a855f7 !important;
        border-bottom: 3px solid #a855f7 !important;
        background: linear-gradient(to top, rgba(168, 85, 247, 0.1), transparent) !important;
    }
    """

    logo_path = config.LOGO_PATH
    if not os.path.exists(logo_path):
        for ext in [".PNG", ".png", ".jpg", ".jpeg"]:
            candidate = os.path.join(config.STATIC_ASSETS_DIR, f"logo{ext}")
            if os.path.exists(candidate):
                logo_path = candidate
                break

    # Auto-login disabled to force Login Screen
    default_user_state = None
    
    with gr.Blocks(title="MuseGenx1000 AI Studio Suite", theme=theme, css=css) as demo:

        # State variables
        user_state = gr.State(value=default_user_state)
        musegen_user_obj = gr.State(value={})
        pending_generation_state = gr.State(value=None)

        # --- LOGIN SECTION ---
        with gr.Column(visible=True, elem_id="login-view") as login_view:
            # Centered Login Card
            with gr.Column(elem_id="login-card"):
                with gr.Row(elem_classes="justify-center"):
                    gr.Image(
                        value=logo_path,
                        show_label=False,
                        interactive=False,
                        elem_id="brand-logo",
                        height=350,
                        container=False,
                    )

                gr.Markdown("""
                    <div style="text-align: center;">
                        <span id='hero-badge'>BETA ACCESS</span>
                        <h1 style="margin-top: 10px; margin-bottom: 5px;">MuseGenx1000</h1>
                        <p style="color: #94a3b8; font-size: 1.1rem;">AI Music Studio • Professional Grade</p>
                    </div>
                    """)

                with gr.Tabs(elem_id="auth-tabs"):
                    with gr.TabItem("Login"):
                        username_input = gr.Textbox(
                            label="Username", placeholder="Enter your username"
                        )
                        password_input = gr.Textbox(
                            label="Password",
                            type="password",
                            placeholder="Enter your password",
                        )
                        login_btn = gr.Button("Sign In", variant="primary", size="lg")
                        login_msg = gr.Textbox(
                            label="Status", interactive=False, visible=True
                        )
                    with gr.TabItem("Sign Up / สมัครสมาชิก"):
                        # Success Modal (Hidden by default)
                        with gr.Group(
                            visible=False, elem_id="signup-success-modal"
                        ) as signup_success_modal:
                            gr.Markdown("""
                                <div style="text-align: center; padding: 20px;">
                                    <h2 style="color: #4ade80;">✅ Registration Successful!</h2>
                                    <p style="font-size: 1.1rem; margin-top: 10px;">Your account has been created.</p>
                                    <p style="color: #cbd5e1;">สมัครสมาชิกเรียบร้อยแล้ว กรุณาเข้าสู่ระบบ</p>
                                </div>
                                """)
                            goto_login_btn = gr.Button("OK / ตกลง", variant="primary")

                        # Sign Up Form
                        with gr.Column(visible=True) as signup_form_col:
                            signup_username = gr.Textbox(
                                label="Username", placeholder="Choose a username"
                            )
                            signup_password = gr.Textbox(
                                label="Password",
                                type="password",
                                placeholder="Create a password",
                            )
                            signup_confirm = gr.Textbox(
                                label="Confirm Password",
                                type="password",
                                placeholder="Confirm password",
                            )
                            signup_display_name = gr.Textbox(
                                label="Display Name",
                                placeholder="Your display name (optional)",
                            )
                            signup_email = gr.Textbox(
                                label="Email", placeholder="Your email (optional)"
                            )
                            signup_btn = gr.Button(
                                "Create Account / สมัครสมาชิก",
                                variant="primary",
                                size="lg",
                            )
                            signup_msg = gr.Textbox(label="Status", interactive=False)

        # --- DASHBOARD SECTION ---
        with gr.Column(visible=False, elem_id="dashboard-view") as dashboard_view:
            # Header Area
            with gr.Row(elem_classes="justify-center mb-8"):
                with gr.Column(scale=1, elem_classes="items-center"):
                    gr.Image(
                        value=logo_path,
                        show_label=False,
                        interactive=False,
                        height=120,
                        container=False,
                        elem_classes="mx-auto block mb-4",
                    )
                    gr.Markdown("""
                        <div style="text-align: center;">
                            <h1 style="margin-bottom: 0.5rem; font-size: 2.5rem; background: linear-gradient(to right, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">MuseGenx1000 Studio Hub</h1>
                            <p style="color: #94a3b8; font-size: 1.2rem;">Your AI-Powered Creative Suite</p>
                        </div>
                        """)
                    dashboard_welcome = gr.Markdown(
                        "<h3 style='text-align: center; color: #e2e8f0; margin-top: 1rem;'>Welcome back!</h3>"
                    )

            # Projects Grid
            with gr.Row(elem_classes="justify-center gap-8 mt-6"):
                # Project Card 1: Music Studio (Active)
                with gr.Column(
                    scale=1,
                    min_width=320,
                    elem_classes="dashboard-card cursor-pointer border-purple-500",
                ):
                    gr.Markdown("### 🎵 AI Music Generator")
                    gr.Markdown("""
                        <div style="height: 60px; color: #cbd5e1; margin-bottom: 1rem;">
                        Create professional tracks with Suno v3.5 & v4. 
                        Full control over lyrics, style, and structure.
                        </div>
                        """)
                    musegen_launch_btn = gr.Button(
                        "🚀 Launch Studio", variant="primary", size="lg"
                    )

                # Project Card 2: Voice Lab (Active)
                with gr.Column(
                    scale=1,
                    min_width=320,
                    elem_classes="dashboard-card cursor-pointer border-cyan-500",
                ):
                    gr.Markdown("### 🎙️ Voice Lab")
                    gr.Markdown("""
                        <div style="height: 60px; color: #cbd5e1; margin-bottom: 1rem;">
                        Clone voices and generate speech with ElevenLabs.
                        Supports Thai language and custom voice models.
                        </div>
                        """)
                    voicelab_launch_btn = gr.Button(
                        "🚀 Launch Voice Lab", variant="primary", size="lg"
                    )

            # Footer Actions
            with gr.Row(elem_classes="mt-12 justify-center"):
                logout_btn = gr.Button(
                    "👋 Log Out",
                    variant="secondary",
                    size="sm",
                    elem_classes="w-auto px-8",
                )

        # --- PROJECT VIEWS ---

        # 1. MuseGen View
        with gr.Column(visible=False, elem_id="musegen-view") as musegen_view:
            with gr.Row():
                back_dashboard_btn_1 = gr.Button(
                    "⬅️ Back to Dashboard", size="sm", variant="secondary"
                )

            with gr.Column(elem_id="musegen-shell"):
                musegen_components = ui_components.render_musegen_tab(user_state)

        # 2. Voice Lab View
        with gr.Column(visible=False, elem_id="voicelab-view") as voicelab_view:
            with gr.Row():
                back_dashboard_btn_2 = gr.Button(
                    "⬅️ Back to Dashboard", size="sm", variant="secondary"
                )

            with gr.Column(elem_id="voicelab-shell"):
                voicelab_components = ui_components.render_voice_lab(user_state)

        # --- EVENT HANDLERS ---

        def resolve_user_id(state, request: Optional[gr.Request]):
            if isinstance(state, dict) and state.get("id"):
                return state.get("id")
            if request and request.username:
                return user_db.get_user_id(request.username)
            return None

        def get_plan_label(user_id):
            info = user_db.get_user_info(user_id) or {}
            level = info.get("level") or "free"
            plan = handlers._get_plan_from_level(level)
            if plan == "easy":
                return plan, "Easy Plan"
            if plan == "standard":
                return plan, "Standard Plan"
            if plan == "pro":
                return plan, "Pro Plan"
            return plan, plan.capitalize()

        def build_user_obj(user_id):
            info = user_db.get_user_info(user_id) or {}
            level = info.get("level") or "free"
            plan = handlers._get_plan_from_level(level)
            credits_value = int(info.get("gg_balance") or 0)
            return {"id": user_id, "plan": plan, "credits": credits_value}

        def mask_request_id(value):
            if not value:
                return "-"
            raw = str(value)
            if len(raw) <= 8:
                return raw
            return f"{raw[:4]}•••{raw[-4:]}"

        def build_job_status(
            status, job_id, eta_seconds, priority, backend, request_id
        ):
            state = "⏳ กำลังประมวลผล"
            if isinstance(status, str) and status.startswith("✅"):
                state = "✅ เสร็จสิ้น"
            if isinstance(status, str) and status.startswith("❌"):
                state = "❌ ล้มเหลว"
            pr = (priority or "low").capitalize()
            eta = f"{eta_seconds}s" if eta_seconds else "-"
            backend_label = (backend or "-").upper()
            req_mask = mask_request_id(request_id)
            job_line = (
                f"**Job ID:** {job_id or '-'}  •  **ETA:** {eta}  •  **Queue:** {pr}"
            )
            meta_line = f"**Backend:** {backend_label}  •  **Request ID:** {req_mask}"
            return state, f"{job_line}<br>{meta_line}"

        def build_history_html(rows):
            if not rows:
                return "<div style='color:#94a3b8;'>No history yet</div>"
            items = []
            for row in rows:
                if len(row) == 7:
                    job_id, title, style, created_at, audio_url, cost, backend = row
                else:
                    job_id = None
                    title, style, created_at, audio_url, cost, backend = row
                audio_tag = ""
                if audio_url:
                    audio_tag = f"<audio controls preload='none' style='width:100%; height:32px;'><source src='{audio_url}'></audio>"
                backend_label = (backend or "-").upper()
                item = (
                    "<div style='border:1px solid #334155;border-radius:12px;padding:12px;margin-bottom:12px;'>"
                    f"<div style='font-weight:600;margin-bottom:6px;'>{title or 'Untitled'}</div>"
                    f"<div style='color:#94a3b8;font-size:12px;margin-bottom:6px;'>{style or '-'}</div>"
                    f"{audio_tag}"
                    "<div style='display:flex;gap:12px;color:#cbd5e1;font-size:12px;margin-top:8px;'>"
                    f"<span>Job ID: {job_id if job_id is not None else '-'}</span>"
                    f"<span>Credits: {int(cost) if cost is not None else '-'}</span>"
                    f"<span>Backend: {backend_label}</span>"
                    f"<span>Time: {created_at or '-'}</span>"
                    "</div></div>"
                )
                items.append(item)
            return "".join(items)

        def handle_login(username, password):
            if not username or not password:
                return (
                    None,
                    "❌ Please enter username and password",
                    gr.update(visible=True),
                    gr.update(visible=False),
                    "Welcome back!",
                )

            user_id, msg = user_db.login_user(username, password)
            if user_id:
                # Login Success
                user_info = handlers.get_user_info(user_id)
                # Parse name from "Name | Email | Level"
                try:
                    name = user_info.split(" | ")[0]
                except Exception:
                    name = username

                welcome_msg = f"<h3 style='text-align: center; color: #e2e8f0; margin-top: 1rem;'>Welcome back, <span style='color: #a855f7;'>{name}</span>!</h3>"

                return (
                    {"id": user_id, "username": username},  # Update State
                    msg,  # Status Message
                    gr.update(visible=False),  # Hide Login
                    gr.update(visible=True),  # Show Dashboard
                    welcome_msg,  # Update Welcome Message
                )
            else:
                # Login Failed
                return (
                    None,
                    msg,
                    gr.update(visible=True),
                    gr.update(visible=False),
                    "Welcome back!",
                )

        def handle_signup(username, password, confirm, display_name, email):
            if not username or not password:
                return (
                    "❌ กรุณากรอกชื่อผู้ใช้และรหัสผ่าน",
                    gr.update(visible=False),
                    gr.update(visible=True),
                )
            if password != confirm:
                return (
                    "❌ รหัสผ่านไม่ตรงกัน",
                    gr.update(visible=False),
                    gr.update(visible=True),
                )
            ok, msg = user_db.register_user(username, password, display_name, email)

            if ok:
                return msg, gr.update(visible=True), gr.update(visible=False)
            else:
                return msg, gr.update(visible=False), gr.update(visible=True)

        login_btn.click(
            handle_login,
            inputs=[username_input, password_input],
            outputs=[
                user_state,
                login_msg,
                login_view,
                dashboard_view,
                dashboard_welcome,
            ],
            api_name="login"
        )
        signup_btn.click(
            handle_signup,
            inputs=[
                signup_username,
                signup_password,
                signup_confirm,
                signup_display_name,
                signup_email,
            ],
            outputs=[signup_msg, signup_success_modal, signup_form_col],
            api_name="signup"
        )

        def close_modal():
            return gr.update(visible=False), gr.update(visible=True)

        goto_login_btn.click(
            close_modal, outputs=[signup_success_modal, signup_form_col]
        )

        # Navigation Handlers
        def show_musegen(state, request: gr.Request):
            user_id = resolve_user_id(state, request)
            plan, plan_name = get_plan_label(user_id)
            user_obj = build_user_obj(user_id)
            credits_value = user_obj.get("credits", 0)
            credits_label = f"Credits: {credits_value} GG"
            cost = ui_components.estimate_cost("easy", False)
            plan_display = f"**Plan:** {plan_name}  •  **Credits:** {credits_value} GG"
            cost_display = f"**Cost:** {cost} GG"
            gen_btn_label = f"🎵 Generate Song ({cost} GG)"
            inst_update = gr.update(
                visible=False, interactive=(plan == "pro"), value=False
            )
            admin_profit, admin_topups, admin_users, admin_status = (
                handlers.on_admin_refresh(request)
            )
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                credits_label,
                handlers.get_user_info(user_id),
                credits_label,
                build_history_html(handlers.get_history(user_id)),
                plan_display,
                cost_display,
                gr.update(value=gen_btn_label),
                "",
                "",
                gr.update(visible=False, value=None),
                inst_update,
                gr.update(visible=False),
                gr.update(visible=False, value=""),
                gr.update(value=config.TOPUP_PACKAGES[2]["gg"]),
                gr.update(visible=False),
                gr.update(value=None),
                user_obj,
                None,
                admin_profit,
                admin_topups,
                admin_users,
                admin_status,
            )

        def show_voicelab(state, request: gr.Request):
            # You might want to update some components here if needed,
            # e.g., credit display in Voice Lab if it exists
            return (
                gr.update(visible=False),  # Hide Dashboard
                gr.update(visible=False),  # Hide MuseGen
                gr.update(visible=True),  # Show VoiceLab
            )

        def back_to_dashboard():
            return (
                gr.update(visible=True),  # Show Dashboard
                gr.update(visible=False),  # Hide MuseGen
                gr.update(visible=False),  # Hide VoiceLab
            )

        def logout():
            return (
                None,  # Clear State
                gr.update(visible=True),  # Show Login
                gr.update(visible=False),  # Hide Dashboard
                gr.update(visible=False),  # Hide MuseGen
                gr.update(visible=False),  # Hide VoiceLab
                "",  # Clear Login Msg
            )

        # Initial Load Logic - FORCE LOGIN SCREEN
        def init_app_state():
            return (
                gr.update(visible=True),   # Show Login
                gr.update(visible=False),  # Hide Dashboard
                gr.update(visible=False),  # Hide MuseGen
                gr.update(visible=False),  # Hide VoiceLab
            )

        demo.load(
            init_app_state,
            inputs=None,
            outputs=[login_view, dashboard_view, musegen_view, voicelab_view],
        )

        musegen_launch_btn.click(
            show_musegen,
            inputs=[user_state],
            outputs=[
                dashboard_view,
                musegen_view,
                voicelab_view,
                musegen_components["credits_display"],
                musegen_components["user_info_display"],
                musegen_components["gg_left_display"],
                musegen_components["history_html"],
                musegen_components["plan_display"],
                musegen_components["cost_display"],
                musegen_components["gen_btn"],
                musegen_components["job_status"],
                musegen_components["job_meta"],
                musegen_components["download_file"],
                musegen_components["instrumental_checkbox"],
                musegen_components["topup_group"],
                musegen_components["topup_msg"],
                musegen_components["topup_amount"],
                musegen_components["topup_resume"],
                musegen_components["topup_slip_upload"],
                musegen_user_obj,
                pending_generation_state,
                musegen_components["admin_profit"],
                musegen_components["admin_topups_table"],
                musegen_components["admin_users_table"],
                musegen_components["admin_status"],
            ],
        )

        voicelab_launch_btn.click(
            show_voicelab,
            inputs=[user_state],
            outputs=[dashboard_view, musegen_view, voicelab_view],
        )

        back_dashboard_btn_1.click(
            back_to_dashboard, outputs=[dashboard_view, musegen_view, voicelab_view]
        )
        back_dashboard_btn_2.click(
            back_to_dashboard, outputs=[dashboard_view, musegen_view, voicelab_view]
        )

        logout_btn.click(
            logout,
            outputs=[
                user_state,
                login_view,
                dashboard_view,
                musegen_view,
                voicelab_view,
                login_msg,
            ],
        )

        def handle_generate_music(
            prompt,
            style,
            mood,
            vocalist,
            mode,
            lyrics_mode,
            custom_lyrics,
            instrumental,
            treat_parens_as_instr,
            state,
            request: gr.Request,
        ):
            def join_values(value):
                if isinstance(value, list):
                    return ", ".join([v for v in value if v])
                return value or ""

            user_id = resolve_user_id(state, request)
            lyrics = custom_lyrics if lyrics_mode == "Custom" else ""
            style_text = join_values(style)
            mood_text = join_values(mood)
            vocalist_text = vocalist if vocalist and vocalist != "Any" else ""

            # Combine style, mood, and vocalist
            style_payload = ", ".join(
                [v for v in [style_text, mood_text, vocalist_text] if v]
            )

            (
                audio,
                status,
                job_id,
                priority,
                backend,
                request_id,
                eta_seconds,
                cost,
                meta,
            ) = handlers.submit_generation(
                prompt,
                style_payload,
                lyrics,
                mode,
                instrumental=instrumental,
                user_id=user_id,
                treat_parens_as_instr=treat_parens_as_instr,
            )
            user_obj = build_user_obj(user_id)
            credits_value = user_obj.get("credits", 0)
            credits_label = f"Credits: {credits_value} GG"
            history = build_history_html(handlers.get_history(user_id))
            job_status, job_meta = build_job_status(
                status, job_id, eta_seconds, priority, backend, request_id
            )
            download_update = (
                gr.update(visible=bool(audio), value=audio)
                if audio
                else gr.update(visible=False, value=None)
            )
            plan, plan_name = get_plan_label(user_id)
            plan_display = f"**Plan:** {plan_name}  •  **Credits:** {credits_value} GG"
            cost_value = ui_components.estimate_cost(mode, instrumental)
            cost_display = f"**Cost:** {cost_value} GG"
            gen_btn_label = f"🎵 Generate Song ({cost_value} GG)"
            inst_update = gr.update(
                visible=(mode == "pro"),
                interactive=(plan == "pro"),
                value=bool(instrumental and plan == "pro"),
            )
            topup_group_update = gr.update(visible=False)
            topup_msg_update = gr.update(visible=False, value="")
            topup_amount_update = gr.update(value=config.TOPUP_PACKAGES[2]["gg"])
            topup_resume_update = gr.update(visible=False)
            pending_payload = None
            status_display = status
            if isinstance(meta, dict) and meta.get("reason") == "insufficient_credits":
                balance = float(meta.get("balance") or 0)
                required = float(meta.get("required") or 0)
                min_topup = int(meta.get("min_topup") or config.GG_TOPUP_MIN)
                topup_amount = max(min_topup, int(required - balance))
                topup_group_update = gr.update(visible=True)
                topup_msg_update = gr.update(
                    visible=True, value="เติมขั้นต่ำ 10 GG / เลือกแพ็กเพื่อรับโบนัส"
                )
                topup_amount_update = gr.update(value=topup_amount)
                topup_resume_update = gr.update(visible=False)
                status_display = "ยอดเครดิตไม่พอ — เติมขั้นต่ำ 10 GG"
                pending_payload = {
                    "prompt": prompt,
                    "style": style,
                    "mood": mood,
                    "vocalist": vocalist,
                    "mode": mode,
                    "lyrics_mode": lyrics_mode,
                    "custom_lyrics": custom_lyrics,
                    "instrumental": instrumental,
                    "treat_parens_as_instr": treat_parens_as_instr,
                }
            return (
                audio,
                status_display,
                credits_label,
                credits_label,
                history,
                plan_display,
                cost_display,
                gr.update(value=gen_btn_label),
                job_status,
                job_meta,
                download_update,
                inst_update,
                gr.update(visible=False),
                topup_group_update,
                topup_msg_update,
                topup_amount_update,
                topup_resume_update,
                user_obj,
                pending_payload,
            )

        def handle_mode_change(mode, lyrics_mode, user_obj):
            user_plan = (user_obj or {}).get("plan", "free")
            return ui_components.on_mode_change(mode, lyrics_mode, user_plan)

        def handle_instrumental_change(mode, instrumental, user_obj):
            user_plan = (user_obj or {}).get("plan", "free")
            return ui_components.on_instrumental_change(mode, instrumental, user_plan)

        def handle_generate_click(
            state,
            mode,
            prompt,
            style,
            mood,
            vocalist,
            lyrics_mode,
            custom_lyrics,
            instrumental,
            treat_parens_as_instr,
            request: gr.Request,
        ):
            user_id = resolve_user_id(state, request)
            user_obj = build_user_obj(user_id) if user_id else {}
            return ui_components.on_generate_click(
                user_obj or {},
                mode,
                prompt,
                style,
                mood,
                vocalist,
                lyrics_mode,
                custom_lyrics,
                instrumental,
                treat_parens_as_instr,
            )

        def cancel_confirm():
            return gr.update(visible=False), ""

        def open_topup_modal():
            return (
                gr.update(visible=True),
                gr.update(visible=False, value=""),
                gr.update(value=config.TOPUP_PACKAGES[2]["gg"]),
                gr.update(visible=False),
                gr.update(value=None),
            )

        def close_topup_modal():
            return (
                gr.update(visible=False),
                gr.update(visible=False, value=""),
                gr.update(visible=False),
                gr.update(value=None),
            )

        def set_quick_amount(amount):
            return gr.update(value=amount)

        def on_pack_click(gg, bonus_pct):
            msg = ""
            if bonus_pct:
                msg = f"โบนัส +{int(bonus_pct * 100)}% เมื่อเติม {gg} GG"
            return gr.update(value=gg), gr.update(
                visible=bool(msg), value=msg
            )

        def handle_topup_submit(
            amount, method, proof_file, state, pending_payload, request: gr.Request
        ):
            user_id = resolve_user_id(state, request)
            if not user_id:
                return (
                    "",
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=True, value="กรุณาเข้าสู่ระบบก่อน"),
                    gr.update(visible=True),
                    gr.update(),
                    gr.update(),
                    gr.update(value=None),
                )
            try:
                amount_int = int(amount)
            except Exception:
                return (
                    "",
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=True, value="กรุณากรอกจำนวนเต็ม"),
                    gr.update(visible=True),
                    gr.update(),
                    gr.update(),
                    gr.update(value=None),
                )
            ok, msg, _ = handlers.submit_topup_request(
                user_id, amount_int, proof_file, method
            )
            if not ok:
                error_msg = msg
                if "Minimum top-up" in msg:
                    error_msg = "ยอดขั้นต่ำคือ 10 GG"
                return (
                    "",
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=True, value=error_msg),
                    gr.update(visible=True),
                    gr.update(),
                    gr.update(),
                    gr.update(value=None),
                )
            return (
                msg,
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(visible=False, value=""),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(),
                gr.update(value=None),
            )

        def resume_generation(pending_payload, state, request: gr.Request):
            if not isinstance(pending_payload, dict):
                return (
                    gr.update(),
                    "ไม่พบงานที่รออยู่",
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=False),
                    gr.update(visible=False, value=""),
                    gr.update(),
                    gr.update(visible=False),
                    gr.update(),
                    None,
                )
            return handle_generate_music(
                pending_payload.get("prompt", ""),
                pending_payload.get("style"),
                pending_payload.get("mood"),
                pending_payload.get("vocalist"),
                pending_payload.get("mode", "easy"),
                pending_payload.get("lyrics_mode", "AI"),
                pending_payload.get("custom_lyrics", ""),
                pending_payload.get("instrumental", False),
                pending_payload.get("treat_parens_as_instr", True),
                state,
                request,
            )

        musegen_components["mode"].change(
            handle_mode_change,
            inputs=[
                musegen_components["mode"],
                musegen_components["lyrics_mode"],
                musegen_user_obj,
            ],
            outputs=[
                musegen_components["custom_lyrics"],
                musegen_components["treat_parens_as_instr"],
                musegen_components["instrumental_checkbox"],
                musegen_components["reference_row"],
                musegen_components["gen_btn"],
                musegen_components["cost_display"],
                musegen_components["confirm_group"],
                musegen_components["status_msg"],
            ],
        )

        musegen_components["instrumental_checkbox"].change(
            handle_instrumental_change,
            inputs=[
                musegen_components["mode"],
                musegen_components["instrumental_checkbox"],
                musegen_user_obj,
            ],
            outputs=[
                musegen_components["gen_btn"],
                musegen_components["cost_display"],
                musegen_components["confirm_group"],
                musegen_components["status_msg"],
            ],
        )

        musegen_components["gen_btn"].click(
            handle_generate_click,
            inputs=[
                user_state,
                musegen_components["mode"],
                musegen_components["prompt"],
                musegen_components["style"],
                musegen_components["mood"],
                musegen_components["vocalist"],
                musegen_components["lyrics_mode"],
                musegen_components["custom_lyrics"],
                musegen_components["instrumental_checkbox"],
                musegen_components["treat_parens_as_instr"],
            ],
            outputs=[
                musegen_components["status_msg"],
                musegen_components["confirm_group"],
                musegen_components["confirm_text"],
                musegen_components["topup_group"],
                musegen_components["topup_msg"],
                musegen_components["topup_amount"],
                musegen_components["topup_resume"],
                pending_generation_state,
            ],
        )

        musegen_components["confirm_btn"].click(
            handle_generate_music,
            inputs=[
                musegen_components["prompt"],
                musegen_components["style"],
                musegen_components["mood"],
                musegen_components["vocalist"],
                musegen_components["mode"],
                musegen_components["lyrics_mode"],
                musegen_components["custom_lyrics"],
                musegen_components["instrumental_checkbox"],
                musegen_components["treat_parens_as_instr"],
                user_state,
            ],
            outputs=[
                musegen_components["audio_out"],
                musegen_components["status_msg"],
                musegen_components["credits_display"],
                musegen_components["gg_left_display"],
                musegen_components["history_html"],
                musegen_components["plan_display"],
                musegen_components["cost_display"],
                musegen_components["gen_btn"],
                musegen_components["job_status"],
                musegen_components["job_meta"],
                musegen_components["download_file"],
                musegen_components["instrumental_checkbox"],
                musegen_components["confirm_group"],
                musegen_components["topup_group"],
                musegen_components["topup_msg"],
                musegen_components["topup_amount"],
                musegen_components["topup_resume"],
                musegen_user_obj,
                pending_generation_state,
            ],
        )

        musegen_components["confirm_cancel_btn"].click(
            cancel_confirm,
            outputs=[musegen_components["confirm_group"], musegen_components["confirm_text"]],
        )

        musegen_components["topup_open_btn"].click(
            open_topup_modal,
            outputs=[
                musegen_components["topup_group"],
                musegen_components["topup_msg"],
                musegen_components["topup_amount"],
                musegen_components["topup_resume"],
                musegen_components["topup_slip_upload"],
            ],
        )

        musegen_components["topup_cancel"].click(
            close_topup_modal,
            outputs=[
                musegen_components["topup_group"],
                musegen_components["topup_msg"],
                musegen_components["topup_resume"],
                musegen_components["topup_slip_upload"],
            ],
        )

        musegen_components["topup_quick_10"].click(
            set_quick_amount,
            inputs=[gr.State(value=10)],
            outputs=[musegen_components["topup_amount"]],
        )
        musegen_components["topup_quick_30"].click(
            set_quick_amount,
            inputs=[gr.State(value=30)],
            outputs=[musegen_components["topup_amount"]],
        )
        musegen_components["topup_quick_100"].click(
            set_quick_amount,
            inputs=[gr.State(value=100)],
            outputs=[musegen_components["topup_amount"]],
        )

        for idx, pack in enumerate(config.TOPUP_PACKAGES):
            btn = musegen_components["topup_pack_buttons"][idx]
            btn.click(
                functools.partial(on_pack_click, pack["gg"], pack.get("bonus_pct", 0.0)),
                outputs=[musegen_components["topup_amount"], musegen_components["topup_msg"]],
            )

        musegen_components["topup_submit"].click(
            handle_topup_submit,
            inputs=[
                musegen_components["topup_amount"],
                musegen_components["topup_method"],
                musegen_components["topup_slip_upload"],
                user_state,
                pending_generation_state,
            ],
            outputs=[
                musegen_components["status_msg"],
                musegen_components["credits_display"],
                musegen_components["gg_left_display"],
                musegen_components["plan_display"],
                musegen_components["topup_msg"],
                musegen_components["topup_group"],
                musegen_components["topup_resume"],
                musegen_user_obj,
                musegen_components["topup_slip_upload"],
            ],
        )

        musegen_components["topup_resume"].click(
            resume_generation,
            inputs=[pending_generation_state, user_state],
            outputs=[
                musegen_components["audio_out"],
                musegen_components["status_msg"],
                musegen_components["credits_display"],
                musegen_components["gg_left_display"],
                musegen_components["history_html"],
                musegen_components["plan_display"],
                musegen_components["cost_display"],
                musegen_components["gen_btn"],
                musegen_components["job_status"],
                musegen_components["job_meta"],
                musegen_components["download_file"],
                musegen_components["instrumental_checkbox"],
                musegen_components["confirm_group"],
                musegen_components["topup_group"],
                musegen_components["topup_msg"],
                musegen_components["topup_amount"],
                musegen_components["topup_resume"],
                musegen_user_obj,
                pending_generation_state,
            ],
        )

        def approve_topup(tx_id, request: gr.Request):
            msg = handlers.approve_tx(tx_id)
            admin_profit, admin_topups, admin_users, admin_status = (
                handlers.on_admin_refresh(request)
            )
            return msg, admin_profit, admin_topups, admin_users, admin_status

        def reject_topup(tx_id, request: gr.Request):
            msg = handlers.reject_tx(tx_id)
            admin_profit, admin_topups, admin_users, admin_status = (
                handlers.on_admin_refresh(request)
            )
            return msg, admin_profit, admin_topups, admin_users, admin_status

        musegen_components["admin_refresh_btn"].click(
            handlers.on_admin_refresh,
            inputs=[],
            outputs=[
                musegen_components["admin_profit"],
                musegen_components["admin_topups_table"],
                musegen_components["admin_users_table"],
                musegen_components["admin_status"],
            ],
        )

        musegen_components["admin_approve_btn"].click(
            approve_topup,
            inputs=[musegen_components["admin_tx_id"]],
            outputs=[
                musegen_components["admin_action_msg"],
                musegen_components["admin_profit"],
                musegen_components["admin_topups_table"],
                musegen_components["admin_users_table"],
                musegen_components["admin_status"],
            ],
        )

        musegen_components["admin_reject_btn"].click(
            reject_topup,
            inputs=[musegen_components["admin_tx_id"]],
            outputs=[
                musegen_components["admin_action_msg"],
                musegen_components["admin_profit"],
                musegen_components["admin_topups_table"],
                musegen_components["admin_users_table"],
                musegen_components["admin_status"],
            ],
        )

        # --- Voice Lab Handlers ---
        voicelab_components["gen_btn"].click(
            handlers.generate_voice_clone,
            inputs=[
                voicelab_components["voice_text"],
                voicelab_components["voice_id"],
                voicelab_components["voice_model"],
                voicelab_components["stability"],
                voicelab_components["similarity"],
                voicelab_components["consent_checkbox"],
                user_state,  # Pass user_state to get user_id
            ],
            outputs=[
                voicelab_components["voice_output"],
                voicelab_components["voice_status"],
            ],
        )

    return demo, theme, css


if __name__ == "__main__":
    ui, theme, css = create_main_ui()
    ui.launch(theme=theme, css=css)
