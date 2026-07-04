"""Unit tests for the ComfyUI HTTP client (mocked transport via respx)."""

import httpx
import pytest
import respx

from comfy_draftsman.comfy.client import ComfyClient

BASE = "http://comfy.test"


@pytest.fixture
def client(config):
    return ComfyClient(config)


@respx.mock
async def test_get_system_stats(client):
    respx.get(f"{BASE}/system_stats").mock(
        return_value=httpx.Response(200, json={"system": {"comfyui_version": "0.27.0"}})
    )
    stats = await client.get_system_stats()
    assert stats["system"]["comfyui_version"] == "0.27.0"


@respx.mock
async def test_object_info_is_cached(client):
    route = respx.get(f"{BASE}/object_info").mock(
        return_value=httpx.Response(200, json={"KSampler": {"name": "KSampler"}})
    )
    first = await client.get_object_info()
    second = await client.get_object_info()
    assert first == second
    assert route.call_count == 1


@respx.mock
async def test_object_info_refresh_bypasses_cache(client):
    route = respx.get(f"{BASE}/object_info").mock(
        return_value=httpx.Response(200, json={"KSampler": {}})
    )
    await client.get_object_info()
    await client.get_object_info(refresh=True)
    assert route.call_count == 2


@respx.mock
async def test_list_models(client):
    respx.get(f"{BASE}/models/checkpoints").mock(
        return_value=httpx.Response(200, json=["a.safetensors", "sub\\b.safetensors"])
    )
    models = await client.list_models("checkpoints")
    assert models == ["a.safetensors", "sub\\b.safetensors"]


@respx.mock
async def test_list_model_folders(client):
    respx.get(f"{BASE}/models").mock(
        return_value=httpx.Response(200, json=["checkpoints", "loras"])
    )
    assert await client.list_model_folders() == ["checkpoints", "loras"]


@respx.mock
async def test_get_template_index(client):
    respx.get(f"{BASE}/templates/index.json").mock(
        return_value=httpx.Response(
            200,
            json=[{"moduleName": "default", "templates": [{"name": "sdxl_simple_example"}]}],
        )
    )
    index = await client.get_template_index()
    assert index[0]["templates"][0]["name"] == "sdxl_simple_example"


@respx.mock
async def test_get_template_workflow(client):
    respx.get(f"{BASE}/templates/sdxl_simple_example.json").mock(
        return_value=httpx.Response(200, json={"version": 0.4, "nodes": []})
    )
    wf = await client.get_template_workflow("sdxl_simple_example")
    assert wf["version"] == 0.4


@respx.mock
async def test_queue_prompt_posts_api_format(client):
    route = respx.post(f"{BASE}/prompt").mock(
        return_value=httpx.Response(200, json={"prompt_id": "abc", "number": 3})
    )
    result = await client.queue_prompt({"1": {"class_type": "KSampler", "inputs": {}}})
    assert result["prompt_id"] == "abc"
    sent = route.calls[0].request
    import json

    body = json.loads(sent.content)
    assert body["prompt"]["1"]["class_type"] == "KSampler"
    assert body["client_id"] == client.client_id


@respx.mock
async def test_queue_prompt_validation_error_raises_with_details(client):
    respx.post(f"{BASE}/prompt").mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {"type": "prompt_outputs_failed_validation", "message": "bad"},
                "node_errors": {"3": {"errors": [{"message": "value not in list"}]}},
            },
        )
    )
    from comfy_draftsman.comfy.client import ComfyValidationError

    with pytest.raises(ComfyValidationError) as exc:
        await client.queue_prompt({"3": {"class_type": "X", "inputs": {}}})
    assert "3" in exc.value.node_errors


@respx.mock
async def test_get_history_for_prompt(client):
    respx.get(f"{BASE}/history/abc").mock(
        return_value=httpx.Response(200, json={"abc": {"status": {"completed": True}}})
    )
    hist = await client.get_history("abc")
    assert hist["status"]["completed"] is True
