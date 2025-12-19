import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.config import settings as app_settings
    print(f"app.config.settings.groq_api_key: {'Set' if app_settings.groq_api_key else 'Not Set'}")
except Exception as e:
    print(f"Error loading app.config: {e}")

try:
    from src.config.settings import settings as src_settings
    print(f"src.config.settings.GROQ_API_KEY: {'Set' if src_settings.GROQ_API_KEY else 'Not Set'}")
except Exception as e:
    print(f"Error loading src.config.settings: {e}")
