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
from locales import t

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
        primary_hue="blue",
        secondary_hue="indigo",
        neutral_hue="slate",
    ).set(
        body_background_fill="#0f172a",
        block_background_fill="#1e293b",
        block_border_width="1px",
        block_border_color="#334155",
        input_background_fill="#020617",
        button_primary_background_fill="linear-gradient(90deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%)",
        button_primary_background_fill_hover="linear-gradient(90deg, #0041a8 0%, #3651c9 50%, #5a9ceb 100%)",
        button_primary_text_color="#ffffff",
        button_secondary_background_fill="#334155",
        button_secondary_text_color="#f8fafc",
    )

    css = """
    /* --- Modern Clean Light Theme (High Contrast) --- */
    
    body {
        background-color: #f8f9fa !important; /* Light Gray Background */
        color: #212529 !important; /* Dark Black Text */
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    .gradio-container {
        background-color: #f8f9fa !important;
        color: #212529 !important;
    }

    /* Primary Button Style - Blue Gradient */
    .gradio-button.primary, button.primary, .primary-btn {
        background: linear-gradient(90deg, #0052D4, #4364F7) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        transition: transform 0.1s ease, box-shadow 0.1s ease;
        font-weight: 600 !important;
    }
    .gradio-button.primary:hover, button.primary:hover, .primary-btn:hover {
        background: linear-gradient(90deg, #0041a8, #3651c9) !important;
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.3);
        transform: translateY(-1px);
    }
    .gradio-button.primary:active, button.primary:active, .primary-btn:active {
        transform: translateY(1px);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #212529 !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em;
    }

    /* Cards / Blocks */
    .gradio-container .block, .gradio-container .panel {
        background-color: #ffffff !important; /* White */
        border: 1px solid #e9ecef !important; /* Light Gray Border */
        border-radius: 16px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05) !important;
    }

    /* Inputs */
    input, textarea, select, .gr-input {
        background-color: #ffffff !important;
        border: 2px solid #ced4da !important; /* Thicker Border */
        color: #212529 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }

    .gradio-container .gr-dropdown,
    .gradio-container .gr-dropdown .wrap,
    .gradio-container .gr-dropdown .single-value,
    .gradio-container .gr-dropdown .multi-value__label,
    .gradio-container .gr-dropdown .multi-value,
    .gradio-container .gr-dropdown input {
        color: #212529 !important;
        background-color: #ffffff !important;
    }

    label,
    .gradio-container label,
    .gradio-container .gr-label,
    .gradio-container .gr-form-label,
    .gradio-container .gr-text,
    .gradio-container .gr-radio label,
    .gradio-container .gr-dropdown label {
        color: #212529 !important;
        font-weight: 700 !important; /* Bold Labels */
    }
    
    input::placeholder, textarea::placeholder {
        color: #adb5bd !important;
    }

    input:focus, textarea:focus, select:focus {
        border-color: #0052D4 !important; /* Blue Focus */
        outline: none !important;
        box-shadow: 0 0 0 4px rgba(0, 82, 212, 0.2) !important; /* Blue Ring */
    }

    /* Secondary Buttons */
    button.secondary {
        background-color: #e9ecef !important;
        color: #212529 !important;
        border: 1px solid #ced4da !important;
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
        border-bottom: 1px solid #dee2e6;
    }
    .tab-nav button {
        color: #6c757d !important;
        font-weight: 500;
    }
    .tab-nav button.selected {
        color: #0052D4 !important;
        border-bottom: 2px solid #0052D4 !important;
        font-weight: 700;
    }

    /* Tables */
    table {
        border-collapse: separate;
        border-spacing: 0;
        width: 100%;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        overflow: hidden;
    }
    th {
        background-color: #f8f9fa !important;
        color: #212529 !important;
        font-weight: 600;
        padding: 12px;
        text-align: left;
        border-bottom: 2px solid #dee2e6;
    }
    td {
        background-color: #ffffff !important;
        color: #212529 !important;
        padding: 12px;
        border-bottom: 1px solid #e9ecef;
    }
    tr:last-child td {
        border-bottom: none;
    }
    tr:hover td {
        background-color: #f1f3f5 !important;
    }

    /* Login Specifics */
    #login-view {
        max-width: 500px !important;
        margin: 60px auto !important;
        width: 100% !important;
    }
    #login-card {
        padding: 40px !important;
        border: 1px solid #e9ecef !important;
        background-color: #ffffff !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    }
    #hero-badge {
        background-color: #e0e7ff;
        color: #3730a3;
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
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));
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
    
    # theme=None to test Custom CSS
    with gr.Blocks(title=t("app_title"), theme=theme, css=css) as demo:

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

                gr.Markdown(f"""
                        <div style="text-align: center;">
                            <span id='hero-badge'>BETA ACCESS</span>
                            <h1 style="margin-top: 10px; margin-bottom: 5px;">MuseGenx1000</h1>
                            <p style="color: #94a3b8; font-size: 1.1rem;">{t("app_subtitle_pro")}</p>
                        </div>
                    """)

                with gr.Tabs(elem_id="auth-tabs") as auth_tabs:
                    with gr.TabItem(t("login_tab")):
                        username_input = gr.Textbox(
                            label=t("username_label"), placeholder=t("username_placeholder")
                        )
                        password_input = gr.Textbox(
                            label=t("password_label"),
                            type="password",
                            placeholder=t("password_placeholder"),
                        )
                        login_btn = gr.Button(t("login_btn"), variant="primary", size="lg")
                        login_msg = gr.Textbox(
                            label=t("status"), interactive=False, visible=True
                        )
                    with gr.TabItem(t("register_tab")):
                        # Success Modal (Hidden by default)
                        with gr.Group(
                            visible=False, elem_id="signup-success-modal"
                        ) as signup_success_modal:
                            gr.Markdown(f"""
                                <div style="text-align: center; padding: 20px;">
                                    <h2 style="color: #4ade80;">{t('signup_success_title')}</h2>
                                    <p style="font-size: 1.1rem; margin-top: 10px;">{t('signup_success_msg')}</p>
                                    <p style="color: #cbd5e1;">{t('signup_success_login')}</p>
                                </div>
                                """)
                            goto_login_btn = gr.Button(t("ok_btn"), variant="primary")

                        # Sign Up Form
                        with gr.Column(visible=True) as signup_form_col:
                            signup_username = gr.Textbox(
                                label=t("reg_username_label"), placeholder=t("reg_username_placeholder")
                            )
                            signup_password = gr.Textbox(
                                label=t("reg_password_label"),
                                type="password",
                                placeholder=t("reg_password_placeholder"),
                            )
                            signup_confirm = gr.Textbox(
                                label=t("confirm_password_label"),
                                type="password",
                                placeholder=t("confirm_password_placeholder"),
                            )
                            signup_display_name = gr.Textbox(
                                label=t("display_name_label"),
                                placeholder=t("display_name_placeholder"),
                            )
                            signup_email = gr.Textbox(
                                label=t("email_label"), placeholder=t("email_placeholder")
                            )
                            signup_btn = gr.Button(
                                t("register_action_btn"),
                                variant="primary",
                                size="lg",
                            )
                            signup_msg = gr.Textbox(label=t("status"), interactive=False)

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
                    gr.Markdown(f"""
                        <div style="text-align: center;">
                            <h1 style="margin-bottom: 0.5rem; font-size: 2.5rem; background: linear-gradient(to right, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{t("dashboard_title_hub")}</h1>
                            <p style="color: #94a3b8; font-size: 1.2rem;">{t("dashboard_sub")}</p>
                        </div>
                        """)
                    dashboard_welcome = gr.Markdown(
                        f"<h3 style='text-align: center; color: #e2e8f0; margin-top: 1rem;'>{t('welcome_back')}</h3>"
                    )

            # Projects Grid
            with gr.Row(elem_classes="justify-center gap-8 mt-6"):
                # Project Card 1: Music Studio (Active)
                with gr.Column(
                    scale=1,
                    min_width=320,
                    elem_classes="dashboard-card cursor-pointer border-purple-500",
                ):
                    gr.Markdown(t("card_music_title"))
                    gr.Markdown(f"""
                        <div style="height: 60px; color: #cbd5e1; margin-bottom: 1rem;">
                        {t('card_music_desc')}
                        </div>
                        """)
                    musegen_launch_btn = gr.Button(
                        t("launch_music_studio"), variant="primary", size="lg"
                    )

                # Project Card 2: Voice Lab (Active)
                with gr.Column(
                    scale=1,
                    min_width=320,
                    elem_classes="dashboard-card cursor-pointer border-cyan-500",
                ):
                    gr.Markdown(t("card_voicelab_title"))
                    gr.Markdown(f"""
                        <div style="height: 60px; color: #cbd5e1; margin-bottom: 1rem;">
                        {t('card_voicelab_desc')}
                        </div>
                        """)
                    voicelab_launch_btn = gr.Button(
                        t("launch_voicelab"), variant="primary", size="lg"
                    )

            # Footer Actions
            with gr.Row(elem_classes="mt-12 justify-center"):
                logout_btn = gr.Button(
                    t("logout_action"),
                    variant="secondary",
                    size="sm",
                    elem_classes="w-auto px-8",
                )

        # --- PROJECT VIEWS ---

        # 1. MuseGen View
        with gr.Column(visible=False, elem_id="musegen-view") as musegen_view:
            with gr.Row():
                back_dashboard_btn_1 = gr.Button(
                    t("back_to_dashboard"), size="sm", variant="secondary"
                )

            with gr.Column(elem_id="musegen-shell"):
                musegen_components = ui_components.render_musegen_tab(user_state)

        # 2. Voice Lab View
        with gr.Column(visible=False, elem_id="voicelab-view") as voicelab_view:
            with gr.Row():
                back_dashboard_btn_2 = gr.Button(
                    t("back_to_dashboard"), size="sm", variant="secondary"
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
                return plan, t("plan_easy")
            if plan == "standard":
                return plan, t("plan_standard")
            if plan == "pro":
                return plan, t("plan_pro")
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
            state = t("job_processing")
            if isinstance(status, str) and status.startswith("✅"):
                state = t("job_finished")
            if isinstance(status, str) and status.startswith("❌"):
                state = t("job_failed")
            pr = (priority or "low").capitalize()
            eta = f"{eta_seconds}s" if eta_seconds else "-"
            backend_label = (backend or "-").upper()
            req_mask = mask_request_id(request_id)
            job_line = (
                f"**{t('job_id')}:** {job_id or '-'}  •  **{t('eta')}:** {eta}  •  **{t('queue')}:** {pr}"
            )
            meta_line = f"**{t('backend')}:** {backend_label}  •  **{t('req_id')}:** {req_mask}"
            return state, f"{job_line}<br>{meta_line}"

        def build_history_html(rows):
            if not rows:
                return t("history_empty")
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
                    f"<span>{t('job_id')}: {job_id if job_id is not None else '-'}</span>"
                    f"<span>{t('credits_label')}: {int(cost) if cost is not None else '-'}</span>"
                    f"<span>{t('backend')}: {backend_label}</span>"
                    f"<span>{t('time_label')}: {created_at or '-'}</span>"
                    "</div></div>"
                )
                items.append(item)
            return "".join(items)

        def handle_login(username, password):
            print(f"DEBUG: handle_login called with username='{username}', password='{password}'")
            if not username or not password:
                print("DEBUG: Missing username or password")
                return (
                    None,
                    t("login_missing_creds"),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    t("welcome_back"),
                )

            user_id, msg = user_db.login_user(username, password)
            print(f"DEBUG: login_user result: user_id={user_id}, msg={msg}")
            
            if user_id:
                # Login Success
                user_info = handlers.get_user_info(user_id)
                # Parse name from "Name | Email | Level"
                try:
                    name = user_info.split(" | ")[0]
                except Exception:
                    name = username

                welcome_msg = f"<h3 style='text-align: center; color: #e2e8f0; margin-top: 1rem;'>{t('welcome_back_name').format(name=name)}</h3>"

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
                    t("welcome_back"),
                )

        def handle_signup(username, password, confirm, display_name, email):
            if not username or not password:
                return (
                    t("login_missing_creds"),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    username, password, confirm, display_name, email,
                    gr.update()
                )
            if password != confirm:
                return (
                    t("signup_password_mismatch"),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    username, password, confirm, display_name, email,
                    gr.update()
                )
            ok, msg = user_db.register_user(username, password, display_name, email)

            if ok:
                gr.Info('สมัครสมาชิกสำเร็จแล้ว! กรุณาล็อกอินเข้าสู่ระบบ')
                return (
                    "",  # Clear msg
                    gr.update(visible=False),  # Hide modal (not used)
                    gr.update(visible=True),   # Keep form visible (or reset state)
                    "", "", "", "", "",        # Clear fields
                    gr.update(selected=t("login_tab")) # Switch to Login Tab
                )
            else:
                return (
                    msg,
                    gr.update(visible=False),
                    gr.update(visible=True),
                    username, password, confirm, display_name, email,
                    gr.update()
                )

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
            outputs=[
                signup_msg, 
                signup_success_modal, 
                signup_form_col,
                signup_username,
                signup_password,
                signup_confirm,
                signup_display_name,
                signup_email,
                auth_tabs
            ],
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
            credits_label = f"{t('credits_label')}: {credits_value} GG"
            cost = ui_components.estimate_cost("easy", False)
            plan_display = f"**Plan:** {plan_name}  •  **{t('credits_label')}:** {credits_value} GG"
            cost_display = t('cost_label').format(cost=cost)
            gen_btn_label = t('cost_btn_generate').format(cost=cost)
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
            progress=gr.Progress(),
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
                progress=progress,
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
                gr.update(value=gen_btn_label, interactive=True),
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
                gr.update(visible=False), # Hide loading animation
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
                    gr.update(), # loading_animation
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

        def lock_ui_confirm():
            return (
                gr.update(visible=True),
                gr.update(interactive=False),
                gr.update(visible=False),
            )

        musegen_components["confirm_btn"].click(
            lock_ui_confirm,
            outputs=[
                musegen_components["loading_animation"],
                musegen_components["gen_btn"],
                musegen_components["confirm_group"],
            ]
        ).then(
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
                musegen_components["loading_animation"],
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

        def lock_ui_resume():
            return (
                gr.update(visible=True),
                gr.update(interactive=False),
                gr.update(visible=False),
            )

        musegen_components["topup_resume"].click(
            lock_ui_resume,
            outputs=[
                musegen_components["loading_animation"],
                musegen_components["gen_btn"],
                musegen_components["topup_group"],
            ]
        ).then(
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
                musegen_components["loading_animation"],
            ],
        )

        def approve_topup(tx_id, request: gr.Request):
            msg = handlers.approve_tx(tx_id, request)
            admin_profit, admin_topups, admin_users, admin_status = (
                handlers.on_admin_refresh(request)
            )
            return msg, admin_profit, admin_topups, admin_users, admin_status

        def reject_topup(tx_id, request: gr.Request):
            msg = handlers.reject_tx(tx_id, request)
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

        def admin_delete_user_wrapper(target_id, request: gr.Request):
            msg = handlers.on_admin_delete_user(target_id, request)
            admin_profit, admin_topups, admin_users, admin_status = (
                handlers.on_admin_refresh(request)
            )
            return msg, admin_profit, admin_topups, admin_users, admin_status

        def admin_add_gg_wrapper(target_id, amount, request: gr.Request):
            msg = handlers.on_admin_add_gg(target_id, amount, request)
            admin_profit, admin_topups, admin_users, admin_status = (
                handlers.on_admin_refresh(request)
            )
            return msg, admin_profit, admin_topups, admin_users, admin_status

        def admin_set_level_wrapper(target_id, level, request: gr.Request):
            msg = handlers.on_admin_set_level(target_id, level, request)
            admin_profit, admin_topups, admin_users, admin_status = (
                handlers.on_admin_refresh(request)
            )
            return msg, admin_profit, admin_topups, admin_users, admin_status

        musegen_components["admin_delete_btn"].click(
            admin_delete_user_wrapper,
            inputs=[musegen_components["admin_target_user_id"]],
            outputs=[
                musegen_components["admin_action_msg"],
                musegen_components["admin_profit"],
                musegen_components["admin_topups_table"],
                musegen_components["admin_users_table"],
                musegen_components["admin_status"],
            ],
        )

        musegen_components["admin_add_gg_btn"].click(
            admin_add_gg_wrapper,
            inputs=[
                musegen_components["admin_target_user_id"],
                musegen_components["admin_add_gg_amount"],
            ],
            outputs=[
                musegen_components["admin_action_msg"],
                musegen_components["admin_profit"],
                musegen_components["admin_topups_table"],
                musegen_components["admin_users_table"],
                musegen_components["admin_status"],
            ],
        )

        musegen_components["admin_set_level_btn"].click(
            admin_set_level_wrapper,
            inputs=[
                musegen_components["admin_target_user_id"],
                musegen_components["admin_set_level_dropdown"],
            ],
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
