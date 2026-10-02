import pytest
from app.schemas import SubTask, TaskDomain, ModelProvider, ConfigSettings
from app.router import DynamicModelRouter
from app.settings_manager import mask_key, save_settings, load_settings


def test_mask_key():
    assert mask_key("") == ""
    assert mask_key("short") == "Configured"
    assert mask_key("AIzaSyAbcd123456789XyZ") == "AIzaSy...9XyZ"


def test_settings_persistence(tmp_path, monkeypatch):
    test_file = tmp_path / "settings.json"
    monkeypatch.setattr("app.settings_manager.SETTINGS_FILE", test_file)

    cfg = ConfigSettings(
        google_api_key="AIzaSyTestGoogleKey123",
        simulation_mode=False,
        preferred_cloud_provider="gemini",
    )
    save_settings(cfg)
    assert test_file.exists()

    loaded = load_settings()
    assert loaded.google_api_key == "AIzaSyTestGoogleKey123"
    assert loaded.simulation_mode is False
    assert loaded.preferred_cloud_provider == "gemini"


def test_router_gemini_priority():
    router = DynamicModelRouter(
        cost_constrained=False,
        force_simulator=False,
        preferred_cloud_provider="gemini",
        has_google_key=True,
    )
    task = SubTask(
        task_id="t1",
        title="Implementation Task",
        description="Write C# Script",
        domain=TaskDomain.IMPLEMENTATION,
        complexity=8,
    )
    model, reason = router.route_task(task)
    assert model == ModelProvider.GEMINI_PRO
    assert "Google Gemini" in reason


def test_router_auto_detect_google_key():
    router = DynamicModelRouter(
        cost_constrained=False,
        force_simulator=False,
        preferred_cloud_provider="auto",
        has_google_key=True,
        has_anthropic_key=False,
        has_openai_key=False,
    )
    task = SubTask(
        task_id="t1",
        title="Code Task",
        description="Write code",
        domain=TaskDomain.IMPLEMENTATION,
        complexity=7,
    )
    model, reason = router.route_task(task)
    assert model == ModelProvider.GEMINI_PRO
