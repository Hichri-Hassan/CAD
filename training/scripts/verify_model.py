#!/usr/bin/env python3
"""Run a simple inference check for the configured local model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.config import load_config  # noqa: E402
from training.models import load_model_bundle  # noqa: E402
from training.models.base import move_inputs_to_device  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify local model inference with a simple prompt.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "training" / "configs" / "qwen_3b.yaml",
        help="Training pipeline config YAML.",
    )
    parser.add_argument(
        "--prompt",
        default="Say hello.",
        help="User prompt for the verification run.",
    )
    return parser


def generate_response(bundle, prompt: str) -> str:
    tokenizer = bundle.tokenizer
    model = bundle.model
    config = bundle.config

    messages = [{"role": "user", "content": prompt}]
    if hasattr(tokenizer, "apply_chat_template"):
        chat_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        chat_text = prompt

    inputs = tokenizer(chat_text, return_tensors="pt")
    inputs = move_inputs_to_device(inputs, bundle.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=config.inference.max_new_tokens,
            temperature=config.inference.temperature,
            do_sample=config.inference.do_sample,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0, inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)

    print(f"Loading model: {config.model.hf_model_id}")
    bundle = load_model_bundle(config, for_inference=True)

    if bundle.tokenizer.pad_token is None and bundle.tokenizer.eos_token is not None:
        bundle.tokenizer.pad_token = bundle.tokenizer.eos_token

    print(f"Prompt: {args.prompt}")
    response = generate_response(bundle, args.prompt)
    print(f"Response: {response}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
