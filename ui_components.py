"""
Gradio UI Components
"""

import os
from typing import Any, Dict

import gradio as gr

from config import (
    ASSETS_DIR,
    STATIC_ASSETS_DIR,
    GENRES,
    GG_COST_INST,
    GG_COST_SONG,
    GG_TOPUP_MIN,
    LOGO_PATH,
    PAYMENT_QR_PATH,
    MOODS,
    TOPUP_PACKAGES,
    VOCALIST_TYPES,
)
from locales import t


def estimate_cost(mode: str, instrumental: bool) -> int:
    base = GG_COST_SONG
    inst = GG_COST_INST if instrumental else 0
    if instrumental and mode != "pro":
        return -1
    return int(base + inst)


def _needs_upgrade(user_plan: str, mode: str) -> bool:
    plan_rank = {"free": 0, "easy": 0, "standard": 1, "pro": 2}
    req_rank = {"easy": 0, "standard": 1, "pro": 2}
    return plan_rank.get(user_plan, 0) < req_rank.get(mode, 0)


def on_mode_change(mode: str, lyrics_mode: str, user_plan: str):
    needs_upgrade = _needs_upgrade(user_plan, mode)
    show_custom_lyrics = (
        mode in ("standard", "pro")
        and lyrics_mode == "Custom"
        and not needs_upgrade
    )
    show_instrumental_opt = mode == "pro"
    show_reference = mode == "pro"
    cost = estimate_cost(mode, instrumental=False)
    btn_label = t("cost_btn_unavailable") if cost < 0 else t("cost_btn_generate").format(cost=cost)
    if needs_upgrade:
        btn_label = t("cost_btn_need_upgrade").format(btn_label=btn_label)
    return (
        gr.update(visible=show_custom_lyrics),
        gr.update(visible=show_custom_lyrics),  # treat_parens_as_instr
        gr.update(
            visible=show_instrumental_opt,
            value=False,
            interactive=not needs_upgrade,
        ),
        gr.update(visible=show_reference),
        gr.update(value=btn_label, interactive=not needs_upgrade),
        gr.update(value=t("cost_label").format(cost=cost) if cost >= 0 else t("cost_free")),
        gr.update(visible=False),
        "",
    )


def on_instrumental_change(mode: str, instrumental: bool, user_plan: str):
    cost = estimate_cost(mode, instrumental)
    needs_upgrade = _needs_upgrade(user_plan, mode)
    if needs_upgrade:
        return (
            gr.update(
                interactive=False,
                value=t("cost_btn_need_upgrade").format(btn_label=t("cost_btn_generate").format(cost=max(cost, 0))),
            ),
            gr.update(value=t("cost_label").format(cost=max(cost, 0))),
            gr.update(visible=False),
            t("msg_upgrade_req"),
        )
    if cost < 0:
        return (
            gr.update(
                interactive=False,
                value=t("instr_pro_only"),
            ),
            gr.update(value=t("cost_free")),
            gr.update(visible=False),
            t("msg_instr_pro_only"),
        )
    return (
        gr.update(interactive=True, value=t("cost_btn_generate").format(cost=cost)),
        gr.update(value=t("cost_label").format(cost=cost)),
        gr.update(visible=False),
        "",
    )


def on_generate_click(
    user_obj: Dict[str, Any],
    mode: str,
    prompt: str,
    style,
    mood,
    vocalist,
    lyrics_mode: str,
    custom_lyrics: str,
    instrumental: bool,
    treat_parens_as_instr: bool = True,
):
    user_plan = user_obj.get("plan", "free")
    user_credits = int(user_obj.get("credits", 0) or 0)
    cost = estimate_cost(mode, instrumental)
    if _needs_upgrade(user_plan, mode):
        return (
            t("msg_upgrade_req"),
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            gr.update(visible=False, value=""),
            gr.update(value=TOPUP_PACKAGES[2]["gg"]),
            gr.update(visible=False),
            None,
        )
    if cost < 0:
        return (
            t("msg_instr_pro_only"),
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            gr.update(visible=False, value=""),
            gr.update(value=TOPUP_PACKAGES[2]["gg"]),
            gr.update(visible=False),
            None,
        )
    if user_credits < cost:
        required = max(GG_TOPUP_MIN, cost - user_credits)
        return (
            t("msg_credit_low"),
            gr.update(visible=False),
            "",
            gr.update(visible=True),
            gr.update(
                visible=True,
                value=t("msg_topup_bonus"),
            ),
            gr.update(value=required),
            gr.update(visible=False),
            {
                "prompt": prompt,
                "style": style,
                "mood": mood,
                "vocalist": vocalist,
                "mode": mode,
                "lyrics_mode": lyrics_mode,
                "custom_lyrics": custom_lyrics,
                "instrumental": instrumental,
                "treat_parens_as_instr": treat_parens_as_instr,
            },
        )
    confirm_text = t("msg_confirm_deduct").format(cost=cost, remaining=user_credits - cost)
    return (
        "",
        gr.update(visible=True),
        confirm_text,
        gr.update(visible=False),
        gr.update(visible=False, value=""),
        gr.update(value=TOPUP_PACKAGES[2]["gg"]),
        gr.update(visible=False),
        None,
    )


def render_voice_lab(user_state):
    """Render the Voice Lab content"""
    gr.Markdown(t("voicelab_header"))
    gr.Markdown(
        t("voicelab_subheader")
    )

    with gr.Row():
        with gr.Column(scale=1):
            voice_text = gr.Textbox(
                label=t("voice_text_label"),
                placeholder=t("voice_text_placeholder"),
                lines=5,
            )

            with gr.Row():
                voice_id = gr.Dropdown(
                    label=t("voice_id_label"),
                    choices=[
                        (t("voice_rachel"), "21m00Tcm4TlvDq8ikWAM"),
                        (t("voice_domi"), "AZnzlk1XvdvUeBnXmlld"),
                        (t("voice_bella"), "EXAVITQu4vr4xnSDxMaL"),
                        (t("voice_antoni"), "ErXwobaYiN019PkySvjV"),
                        (t("voice_josh"), "TxGEqnHWrfWFTfGW9XjX"),
                    ],
                    value="21m00Tcm4TlvDq8ikWAM",
                    allow_custom_value=True,
                    info=t("voice_id_info"),
                )
                voice_model = gr.Dropdown(
                    label=t("voice_model_label"),
                    choices=[
                        (t("voice_model_multilingual_rec"), "eleven_multilingual_v2"),
                        (t("voice_model_monolingual"), "eleven_monolingual_v1"),
                        (t("voice_model_turbo"), "eleven_turbo_v2"),
                    ],
                    value="eleven_multilingual_v2",
                    info=t("voice_model_info"),
                )

            with gr.Accordion(t("adv_settings"), open=False):
                stability = gr.Slider(
                    label=t("stability_label"),
                    minimum=0.0,
                    maximum=1.0,
                    value=0.4,
                    step=0.05,
                    info=t("stability_info"),
                )
                similarity = gr.Slider(
                    label=t("similarity_label"),
                    minimum=0.0,
                    maximum=1.0,
                    value=0.1,
                    step=0.05,
                    info=t("similarity_info"),
                )
                consent_checkbox = gr.Checkbox(
                    label=t("consent_label"), value=False
                )

            gen_btn = gr.Button(t("btn_generate_voice"), variant="primary", size="lg")

        with gr.Column(scale=1):
            voice_output = gr.Audio(
                label=t("voice_output_label"), type="filepath", interactive=False
            )
            voice_status = gr.Markdown("")

            gr.Markdown(t("voice_tips_header"))
            gr.Info(
                t("voice_tips_info")
            )

    return {
        "voice_text": voice_text,
        "voice_id": voice_id,
        "voice_model": voice_model,
        "stability": stability,
        "similarity": similarity,
        "consent_checkbox": consent_checkbox,
        "gen_btn": gen_btn,
        "voice_output": voice_output,
        "voice_status": voice_status,
    }


def render_musegen_tab(user_state):
    """Render the MuseGen content"""

    logo_path = LOGO_PATH
    if not os.path.exists(logo_path):
        for ext in [".PNG", ".png", ".jpg", ".jpeg"]:
            candidate = os.path.join(STATIC_ASSETS_DIR, f"logo{ext}")
            if os.path.exists(candidate):
                logo_path = candidate
                break

    gr.Markdown(
        f"### <span id='musegen-hero'>{t('app_header')}</span>"
    )
    gr.HTML("""
        <style>
            #musegen-status-msg { display: none !important; }
            
            /* Loading Container */
            #musegen-loading {
                display: none; /* Hidden by default */
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px;
                background: rgba(15, 23, 42, 0.5);
                border-radius: 16px;
                margin: 20px 0;
                border: 1px solid rgba(168, 85, 247, 0.2);
                backdrop-filter: blur(10px);
            }
            
            /* Show when active class is added (controlled by JS or visible prop if using Gradio logic, 
               but here we might toggle visibility via component update) */
            
            /* Sound Wave Animation */
            .music-wave {
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                margin-bottom: 20px;
            }
            
            .music-wave .bar {
                width: 8px;
                height: 100%;
                background: linear-gradient(to top, #9333ea, #c084fc);
                border-radius: 99px;
                animation: wave-animation 1.2s ease-in-out infinite;
            }
            
            .music-wave .bar:nth-child(1) { animation-delay: -1.1s; }
            .music-wave .bar:nth-child(2) { animation-delay: -1.0s; }
            .music-wave .bar:nth-child(3) { animation-delay: -0.9s; }
            .music-wave .bar:nth-child(4) { animation-delay: -0.8s; }
            .music-wave .bar:nth-child(5) { animation-delay: -0.7s; }
            .music-wave .bar:nth-child(6) { animation-delay: -0.6s; }
            
            @keyframes wave-animation {
                0%, 40%, 100% { height: 20%; opacity: 0.6; }
                20% { height: 100%; opacity: 1; box-shadow: 0 0 15px rgba(168, 85, 247, 0.6); }
            }
            
            .loading-text {
                color: #e2e8f0;
                font-size: 1.25rem;
                font-weight: 600;
                text-align: center;
                text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            }
            
            .loading-subtext {
                color: #94a3b8;
                font-size: 0.95rem;
                margin-top: 8px;
                text-align: center;
            }
        </style>
        
        <div id="musegen-loading-container">
            <!-- Content will be injected or toggled via Gradio updates -->
        </div>
        """)
    
    loading_animation = gr.HTML("""
        <div class="music-wave">
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
        </div>
        <div class="loading-text">กำลังประพันธ์เพลง...</div>
        <div class="loading-subtext">AI กำลังวิเคราะห์และสร้างสรรค์ทำนอง</div>
    """, visible=False)

    with gr.Tabs():
        with gr.TabItem(t("tab_create_music")):
            with gr.Row():
                with gr.Column(scale=1):
                    prompt = gr.Textbox(
                        label=t("prompt"),
                        placeholder=t("prompt_placeholder"),
                        lines=3,
                    )

                    with gr.Accordion(t("adv_settings_accord"), open=True):
                        with gr.Row():
                            style = gr.Dropdown(
                                label=t("style"),
                                choices=GENRES + [(t("style_custom"), "Custom")],
                                value=["Pop"],
                                allow_custom_value=True,
                                interactive=True,
                                multiselect=True,
                                info=t("style_info"),
                            )
                            mood = gr.Dropdown(
                                label=t("mood"),
                                choices=MOODS,
                                value=["Energetic"],
                                interactive=True,
                                allow_custom_value=True,
                                multiselect=True,
                            )
                        gr.Markdown(
                            t("mood_example")
                        )

                        with gr.Row():
                            vocalist = gr.Dropdown(
                                label=t("vocalist"),
                                choices=VOCALIST_TYPES,
                                value="Any",
                                interactive=True,
                                info=t("vocalist_info"),
                            )

                        with gr.Row():
                            mode = gr.Radio(
                                label=t("mode"),
                                choices=[(t("mode_easy_desc"), "easy"), (t("mode_standard_desc"), "standard"), (t("mode_pro_desc"), "pro")],
                                value="easy",
                                info=t("mode_info"),
                                interactive=True,
                            )
                            lyrics_mode = gr.Dropdown(
                                label=t("lyrics_mode"),
                                choices=[(t("lyrics_mode_ai_desc"), "AI"), (t("lyrics_mode_custom_desc"), "Custom")],
                                value="AI",
                                interactive=True,
                            )
                            instrumental_checkbox = gr.Checkbox(
                        label=t("instrumental_label"),
                        visible=False,
                        value=False,
                        info=t("instrumental_info"),
                    )
                    with gr.Row(visible=False) as reference_row:
                        reference_upload = gr.File(
                            label=t("reference_upload"), visible=True
                        )
                    midi_upload = gr.File(label=t("midi_upload"), visible=False)
                    phonetic_text = gr.Textbox(label=t("phonetic_text"), visible=False)

                    custom_lyrics = gr.Textbox(
                        label=t("custom_lyrics"),
                        placeholder=t("custom_lyrics_placeholder"),
                        lines=8,
                        visible=False,
                        info=t("custom_lyrics_info")
                    )
                    
                    treat_parens_as_instr = gr.Checkbox(
                        label=t("treat_parens_as_instr"),
                        value=True,
                        visible=False,
                        info=t("treat_parens_as_instr_info")
                    )

                    def on_lyrics_change(mode_value, lyrics_value):
                        is_visible = (
                            lyrics_value == "Custom"
                            and mode_value in ("standard", "pro")
                        )
                        return gr.update(visible=is_visible), gr.update(visible=is_visible)

                    lyrics_mode.change(
                        on_lyrics_change,
                        inputs=[mode, lyrics_mode],
                        outputs=[custom_lyrics, treat_parens_as_instr],
                    )

                    plan_display = gr.Markdown("")
                    cost_display = gr.Markdown("")
                    gen_btn = gr.Button(
                        t("generate_btn"), variant="primary", size="lg"
                    )
                    with gr.Group(visible=False) as confirm_group:
                        confirm_text = gr.Markdown("")
                        with gr.Row():
                            confirm_btn = gr.Button(t("confirm_btn"), variant="primary")
                            confirm_cancel_btn = gr.Button(
                                t("cancel_btn"), variant="secondary"
                            )

                    with gr.Group(visible=False, elem_id="musegen-topup-card") as topup_group:
                        gr.Markdown(t("topup_title"))
                        topup_subtitle = gr.Markdown(
                            t("topup_subtitle")
                        )
                        topup_qr = gr.Image(
                            value=PAYMENT_QR_PATH,
                            visible=True,
                            width=300,
                            label=t("scan_to_pay"),
                        )
                        with gr.Row():
                            topup_quick_10 = gr.Button(t("quick_topup").format(amount=10), variant="secondary")
                            topup_quick_30 = gr.Button(t("quick_topup").format(amount=30), variant="secondary")
                            topup_quick_100 = gr.Button(t("quick_topup").format(amount=100), variant="primary")
                        topup_amount = gr.Number(
                            label=t("topup_amount_label"),
                            value=TOPUP_PACKAGES[2]["gg"],
                            precision=0,
                            minimum=GG_TOPUP_MIN,
                            step=1,
                        )
                        topup_method = gr.Dropdown(
                            label=t("payment_method"),
                            choices=[(t("pay_promptpay"), "PromptPay"), (t("pay_card"), "Card"), (t("pay_wallet"), "Wallet")],
                            value="PromptPay",
                        )
                        topup_slip_upload = gr.File(
                            label=t("upload_slip"),
                            file_types=["image"],
                        )
                        topup_note = gr.Markdown(t("topup_note"))
                        topup_pack_buttons = []
                        with gr.Row():
                            for pack in TOPUP_PACKAGES:
                                pack_label = t(f"pack_{pack['key']}")
                                label = f"{pack_label} • {pack['gg']} GG • {pack['price_thb']} {t('currency_thb')}"
                                if pack.get("bonus_pct", 0):
                                    label = f"{label} (+{int(pack['bonus_pct'] * 100)}%)"
                                topup_pack_buttons.append(
                                    gr.Button(label, variant="primary" if pack["key"] == "popular" else "secondary")
                                )
                        topup_msg = gr.Markdown("", visible=False)
                        with gr.Row():
                            topup_submit = gr.Button(t("pay_and_topup"), variant="primary")
                            topup_cancel = gr.Button(t("cancel_btn"), variant="secondary")
                        topup_resume = gr.Button(
                            t("resume_create"), variant="primary", visible=False
                        )

                with gr.Column(scale=1):
                    with gr.Row():
                        user_info_display = gr.Markdown(t("loading_user_info"))
                        credits_display = gr.Markdown(t("loading_credits"))
                        topup_open_btn = gr.Button(
                            t("topup_btn"), variant="secondary", size="sm"
                        )

                    audio_out = gr.Audio(
                        label=t("generated_song"), type="filepath", interactive=False
                    )
                    status_msg = gr.Markdown("", elem_id="musegen-status-msg")
                    job_status = gr.Markdown("")
                    job_meta = gr.Markdown("")
                    download_file = gr.File(
                        label=t("download"), interactive=False, visible=False
                    )

                    gg_left_display = gr.Markdown(visible=False)

                    gr.Markdown(t("recent_history"))
                    history_list = gr.HTML("")
        with gr.TabItem(t("admin_management"), visible=False) as admin_tab:
            with gr.Column(elem_id="musegen-admin-card"):
                gr.Markdown(t("admin_management"))
                admin_status = gr.Markdown(f"{t('admin_status')}: {t('admin_ready')}")
                with gr.Row():
                    admin_profit = gr.Markdown(t("total_profit"))
                    admin_refresh_btn = gr.Button(t("refresh"), variant="secondary")
                gr.Markdown(t("pending_topups"))
                admin_topups_table = gr.Dataframe(
                    headers=[t("col_id"), t("col_username"), t("col_amount"), t("col_date"), t("col_proof")],
                    datatype=["number", "str", "number", "str", "str"],
                    interactive=False,
                    row_count=5,
                )
                with gr.Row():
                    admin_tx_id = gr.Textbox(label=t("transaction_id"))
                    admin_approve_btn = gr.Button(t("approve"), variant="primary")
                    admin_reject_btn = gr.Button(t("reject"), variant="secondary")
                admin_action_msg = gr.Markdown("")
                gr.Markdown(t("users"))
                admin_users_table = gr.Dataframe(
                    headers=[
                        t("col_id"),
                        t("col_username"),
                        t("col_email"),
                        t("col_level"),
                        t("col_balance"),
                        t("col_created_at"),
                    ],
                    datatype=["number", "str", "str", "str", "number", "str"],
                    interactive=False,
                    row_count=10,
                )
                with gr.Row():
                    admin_target_user_id = gr.Textbox(label=t("target_user_id"))
                    admin_delete_btn = gr.Button(t("delete_user"), variant="stop")
                with gr.Row():
                    admin_add_gg_amount = gr.Textbox(label=t("amount_gg"))
                    admin_add_gg_btn = gr.Button(t("add_gg"), variant="secondary")
                with gr.Row():
                    admin_set_level_dropdown = gr.Dropdown(
                        choices=["free", "pro", "admin"], label=t("user_level")
                    )
                    admin_set_level_btn = gr.Button(t("set_level"), variant="secondary")

    return {
        "prompt": prompt,
        "style": style,
        "mood": mood,
        "mode": mode,
        "lyrics_mode": lyrics_mode,
        "custom_lyrics": custom_lyrics,
        "treat_parens_as_instr": treat_parens_as_instr,
        "instrumental_checkbox": instrumental_checkbox,
        "reference_upload": reference_upload,
        "reference_row": reference_row,
        "midi_upload": midi_upload,
        "phonetic_text": phonetic_text,
        "plan_display": plan_display,
        "cost_display": cost_display,
        "confirm_group": confirm_group,
        "confirm_text": confirm_text,
        "confirm_btn": confirm_btn,
        "confirm_cancel_btn": confirm_cancel_btn,
        "topup_group": topup_group,
        "topup_subtitle": topup_subtitle,
        "topup_qr": topup_qr,
        "topup_quick_10": topup_quick_10,
        "topup_quick_30": topup_quick_30,
        "topup_quick_100": topup_quick_100,
        "topup_amount": topup_amount,
        "topup_method": topup_method,
        "topup_slip_upload": topup_slip_upload,
        "topup_note": topup_note,
        "topup_pack_buttons": topup_pack_buttons,
        "topup_msg": topup_msg,
        "topup_submit": topup_submit,
        "topup_cancel": topup_cancel,
        "topup_resume": topup_resume,
        "topup_open_btn": topup_open_btn,
        "gen_btn": gen_btn,
        "audio_out": audio_out,
        "status_msg": status_msg,
        "job_status": job_status,
        "job_meta": job_meta,
        "download_file": download_file,
        "history_html": history_list,
        "user_info_display": user_info_display,
        "credits_display": credits_display,
        "gg_left_display": gg_left_display,
        "vocalist": vocalist,
        "admin_tab": admin_tab,
        "admin_refresh_btn": admin_refresh_btn,
        "admin_profit": admin_profit,
        "admin_topups_table": admin_topups_table,
        "admin_users_table": admin_users_table,
        "admin_status": admin_status,
        "admin_tx_id": admin_tx_id,
        "admin_approve_btn": admin_approve_btn,
        "admin_reject_btn": admin_reject_btn,
        "admin_action_msg": admin_action_msg,
        "admin_target_user_id": admin_target_user_id,
        "admin_delete_btn": admin_delete_btn,
        "admin_add_gg_amount": admin_add_gg_amount,
        "admin_add_gg_btn": admin_add_gg_btn,
        "admin_set_level_dropdown": admin_set_level_dropdown,
        "admin_set_level_btn": admin_set_level_btn,
        "loading_animation": loading_animation,
    }
