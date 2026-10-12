"""Model loading and generation for the evaluation dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from training.dataset import load_system_prompt
from training.evaluation_app.config import AppPaths, default_paths
from training.scripts.evaluate_generation import (
    extract_json_object,
    generate_operations,
    load_adapter_bundle,
    validate_training_schema,
)


@dataclass
class GenerationResult:
    raw_text: str
    payload: dict[str, Any] | None
    json_valid: bool
    schema_valid: bool
    operations: list[dict[str, Any]] | None
    seed: int | None = None


class InferenceService:
    def __init__(self, paths: AppPaths | None = None) -> None:
        self.paths = paths or default_paths()
        self._model = None
        self._tokenizer = None
        self._device = None
        self._pipeline_config = None
        self._system_prompt: str | None = None
        self._loaded_adapter: Path | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self.is_loaded and self._loaded_adapter == self.paths.adapter:
            return
        if self.is_loaded:
            self.unload()
        if not self.paths.adapter.exists():
            raise FileNotFoundError(f"Adapter not found: {self.paths.adapter}")
        model, tokenizer, device, pipeline_config = load_adapter_bundle(
            self.paths.adapter,
            self.paths.config,
        )
        self._model = model
        self._tokenizer = tokenizer
        self._device = device
        self._pipeline_config = pipeline_config
        self._system_prompt = load_system_prompt(self.paths.system_prompt)
        self._loaded_adapter = self.paths.adapter

    def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        self._device = None
        self._pipeline_config = None
        self._system_prompt = None
        self._loaded_adapter = None

    def generate(
        self,
        prompt: str,
        *,
        max_new_tokens: int = 4096,
        temperature: float | None = None,
        do_sample: bool | None = None,
        seed: int | None = None,
    ) -> GenerationResult:
        self.load()
        assert self._model is not None
        assert self._tokenizer is not None
        assert self._device is not None
        assert self._pipeline_config is not None
        assert self._system_prompt is not None

        if seed is not None:
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)

        temp = temperature if temperature is not None else self._pipeline_config.inference.temperature
        sample = do_sample if do_sample is not None else self._pipeline_config.inference.do_sample

        raw_text = generate_operations(
            self._model,
            self._tokenizer,
            self._device,
            prompt=prompt,
            system_prompt=self._system_prompt,
            max_new_tokens=max_new_tokens,
            temperature=temp,
            do_sample=sample,
        )
        payload = extract_json_object(raw_text)
        json_valid = payload is not None
        schema_valid = bool(payload and validate_training_schema(payload))
        operations = payload.get("operations") if isinstance(payload, dict) else None
        if not isinstance(operations, list):
            operations = None

        return GenerationResult(
            raw_text=raw_text,
            payload=payload,
            json_valid=json_valid,
            schema_valid=schema_valid,
            operations=operations,
            seed=seed,
        )

    def generate_many(
        self,
        prompt: str,
        *,
        count: int,
        base_seed: int = 42,
        **kwargs: Any,
    ) -> list[GenerationResult]:
        return [self.generate(prompt, seed=base_seed + i, **kwargs) for i in range(count)]
