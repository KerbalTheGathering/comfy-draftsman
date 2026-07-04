"""Mapping between UI-format widgets_values arrays and named inputs.

ComfyUI's UI format stores widget values as a positional array whose order is the
node schema's input declaration order (required section first, then optional),
counting only *widget* inputs (primitives / combos), and inserting synthetic
slots the frontend adds:

- ``control_after_generate`` (e.g. 'randomize'/'fixed') right after any input
  whose schema options set ``control_after_generate: true``
- an upload-button slot after inputs with ``image_upload: true``

Connection-typed inputs (MODEL, CLIP, LATENT, ...) never consume a slot, but
widget inputs that have been *converted to inputs* (connected) still do.
"""

from __future__ import annotations

from typing import Any

PRIMITIVE_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN"}

CONTROL_SUFFIX = "__control_after_generate"
UPLOAD_SUFFIX = "__upload"
SYNTHETIC_SUFFIXES = (CONTROL_SUFFIX, UPLOAD_SUFFIX)


def _iter_schema_inputs(schema: dict[str, Any]):
    """Yield (name, spec) over required then optional inputs, in declaration order."""
    inputs = schema.get("input", {})
    for section in ("required", "optional"):
        yield from inputs.get(section, {}).items()


def is_widget_input(spec: Any) -> bool:
    """True if this input spec renders as a widget (consumes a widgets_values slot)."""
    if not isinstance(spec, list | tuple) or not spec:
        return False
    kind = spec[0]
    opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
    if opts.get("forceInput"):
        return False
    if isinstance(kind, list):  # legacy COMBO: list of choices
        return True
    if kind == "COMBO":  # V3-style COMBO
        return True
    return kind in PRIMITIVE_TYPES


def widget_slot_names(class_type: str, object_info: dict[str, Any]) -> list[str]:
    """Ordered widgets_values slot names for a node class, including synthetic slots."""
    schema = object_info.get(class_type)
    if schema is None:
        raise ValueError(f"unknown node class: {class_type}")
    slots: list[str] = []
    for name, spec in _iter_schema_inputs(schema):
        if not is_widget_input(spec):
            continue
        slots.append(name)
        opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
        if opts.get("control_after_generate"):
            slots.append(name + CONTROL_SUFFIX)
        if opts.get("image_upload"):
            slots.append(name + UPLOAD_SUFFIX)
    return slots


def widget_defaults(class_type: str, object_info: dict[str, Any]) -> list[Any]:
    """Default widgets_values array for a freshly created node."""
    schema = object_info[class_type]
    specs = dict(_iter_schema_inputs(schema))
    values: list[Any] = []
    for slot in widget_slot_names(class_type, object_info):
        if slot.endswith(CONTROL_SUFFIX):
            values.append("fixed")
            continue
        if slot.endswith(UPLOAD_SUFFIX):
            values.append("image")
            continue
        spec = specs[slot]
        kind = spec[0]
        opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
        if "default" in opts:
            values.append(opts["default"])
        elif isinstance(kind, list):
            values.append(kind[0] if kind else None)
        elif kind == "COMBO":
            options = opts.get("options", [])
            values.append(options[0] if options else None)
        elif kind == "INT":
            values.append(0)
        elif kind == "FLOAT":
            values.append(0.0)
        elif kind == "BOOLEAN":
            values.append(False)
        else:
            values.append("")
    return values


def widgets_to_named(
    class_type: str, widgets_values: list[Any], object_info: dict[str, Any]
) -> dict[str, Any]:
    """Map a positional widgets_values array to {input_name: value}.

    Synthetic slots are included under their suffixed names. A short or long
    array is tolerated (custom frontend versions drift): missing slots are
    omitted, extras ignored.
    """
    if isinstance(widgets_values, dict):  # some nodes serialize as dict already
        return dict(widgets_values)
    named: dict[str, Any] = {}
    slots = widget_slot_names(class_type, object_info)
    for slot, value in zip(slots, widgets_values or [], strict=False):
        named[slot] = value
    return named


def named_to_widgets(
    class_type: str, named: dict[str, Any], object_info: dict[str, Any]
) -> list[Any]:
    """Build a positional widgets_values array from named values, defaults filling gaps."""
    values = widget_defaults(class_type, object_info)
    slots = widget_slot_names(class_type, object_info)
    for i, slot in enumerate(slots):
        if slot in named:
            values[i] = named[slot]
    return values
