import json
import os
from pathlib import Path
from typing import Optional
from app.schemas import ConfigSettings

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"


def mask_key(key: Optional[str], prefix_len: int = 6, suffix_len: int = 4) -> str:
    if not key:
        return ""
    if len(key) <= prefix_len + suffix_len:
        return "Configured"
    return f"{key[:prefix_len]}...{key[-suffix_len:]}"


def load_settings() -> ConfigSettings:
    defaults = ConfigSettings()
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults = ConfigSettings(**data)
        except Exception:
            pass

    if not defaults.google_api_key:
        defaults.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not defaults.anthropic_api_key:
        defaults.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not defaults.openai_api_key:
        defaults.openai_api_key = os.getenv("OPENAI_API_KEY")
    if not defaults.openrouter_api_key:
        defaults.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not defaults.github_token:
        defaults.github_token = os.getenv("GITHUB_TOKEN")

    if defaults.google_api_key:
        os.environ["GOOGLE_API_KEY"] = defaults.google_api_key
        os.environ["GEMINI_API_KEY"] = defaults.google_api_key
    if defaults.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = defaults.anthropic_api_key
    if defaults.openai_api_key:
        os.environ["OPENAI_API_KEY"] = defaults.openai_api_key
    if defaults.openrouter_api_key:
        os.environ["OPENROUTER_API_KEY"] = defaults.openrouter_api_key
    if defaults.github_token:
        os.environ["GITHUB_TOKEN"] = defaults.github_token

    return defaults


def save_settings(settings: ConfigSettings) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, indent=2)
    except Exception:
        pass

    if settings.google_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.google_api_key
        os.environ["GEMINI_API_KEY"] = settings.google_api_key
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.openrouter_api_key:
        os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key
    if settings.github_token:
        os.environ["GITHUB_TOKEN"] = settings.github_token
