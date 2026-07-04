import pytest

from comfy_draftsman.config import Config


@pytest.fixture
def config(tmp_path):
    return Config(
        comfyui_url="http://comfy.test",
        registry_url="http://registry.test",
        session_dir=tmp_path / "sessions",
        request_timeout=5.0,
    )
