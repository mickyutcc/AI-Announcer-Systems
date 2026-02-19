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
)


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
    btn_label = "Unavailable" if cost < 0 else f"🎵 Generate Song ({cost} GG)"
    if needs_upgrade:
        btn_label = f"Upgrade required • {btn_label}"
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
        gr.update(value=f"**Cost:** {cost} GG" if cost >= 0 else "**Cost:** -"),
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
                value=f"Upgrade required • 🎵 Generate Song ({max(cost, 0)} GG)",
            ),
            gr.update(value=f"**Cost:** {max(cost, 0)} GG"),
            gr.update(visible=False),
            "กรุณาอัปเกรดแพ็กเกจเพื่อใช้งานโหมดนี้",
        )
    if cost < 0:
        return (
            gr.update(
                interactive=False,
                value="Instrumental: Pro only (Upgrade)",
            ),
            gr.update(value="**Cost:** -"),
            gr.update(visible=False),
            "Instrumental ใช้ได้เฉพาะ Pro เท่านั้น",
        )
    return (
        gr.update(interactive=True, value=f"🎵 Generate Song ({cost} GG)"),
        gr.update(value=f"**Cost:** {cost} GG"),
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
            "กรุณาอัปเกรดแพ็กเกจเพื่อใช้งานโหมดนี้",
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
            "Instrumental ใช้ได้เฉพาะ Pro เท่านั้น",
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
            "ยอดเครดิตไม่พอ — เติมขั้นต่ำ 10 GG",
            gr.update(visible=False),
            "",
            gr.update(visible=True),
            gr.update(
                visible=True,
                value="เติมขั้นต่ำ 10 GG / เลือกแพ็กเพื่อรับโบนัส",
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
    confirm_text = (
        f"ใช้ {cost} GG เพื่อสร้างเพลงนี้ เหลือ {user_credits - cost} GG ยืนยันหรือไม่?"
    )
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
    gr.Markdown("### 🎙️ Voice Lab - Text to Speech")
    gr.Markdown(
        "Convert text to lifelike speech using ElevenLabs technology. Supports Thai language."
    )

    with gr.Row():
        with gr.Column(scale=1):
            voice_text = gr.Textbox(
                label="Text to Speech",
                placeholder="พิมพ์ข้อความที่นี่... (รองรับภาษาไทย)",
                lines=5,
            )

            with gr.Row():
                voice_id = gr.Dropdown(
                    label="Voice ID",
                    choices=[
                        ("Rachel (American, Calm)", "21m00Tcm4TlvDq8ikWAM"),
                        ("Domi (American, Strong)", "AZnzlk1XvdvUeBnXmlld"),
                        ("Bella (American, Soft)", "EXAVITQu4vr4xnSDxMaL"),
                        ("Antoni (American, Deep)", "ErXwobaYiN019PkySvjV"),
                        ("Josh (American, Deep)", "TxGEqnHWrfWFTfGW9XjX"),
                    ],
                    value="21m00Tcm4TlvDq8ikWAM",
                    allow_custom_value=True,
                    info="Select a preset or enter a custom Voice ID",
                )
                voice_model = gr.Dropdown(
                    label="Model",
                    choices=[
                        "eleven_multilingual_v2",
                        "eleven_monolingual_v1",
                        "eleven_turbo_v2",
                    ],
                    value="eleven_multilingual_v2",
                    info="Use Multilingual v2 for Thai",
                )

            with gr.Accordion("Advanced Settings", open=False):
                stability = gr.Slider(
                    label="Stability",
                    minimum=0.0,
                    maximum=1.0,
                    value=0.4,
                    step=0.05,
                    info="Lower = more expressive/unstable, Higher = more consistent/monotone",
                )
                similarity = gr.Slider(
                    label="Similarity Boost",
                    minimum=0.0,
                    maximum=1.0,
                    value=0.1,
                    step=0.05,
                    info="Higher = closer to original voice, Lower = more generation variation (Recommended ~0.1 for Thai)",
                )
                consent_checkbox = gr.Checkbox(
                    label="ยืนยันสิทธิ์และความยินยอมในการสร้างเสียง", value=False
                )

            gen_btn = gr.Button("Generate Speech (2 GG)", variant="primary", size="lg")

        with gr.Column(scale=1):
            voice_output = gr.Audio(
                label="Generated Audio", type="filepath", interactive=False
            )
            voice_status = gr.Markdown("")

            gr.Markdown("#### Tips for Thai Language")
            gr.Info(
                "Use 'eleven_multilingual_v2' for best Thai results. Adjust Stability to 0.35-0.5 for natural intonation."
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
        "### <span id='musegen-hero'>MuseGenx1000 • AI Music Engine v2.0</span>"
    )
    gr.HTML("""
        <style>
            #musegen-status-msg { display: none !important; }
            #musegen-loading {
                display: none;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 24px;
                background: rgba(15, 23, 42, 0.9);
                border-radius: 16px;
                margin-bottom: 20px;
                border: 1px solid rgba(168, 85, 247, 0.3);
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            }
            #musegen-loading.loading { display: flex; }
            /* ... animations ... */
        </style>
        
        <div id="musegen-loading">
            <h3 style="color: #e2e8f0;">Creating your masterpiece...</h3>
        </div>
        """)

    with gr.Tabs():
        with gr.TabItem("Generate"):
            with gr.Row():
                with gr.Column(scale=1):
                    prompt = gr.Textbox(
                        label="Song Description (Prompt)",
                        placeholder="A sad song about a robot who fell in love with a toaster...",
                        lines=3,
                    )

                    with gr.Accordion("Advanced Settings", open=True):
                        with gr.Row():
                            style = gr.Dropdown(
                                label="Musical Style",
                                choices=GENRES + ["Custom"],
                                value=["Pop"],
                                allow_custom_value=True,
                                interactive=True,
                                multiselect=True,
                                info="เลือกแนวเพลง — จะถูกแปลงเป็นคำสั่งสำหรับตัวสร้างดนตรี",
                            )
                            mood = gr.Dropdown(
                                label="Mood",
                                choices=MOODS,
                                value=["Energetic"],
                                interactive=True,
                                allow_custom_value=True,
                                multiselect=True,
                            )
                        gr.Markdown(
                            "ตัวอย่าง: เลือก “ลูกทุ่ง” หรือ “หมอลำ” ถ้าต้องการสำเนียงไทยพื้นบ้าน"
                        )

                        with gr.Row():
                            vocalist = gr.Dropdown(
                                label="Vocalist Type",
                                choices=[
                                    "Male",
                                    "Female",
                                    "Duet",
                                    "Choir",
                                    "Child",
                                    "Elderly",
                                    "Robot",
                                    "Non-binary",
                                    "Any",
                                ],
                                value="Any",
                                interactive=True,
                                info="Select the type of vocalist",
                            )

                        with gr.Row():
                            mode = gr.Radio(
                                label="Generation Mode",
                                choices=["easy", "standard", "pro"],
                                value="easy",
                                info="Easy=Quick, Standard=Balanced, Pro=High Quality",
                                interactive=True,
                            )
                            lyrics_mode = gr.Dropdown(
                                label="Lyrics Mode",
                                choices=["AI", "Custom"],
                                value="AI",
                                interactive=True,
                            )
                    instrumental_checkbox = gr.Checkbox(
                        label="Add Instrumental (+3 GG, Pro only)",
                        visible=False,
                        value=False,
                        info="Available on Pro",
                    )
                    with gr.Row(visible=False) as reference_row:
                        reference_upload = gr.File(
                            label="Reference Upload", visible=True
                        )
                    midi_upload = gr.File(label="MIDI Upload", visible=False)
                    phonetic_text = gr.Textbox(label="Phonetic Guide", visible=False)

                    custom_lyrics = gr.Textbox(
                        label="Custom Lyrics",
                        placeholder="Enter your lyrics here...",
                        lines=8,
                        visible=False,
                        info="ข้อความในวงเล็บจะไม่ถูกร้อง หากต้องการให้เป็นเสียงเครื่องดนตรีให้วางในช่อง Instrumental/Notes"
                    )
                    
                    treat_parens_as_instr = gr.Checkbox(
                        label="Treat parenthetical lines as instructions (not sung)",
                        value=True,
                        visible=False,
                        info="หากเปิดใช้งาน ข้อความใน (วงเล็บ) จะถูกส่งเป็นคำสั่งดนตรีและจะไม่ถูกร้อง"
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
                        "🎵 Generate Song (6 GG)", variant="primary", size="lg"
                    )
                    with gr.Group(visible=False) as confirm_group:
                        confirm_text = gr.Markdown("")
                        with gr.Row():
                            confirm_btn = gr.Button("Confirm", variant="primary")
                            confirm_cancel_btn = gr.Button(
                                "Cancel", variant="secondary"
                            )

                    with gr.Group(visible=False, elem_id="musegen-topup-card") as topup_group:
                        gr.Markdown("### เติมเครดิต GG (ขั้นต่ำ 10 GG)")
                        topup_subtitle = gr.Markdown(
                            "ใส่จำนวน (ขั้นต่ำ 10 GG) หรือเลือกแพ็กด้านล่าง"
                        )
                        topup_qr = gr.Image(
                            value=PAYMENT_QR_PATH,
                            visible=True,
                            width=300,
                            label="Scan to Pay",
                        )
                        with gr.Row():
                            topup_quick_10 = gr.Button("10 GG", variant="secondary")
                            topup_quick_30 = gr.Button("30 GG", variant="secondary")
                            topup_quick_100 = gr.Button("100 GG", variant="primary")
                        topup_amount = gr.Number(
                            label="จำนวน GG ที่ต้องการเติม",
                            value=TOPUP_PACKAGES[2]["gg"],
                            precision=0,
                            minimum=GG_TOPUP_MIN,
                            step=1,
                        )
                        topup_method = gr.Dropdown(
                            label="ช่องทางชำระเงิน",
                            choices=["PromptPay", "Card", "Wallet"],
                            value="PromptPay",
                        )
                        topup_slip_upload = gr.File(
                            label="อัปโหลดสลิปการโอนเงิน",
                            file_types=["image"],
                        )
                        topup_note = gr.Markdown("เติมขั้นต่ำ 10 GG / เลือกแพ็กเพื่อรับโบนัส")
                        topup_pack_buttons = []
                        with gr.Row():
                            for pack in TOPUP_PACKAGES:
                                label = f"{pack['label']} • {pack['gg']} GG • {pack['price_thb']} THB"
                                if pack.get("bonus_pct", 0):
                                    label = f"{label} (+{int(pack['bonus_pct'] * 100)}%)"
                                topup_pack_buttons.append(
                                    gr.Button(label, variant="primary" if pack["key"] == "popular" else "secondary")
                                )
                        topup_msg = gr.Markdown("", visible=False)
                        with gr.Row():
                            topup_submit = gr.Button("ชำระและเติมเครดิต", variant="primary")
                            topup_cancel = gr.Button("ยกเลิก", variant="secondary")
                        topup_resume = gr.Button(
                            "กลับไปสร้างเพลง (ใช้ 6 GG)", variant="primary", visible=False
                        )

                with gr.Column(scale=1):
                    with gr.Row():
                        user_info_display = gr.Markdown("Loading user info...")
                        credits_display = gr.Markdown("Loading credits...")
                        topup_open_btn = gr.Button(
                            "เติมเครดิต", variant="secondary", size="sm"
                        )

                    audio_out = gr.Audio(
                        label="Generated Song", type="filepath", interactive=False
                    )
                    status_msg = gr.Markdown("", elem_id="musegen-status-msg")
                    job_status = gr.Markdown("")
                    job_meta = gr.Markdown("")
                    download_file = gr.File(
                        label="Download", interactive=False, visible=False
                    )

                    gg_left_display = gr.Markdown(visible=False)

                    gr.Markdown("### Recent History")
                    history_list = gr.HTML("")
        with gr.TabItem("Admin Management", visible=False) as admin_tab:
            with gr.Column(elem_id="musegen-admin-card"):
                gr.Markdown("### Admin Management")
                admin_status = gr.Markdown("Ready")
                with gr.Row():
                    admin_profit = gr.Markdown("Total Profit: N/A")
                    admin_refresh_btn = gr.Button("Refresh", variant="secondary")
                gr.Markdown("#### Pending Topups")
                admin_topups_table = gr.Dataframe(
                    headers=["ID", "Username", "Amount", "Date", "Proof"],
                    datatype=["number", "str", "number", "str", "str"],
                    interactive=False,
                    row_count=5,
                )
                with gr.Row():
                    admin_tx_id = gr.Textbox(label="Transaction ID")
                    admin_approve_btn = gr.Button("Approve", variant="primary")
                    admin_reject_btn = gr.Button("Reject", variant="secondary")
                admin_action_msg = gr.Markdown("")
                gr.Markdown("#### Users")
                admin_users_table = gr.Dataframe(
                    headers=[
                        "ID",
                        "Username",
                        "Email",
                        "Level",
                        "Balance",
                        "Created At",
                    ],
                    datatype=["number", "str", "str", "str", "number", "str"],
                    interactive=False,
                    row_count=10,
                )

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
    }
