"""save_workflow must never overwrite an existing workflow file by default."""

import pytest

from comfy_draftsman import server
from comfy_draftsman.graph.model import Workflow
from comfy_draftsman.session import Session


class FakeClient:
    """Mimics ComfyClient's userdata conflict behavior."""

    def __init__(self, existing: set[str]):
        self.existing = set(existing)
        self.saved: list[str] = []

    async def get_object_info(self, refresh: bool = False):
        return {}

    async def save_userdata_workflow(self, name, document, overwrite: bool = False):
        filename = name if name.endswith(".json") else f"{name}.json"
        if filename in self.existing and not overwrite:
            raise FileExistsError(filename)
        self.existing.add(filename)
        self.saved.append(filename)
        return filename


@pytest.fixture
def wired(tmp_path, config, monkeypatch):
    client = FakeClient(existing={"menu.json"})
    session = Session(tmp_path / "sessions")
    monkeypatch.setattr(server._State, "config", config)
    monkeypatch.setattr(server._State, "client", client)
    monkeypatch.setattr(server._State, "session", session)
    wf_id = session.create(Workflow.new(), title="t")
    return client, wf_id


async def test_save_renames_instead_of_clobbering(wired):
    client, wf_id = wired
    result = await server.save_workflow(wf_id, "menu")
    assert result["saved"] is True
    assert client.saved == ["menu (draftsman).json"]
    assert result["renamed_from"] == "menu"
    assert "menu.json" in client.existing  # original untouched


async def test_save_free_name_needs_no_rename(wired):
    client, wf_id = wired
    result = await server.save_workflow(wf_id, "fresh")
    assert result["saved"] is True
    assert client.saved == ["fresh.json"]
    assert result["renamed_from"] is None


async def test_save_overwrite_true_replaces(wired):
    client, wf_id = wired
    result = await server.save_workflow(wf_id, "menu", overwrite=True)
    assert result["saved"] is True
    assert client.saved == ["menu.json"]
    assert result["renamed_from"] is None
