"""JSON and operation diff utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import unified_diff
from typing import Any

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer


@dataclass
class OperationDiff:
    index: int
    kind: str
    reference: dict[str, Any] | None
    generated: dict[str, Any] | None
    detail: str


def format_json(payload: Any, *, indent: int = 2) -> str:
    return json.dumps(payload, indent=indent, ensure_ascii=False)


def highlight_json(text: str, *, style: str = "monokai") -> str:
    formatter = HtmlFormatter(style=style, noclasses=True, nowrap=True)
    return highlight(text, JsonLexer(), formatter)


def unified_json_diff(reference: Any, generated: Any) -> str:
    ref_lines = format_json(reference).splitlines(keepends=True)
    gen_lines = format_json(generated).splitlines(keepends=True)
    return "".join(
        unified_diff(ref_lines, gen_lines, fromfile="ground_truth", tofile="generated", lineterm="")
    )


def compare_operations(
    reference: list[dict[str, Any]],
    generated: list[dict[str, Any]] | None,
) -> list[OperationDiff]:
    if generated is None:
        return [
            OperationDiff(index=i, kind="missing", reference=ref, generated=None, detail="No generation")
            for i, ref in enumerate(reference)
        ]

    diffs: list[OperationDiff] = []
    max_len = max(len(reference), len(generated))
    for index in range(max_len):
        ref_op = reference[index] if index < len(reference) else None
        gen_op = generated[index] if index < len(generated) else None

        if ref_op is None and gen_op is not None:
            diffs.append(
                OperationDiff(index=index, kind="extra", reference=None, generated=gen_op, detail="Extra operation")
            )
        elif ref_op is not None and gen_op is None:
            diffs.append(
                OperationDiff(
                    index=index,
                    kind="missing",
                    reference=ref_op,
                    generated=None,
                    detail="Missing operation",
                )
            )
        elif ref_op is not None and gen_op is not None:
            ref_type = ref_op.get("type")
            gen_type = gen_op.get("type")
            if ref_type != gen_type:
                diffs.append(
                    OperationDiff(
                        index=index,
                        kind="wrong_type",
                        reference=ref_op,
                        generated=gen_op,
                        detail=f"Type mismatch: {ref_type} vs {gen_type}",
                    )
                )
            elif ref_op != gen_op:
                diffs.append(
                    OperationDiff(
                        index=index,
                        kind="wrong_param",
                        reference=ref_op,
                        generated=gen_op,
                        detail="Parameter mismatch",
                    )
                )
            else:
                diffs.append(
                    OperationDiff(
                        index=index,
                        kind="match",
                        reference=ref_op,
                        generated=gen_op,
                        detail="Match",
                    )
                )
    return diffs


def annotate_json_html(
    reference: list[dict[str, Any]],
    generated: list[dict[str, Any]] | None,
) -> tuple[str, str]:
    """Return HTML snippets for reference and generated JSON with diff classes."""
    ref_payload = {"operations": reference}
    gen_payload = {"operations": generated or []}
    ref_text = format_json(ref_payload)
    gen_text = format_json(gen_payload)

    diffs = compare_operations(reference, generated)
    missing_indices = {d.index for d in diffs if d.kind == "missing"}
    extra_indices = {d.index for d in diffs if d.kind == "extra"}
    wrong_type_indices = {d.index for d in diffs if d.kind == "wrong_type"}
    wrong_param_indices = {d.index for d in diffs if d.kind == "wrong_param"}

    def _wrap_indices(text: str, indices: set[int], css_class: str, side: str) -> str:
        if not indices:
            return highlight_json(text)
        lines = text.splitlines()
        output: list[str] = []
        op_index = -1
        in_operations = False
        for line in lines:
            stripped = line.strip()
            if '"operations"' in stripped and "[" in stripped:
                in_operations = True
            if in_operations and stripped.startswith("{"):
                op_index += 1
            if op_index in indices:
                output.append(f'<span class="{css_class}">{line}</span>')
            else:
                output.append(line)
            if in_operations and stripped in ("],", "]"):
                in_operations = False
        # Fallback to pygments if line-based wrapping is too fragile
        highlighted = highlight_json("\n".join(output) if output else text)
        return highlighted.replace(
            "<pre",
            f'<pre data-side="{side}"',
            1,
        )

    ref_html = _wrap_indices(
        ref_text,
        missing_indices | wrong_type_indices | wrong_param_indices,
        "diff-missing",
        "reference",
    )
    gen_html = _wrap_indices(
        gen_text,
        extra_indices | wrong_type_indices | wrong_param_indices,
        "diff-extra",
        "generated",
    )
    return ref_html, gen_html
