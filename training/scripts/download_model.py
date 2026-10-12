#!/usr/bin/env python3
"""Download and verify a Hugging Face model for the training pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.config import load_config  # noqa: E402
from training.models import get_model_loader  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download and verify the configured Hugging Face model and tokenizer.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "training" / "configs" / "qwen_3b.yaml",
        help="Training pipeline config YAML.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    loader = get_model_loader(config)

    print(f"Downloading tokenizer: {config.model.hf_model_id}")
    tokenizer = loader.load_tokenizer(config)
    print(f"Downloading model: {config.model.hf_model_id}")
    model = loader.load_model(config, for_inference=True)

    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    param_count = sum(parameter.numel() for parameter in model.parameters())
    print("----------------------------------------")
    print("Model download successful")
    print(f"Model ID        : {config.model.hf_model_id}")
    print(f"Family          : {config.model.family}")
    print(f"Tokenizer class : {tokenizer.__class__.__name__}")
    print(f"Model class     : {model.__class__.__name__}")
    print(f"Parameters      : {param_count:,}")
    print("Tokenizer and model load correctly.")
    print("----------------------------------------")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
