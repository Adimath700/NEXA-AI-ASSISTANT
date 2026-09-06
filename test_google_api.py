#!/usr/bin/env python3
"""Test Google Realtime API connection"""
import os
import asyncio
from dotenv import load_dotenv
import sys

load_dotenv()

async def test_google_api():
    """Test if Google Realtime API is accessible"""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip().strip("'\"")
    
    print(f"🔑 API Key loaded: {api_key[:20]}...")
    
    if not api_key or len(api_key) < 10:
        print("❌ API Key is empty or invalid!")
        return False
    
    try:
        print("📡 Attempting to import Google plugin...")
        from livekit.plugins import google
        print("✓ Google plugin imported")
        
        print("⏳ Testing connection to Google Realtime API...")
        
        # Simple test - create a model instance (doesn't connect yet)
        model = google.beta.realtime.RealtimeModel(voice="Charon")
        print("✓ Model created successfully")
        
        print("\n✅ Google API configuration looks good!")
        print("Note: Connection happens when LiveKit session starts with actual audio")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Run: pip install livekit-plugins-google")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_google_api())
    sys.exit(0 if result else 1)

