from dotenv import load_dotenv

import os
import sys
import subprocess
import logging
import asyncio

from google.genai import types

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import google, noise_cancellation

from NEXA_screenshot import screenshot_tool
from NEXA_google_search import google_search, get_current_datetime
from memory.jarvis_memory import (
    load_memory,
    save_memory,
    get_recent_conversations,
    add_memory_entry,
)
from NEXA_get_whether import get_weather
from NEXA_window_CTRL import open, close, folder_file
from NEXA_file_open import Play_file

from keyboard_mouse_CTRL import (
    move_cursor_tool,
    mouse_click_tool,
    scroll_cursor_tool,
    type_text_tool,
    press_key_tool,
    swipe_gesture_tool,
    press_hotkey_tool,
    control_volume_tool,
)

from flipkart import (
    flipkart_buy_cod,
    flipkart_buy_cod_auto,
    flipkart_buy_auto,
)

from ip_address import get_ip_info

from youtube import (
    play_song,
    download_favourite_song,
    share_favourite_song_whatsapp,
)

from image_to_pdf import image_to_pdf
from image_generate import generate_image_tool
from object_detection import detect_objects
from file_search import jarvis_file_search_command
from thinking import JarvisAutoThinking


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
    except Exception:
        pass

    for env_path in (
        os.path.join(base_dir, ".env"),
        os.path.join(os.path.dirname(base_dir), ".env"),
    ):
        if os.path.exists(env_path):
            load_dotenv(env_path)
            break


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

logger = logging.getLogger("NEXA")


# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_LIVE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
GEMINI_VOICE = "Charon"
GEMINI_TEMPERATURE = 0.5

# Gemini 2.5 Flash supports thinking_budget=0.
# Disabling thinking is intentional here because NEXA is a
# realtime voice assistant where low latency is more important
# than deep reasoning for ordinary conversation.
GEMINI_THINKING_CONFIG = types.ThinkingConfig(
    thinking_budget=0,
    include_thoughts=False,
)

# Compact instructions are intentionally used instead of the
# very large original behavior/reply prompt combination.
NEXA_INSTRUCTIONS = """
You are NEXA, a fast personal AI voice assistant.

Address the user as Sir when appropriate.

Speak naturally and concisely. Prefer Hindi/Hinglish when the user speaks
Hindi/Hinglish, and use English when the user speaks English.

You have tools for web search, date/time, weather, memory, files,
Windows/application control, keyboard and mouse control, screenshots,
vision, media, YouTube, image generation, object detection, networking,
shopping, and file search.

Use a tool when the user's request requires real information or an action.
For simple conversation, answer immediately without unnecessary tools.

Never claim an action succeeded unless the relevant tool actually succeeded.
If a tool fails, briefly explain the failure.

For greetings and simple questions, keep the spoken response short.
Do not repeat the user's question unnecessarily.

Priorities:
1. Correctness
2. Fast response
3. Appropriate tool use
4. Concise natural speech

You are a realtime voice assistant, so avoid long explanations unless
the user explicitly asks for detail.
"""


# ============================================================
# API CHECK
# ============================================================

if not os.getenv("GOOGLE_API_KEY"):
    raise RuntimeError(
        "\n❌ GOOGLE_API_KEY was not found.\n"
        "Check the .env file in the NEXA project folder.\n"
    )


# ============================================================
# ASSISTANT
# ============================================================

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=NEXA_INSTRUCTIONS,
            tools=[
                # Information
                google_search,
                get_current_datetime,
                get_weather,

                # Memory
                load_memory,
                save_memory,
                get_recent_conversations,
                add_memory_entry,

                # Windows / files
                open,
                close,
                folder_file,
                Play_file,

                # Vision / screen
                screenshot_tool,
                detect_objects,

                # Keyboard / mouse
                move_cursor_tool,
                mouse_click_tool,
                scroll_cursor_tool,
                type_text_tool,
                press_key_tool,
                press_hotkey_tool,
                control_volume_tool,
                swipe_gesture_tool,

                # Images / documents
                image_to_pdf,
                generate_image_tool,

                # Shopping
                flipkart_buy_cod,
                flipkart_buy_cod_auto,
                flipkart_buy_auto,

                # Network
                get_ip_info,

                # Media
                play_song,
                download_favourite_song,
                share_favourite_song_whatsapp,

                # File search
                jarvis_file_search_command,
            ],
        )


# ============================================================
# LIVEKIT ENTRYPOINT
# ============================================================

async def entrypoint(ctx: agents.JobContext):
    print("\n" + "=" * 62)
    print("🚀 NEXA AI ASSISTANT STARTING")
    print("=" * 62)
    print(f"🧠 Gemini model : {GEMINI_LIVE_MODEL}")
    print(f"🎙️ Voice        : {GEMINI_VOICE}")
    print("⚡ Thinking     : DISABLED for low latency")
    print("📝 Prompt       : COMPACT")
    print("🔐 Google API   : configured")
    print("=" * 62)

    # Start the existing background assistant.
    try:
        auto_thinker = JarvisAutoThinking()
        print("🧠 JarvisAutoThinking background assistant started")
    except Exception as e:
        auto_thinker = None
        print(f"⚠️ AutoThinking could not start: {e}")

    try:
        print("\n🔄 Creating Gemini Live session...")

        session = AgentSession(
            llm=google.beta.realtime.RealtimeModel(
                model=GEMINI_LIVE_MODEL,
                voice=GEMINI_VOICE,
                temperature=GEMINI_TEMPERATURE,
                instructions=NEXA_INSTRUCTIONS,
                thinking_config=GEMINI_THINKING_CONFIG,
            )
        )

        print("🔄 Starting LiveKit session...")

        await session.start(
            room=ctx.room,
            agent=Assistant(),
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
                video_enabled=False,
            ),
        )

        await ctx.connect()

        print("\n" + "=" * 62)
        print("✅ NEXA IS ONLINE")
        print("=" * 62)
        print(f"🧠 Model      : {GEMINI_LIVE_MODEL}")
        print(f"🎙️ Voice      : {GEMINI_VOICE}")
        print("🎤 Microphone : READY")
        print("🔊 Speaker    : READY")
        print("🛠️ Tools      : READY")
        print("💾 Memory     : READY")
        print("⚡ Thinking   : OFF")
        print("=" * 62)
        print("🎧 Waiting for your command...")
        print("=" * 62 + "\n")

        # Do NOT call session.generate_reply() here.
        # NEXA waits for the user and Gemini Live handles the
        # response automatically.
        await asyncio.Event().wait()

    except asyncio.CancelledError:
        print("\n⛔ NEXA session cancelled")
        raise

    except KeyboardInterrupt:
        print("\n⛔ NEXA stopped by user")

    except Exception as e:
        print(f"\n❌ NEXA session error: {e}")
        logger.exception("NEXA session failure")
        raise


# ============================================================
# GUI
# ============================================================

def start_nexa_gui():
    """Start the NEXA GUI in a separate process."""

    try:
        gui_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "NEXA_gui.py",
        )

        if not os.path.exists(gui_path):
            print("⚠️ NEXA_gui.py not found.")
            print("   Voice agent will continue without GUI.")
            return

        print("🖥️ Starting NEXA GUI...")

        subprocess.Popen(
            [sys.executable, gui_path],
            stdout=None,
            stderr=None,
            stdin=None,
            close_fds=True,
        )

        print("✅ NEXA GUI started")

    except Exception as e:
        print(f"⚠️ Failed to start NEXA GUI: {e}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                  N.E.X.A. AI ASSISTANT                 ║")
    print("║                 LOW-LATENCY VOICE MODE                 ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    start_nexa_gui()

    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
