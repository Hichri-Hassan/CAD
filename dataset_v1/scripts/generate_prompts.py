"""Generate natural-language prompts from a CAD JSON document."""

from __future__ import annotations

from typing import Any

from dataset_v1.scripts.openai_client import OpenAIClient, OpenAIClientError
from dataset_v1.scripts.summary_generator import generate_summary, summary_to_text


def generate_prompt_metadata(
    cad_json: dict[str, Any],
    *,
    client: OpenAIClient | None = None,
    use_openai: bool = True,
) -> dict[str, Any]:
    """Return title, description, tags, and prompts for one model."""
    summary = generate_summary(cad_json)
    summary_text = summary_to_text(summary)

    if use_openai:
        if client is None:
            client = OpenAIClient()
        try:
            return client.generate_prompts(summary_text)
        except OpenAIClientError:
            raise

    return _fallback_prompt_metadata(summary, summary_text)


def _fallback_prompt_metadata(summary: dict[str, Any], summary_text: str) -> dict[str, Any]:
    """Deterministic placeholder metadata when OpenAI is unavailable."""
    counts = summary.get("feature_counts", {})
    unit = summary.get("unit", "mm")
    dims = summary.get("dimensions", {})
    height = dims.get("extrusion_heights", [None])[0]

    shape_label = _fallback_shape_label(counts)
    title = shape_label.title()

    parts = [f"A {shape_label}"]
    if counts.get("holes"):
        parts.append(f"with {counts['holes']} hole(s)")
    if counts.get("pockets"):
        parts.append(f"and {counts['pockets']} recessed pocket(s)")
    description = " ".join(parts) + "."

    prompts = [
        f"{shape_label}, please.",
        f"I need a {shape_label} modeled in {unit}.",
        _geometry_focused_prompt(shape_label, counts),
        _dimension_focused_prompt(shape_label, height, unit),
        f"Could you model a {shape_label} like the one described?",
    ]

    tags = ["mechanical", shape_label.replace(" ", "-")]
    if counts.get("holes"):
        tags.append("holes")
    if counts.get("pockets"):
        tags.append("pockets")

    return {
        "title": title,
        "description": description,
        "tags": tags[:6],
        "prompts": prompts,
    }


def _fallback_shape_label(counts: dict[str, int]) -> str:
    if counts.get("pockets"):
        return "rectangular plate with pockets"
    if counts.get("holes"):
        return "rectangular block with holes"
    return "rectangular block"


def _geometry_focused_prompt(shape_label: str, counts: dict[str, int]) -> str:
    details = []
    if counts.get("pockets"):
        details.append("recessed pockets")
    if counts.get("fillets"):
        details.append("rounded corners")
    if counts.get("chamfers"):
        details.append("chamfered edges")
    if details:
        return f"A {shape_label} with {', '.join(details)}."
    return f"A simple {shape_label}."


def _dimension_focused_prompt(shape_label: str, height: float | None, unit: str) -> str:
    if height is not None:
        return f"Build a {shape_label} about {height} {unit} tall."
    return f"Build a {shape_label} to the sizes in the spec."
