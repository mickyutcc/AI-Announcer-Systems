import argparse
import sys

import config

# If run directly, try to run the main CLI
if __name__ == "__main__":

    # Check if arguments are provided. If not, launch UI.
    if len(sys.argv) == 1:
        print("🎵 Starting MuseGenx1000 AI Studio Suite...")
        try:
            import main_ui

            demo, theme, css = main_ui.create_main_ui()
            # Pass theme to launch() as per Gradio 6.0 warning
            demo.launch(
                server_port=config.GRADIO_SERVER_PORT,
                server_name=config.GRADIO_SERVER_NAME,
                share=False,
                theme=theme,
                css=css,
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
