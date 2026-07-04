"""Async HTTP client for a local ComfyUI instance.

Endpoint shapes verified against ComfyUI 0.27.0 (July 2026):
- GET  /system_stats            -> {"system": {...}, "devices": [...]}
- GET  /object_info             -> {class_type: schema, ...}  (~2.5 MB; cached here)
- GET  /models                  -> [folder, ...]
- GET  /models/{folder}         -> [filename, ...]
- GET  /templates/index.json    -> [{"moduleName", "templates": [...]}, ...]
- GET  /templates/{name}.json   -> UI-format workflow JSON (schema 0.4)
- POST /prompt                  -> {"prompt_id", "number"} | 400 {"error", "node_errors"}
- GET  /history/{prompt_id}     -> {prompt_id: {...}}
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from ..config import Config


class ComfyValidationError(Exception):
    """ComfyUI rejected a prompt at validation time."""

    def __init__(self, error: dict[str, Any], node_errors: dict[str, Any]):
        self.error = error
        self.node_errors = node_errors
        message = error.get("message", "prompt validation failed")
        super().__init__(f"{message}; node_errors={list(node_errors)}")


class ComfyClient:
    def __init__(self, config: Config):
        self._config = config
        self.base_url = config.comfyui_url
        self.client_id = uuid.uuid4().hex
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=config.request_timeout)
        self._object_info: dict[str, Any] | None = None

    async def close(self) -> None:
        await self._http.aclose()

    async def _get_json(self, path: str) -> Any:
        response = await self._http.get(path)
        response.raise_for_status()
        return response.json()

    async def get_system_stats(self) -> dict[str, Any]:
        return await self._get_json("/system_stats")

    async def get_object_info(self, refresh: bool = False) -> dict[str, Any]:
        if self._object_info is None or refresh:
            self._object_info = await self._get_json("/object_info")
        return self._object_info

    async def list_model_folders(self) -> list[str]:
        return await self._get_json("/models")

    async def list_models(self, folder: str) -> list[str]:
        return await self._get_json(f"/models/{folder}")

    async def get_template_index(self) -> list[dict[str, Any]]:
        return await self._get_json("/templates/index.json")

    async def get_template_workflow(self, name: str) -> dict[str, Any]:
        return await self._get_json(f"/templates/{name}.json")

    async def queue_prompt(self, api_prompt: dict[str, Any], extra_data: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"prompt": api_prompt, "client_id": self.client_id}
        if extra_data:
            payload["extra_data"] = extra_data
        response = await self._http.post("/prompt", json=payload)
        if response.status_code == 400:
            body = response.json()
            raise ComfyValidationError(body.get("error", {}), body.get("node_errors", {}))
        response.raise_for_status()
        return response.json()

    async def get_history(self, prompt_id: str) -> dict[str, Any]:
        history = await self._get_json(f"/history/{prompt_id}")
        return history.get(prompt_id, {})

    async def get_queue(self) -> dict[str, Any]:
        return await self._get_json("/queue")

    async def interrupt(self) -> None:
        response = await self._http.post("/interrupt")
        response.raise_for_status()
