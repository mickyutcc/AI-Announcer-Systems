import argparse
import os
import sys

import config

REQUEST_TIMEOUT: int = config.REQUEST_TIMEOUT
SUNO_TIMEOUT: int = config.SUNO_TIMEOUT
MAX_POLL_SECONDS: int = config.MAX_POLL_SECONDS
RETRY_DELAY: int = config.RETRY_DELAY
FAL_KEY: str = config.FAL_KEY
GOAPI_KEY: str = config.GOAPI_KEY
ASSETS_DIR: str = config.ASSETS_DIR
MUSIC_BACKEND: str = config.MUSIC_BACKEND
SUNO_SERVER_URL: str = config.SUNO_SERVER_URL
SUNO_COOKIE: str = config.SUNO_COOKIE
TWOCAPTCHA_KEY: str = config.TWOCAPTCHA_KEY
GENERATE_URL: str = config.GENERATE_URL
FETCH_URL: str = config.FETCH_URL
FREE_CREDITS: int = 9

# If run directly, try to run the main CLI
if __name__ == "__main__":

    # Check if arguments are provided. If not, launch UI.
    if len(sys.argv) == 1:
        print("🎵 Starting MuseGenx1000 AI Studio Suite...")
        try:
            # Metrics server is started in main_ui.create_main_ui() via prometheus_metrics module
            
            import voice_clone
            voice_clone.start_cache_cleanup_worker()
            import main_ui
            import uvicorn
            from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
            from fastapi.middleware.cors import CORSMiddleware
            from prometheus_fastapi_instrumentator import Instrumentator
            from pydantic import BaseModel
            from sqlalchemy.orm import Session
            import gradio as gr
            
            # App modules
            from database_setup import get_db
            import handlers_subscription_manual
            import handlers_subscription_admin
            import user_db

            # Create FastAPI app
            app = FastAPI()
            
            # Instrument FastAPI for Prometheus metrics
            Instrumentator().instrument(app).expose(app)
            
            # CORS
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            @app.get("/healthz")
            def health_check():
                return {"status": "ok"}
                
            # --- API Endpoints for Smoke Test & Integration ---
            
            class FileWrapper:
                def __init__(self, upload_file):
                    self.upload_file = upload_file
                    self.filename = upload_file.filename
                def read(self):
                    return self.upload_file.file.read()

            @app.post("/api/subscriptions")
            def create_subscription(
                user_id: int = Form(...),
                plan: str = Form(...),
                payment_ref: str = Form(...),
                file: UploadFile = File(...),
                db: Session = Depends(get_db)
            ):
                result = handlers_subscription_manual.create_subscription_request(
                    user_id=user_id,
                    plan=plan,
                    payment_ref=payment_ref,
                    file_obj=FileWrapper(file),
                    db_session=db
                )
                if result.get("status") == "ERROR":
                    raise HTTPException(status_code=400, detail=result.get("message"))
                return result

            class ApproveRequest(BaseModel):
                admin_id: int
                period_days: int = 30

            @app.post("/api/admin/subscriptions/{subscription_id}/approve")
            def approve_subscription(
                subscription_id: int,
                req: ApproveRequest,
                db: Session = Depends(get_db)
            ):
                result = handlers_subscription_admin.admin_approve_subscription(
                    admin_id=req.admin_id,
                    subscription_id=subscription_id,
                    db_session=db,
                    user_db=user_db,
                    period_days=req.period_days
                )
                if not result.get("ok"):
                    raise HTTPException(status_code=400, detail=result.get("msg"))
                return result
            # --------------------------------------------------

            demo, theme, css = main_ui.create_main_ui()
            
            # Mount Gradio app to FastAPI
            # Theme and CSS are passed to gr.Blocks in create_main_ui
            app = gr.mount_gradio_app(app, demo, path="/")

            print(f"🚀 Starting server on {config.GRADIO_SERVER_NAME}:{config.GRADIO_SERVER_PORT}")
            uvicorn.run(
                app,
                host=config.GRADIO_SERVER_NAME,
                port=int(config.GRADIO_SERVER_PORT),
            )
        except ImportError as e:
            print(f"❌ Error launching UI: {e}")
            print(
                "Please ensure requirements are installed: pip install -r requirements.txt"
            )
        except Exception as e:
            print(f"❌ System Error: {e}")
    else:
        # Run CLI mode
        # เพิ่ม argument สำหรับเลือกสำเนียงภาษา
        parser = argparse.ArgumentParser(description="MuseGenx1000 CLI")
        parser.add_argument(
            "--accent",
            type=str,
            default="thai",
            help="Accent for song generation (default: thai)",
        )
        args, unknown = parser.parse_known_args()
        # ส่ง accent ไปยัง main.main()
        try:
            import main

            main.main(accent=args.accent)
        except ImportError:
            print("Error: Could not import main.py")
            sys.exit(1)
