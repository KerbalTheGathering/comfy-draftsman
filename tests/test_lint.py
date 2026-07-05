"""Lint rule: wired positive prompts need a Show Text preview node."""

import json
from pathlib import Path

import pytest

from comfy_draftsman.graph.lint import lint
from comfy_draftsman.graph.model import Workflow

FIXTURES = Path(__file__).parent / "fixtures"

SHOWTEXT_SCHEMA = {
    "input": {"required": {"text": ["STRING", {"forceInput": True}]}},
    "output": ["STRING"],
    "output_node": True,
    "category": "utils",
    "display_name": "Show Text",
}
WILDCARD_SCHEMA = {
    "input": {"required": {"wildcard_text": ["STRING", {"multiline": True, "default": ""}]}},
    "output": ["STRING"],
    "category": "custom/text",
    "display_name": "Wildcard Text",
}


@pytest.fixture(scope="module")
def object_info():
    info = json.loads((FIXTURES / "object_info_trimmed.json").read_text(encoding="utf-8"))
    info["ShowText|pys"] = SHOWTEXT_SCHEMA
    info["WildcardText"] = WILDCARD_SCHEMA
    return info


def _base(object_info, *, wire_wildcard_to, via_showtext=False):
    """txt2img graph; wildcard node optionally wired into one encoder's text."""
    wf = Workflow.new()
    ckpt = wf.add_node("CheckpointLoaderSimple", object_info=object_info)
    pos = wf.add_node("CLIPTextEncode", object_info=object_info, title="pos")
    neg = wf.add_node("CLIPTextEncode", object_info=object_info, title="neg")
    sampler = wf.add_node("KSampler", object_info=object_info)
    wf.connect(ckpt.id, "CLIP", pos.id, "clip")
    wf.connect(ckpt.id, "CLIP", neg.id, "clip")
    wf.connect(ckpt.id, "MODEL", sampler.id, "model")
    wf.connect(pos.id, "CONDITIONING", sampler.id, "positive")
    wf.connect(neg.id, "CONDITIONING", sampler.id, "negative")
    target = {"pos": pos, "neg": neg}[wire_wildcard_to] if wire_wildcard_to else None
    if target is not None:
        wildcard = wf.add_node("WildcardText", object_info=object_info)
        if via_showtext:
            show = wf.add_node("ShowText|pys", object_info=object_info)
            wf.connect(wildcard.id, 0, show.id, "text", object_info)
            wf.connect(show.id, 0, target.id, "text", object_info)
        else:
            wf.connect(wildcard.id, 0, target.id, "text", object_info)
    return wf, pos


def test_wired_positive_prompt_without_preview_is_flagged(object_info):
    wf, pos = _base(object_info, wire_wildcard_to="pos")
    findings = lint(wf, object_info)
    hits = [f for f in findings if f["code"] == "no-prompt-preview"]
    assert hits and hits[0]["node_id"] == pos.id, findings


def test_wired_positive_prompt_with_showtext_is_clean(object_info):
    wf, _pos = _base(object_info, wire_wildcard_to="pos", via_showtext=True)
    findings = lint(wf, object_info)
    assert not [f for f in findings if f["code"] == "no-prompt-preview"], findings


def test_hand_typed_prompt_not_flagged(object_info):
    wf, _pos = _base(object_info, wire_wildcard_to=None)
    findings = lint(wf, object_info)
    assert not [f for f in findings if f["code"] == "no-prompt-preview"], findings


def test_wired_negative_prompt_not_flagged(object_info):
    wf, _pos = _base(object_info, wire_wildcard_to="neg")
    findings = lint(wf, object_info)
    assert not [f for f in findings if f["code"] == "no-prompt-preview"], findings
