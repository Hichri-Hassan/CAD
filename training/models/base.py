"""Model loader interfaces for the training pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from training.config import PipelineConfig


@dataclass(frozen=True)
class LoadedModel:
    """A tokenizer and causal LM ready for inference or future fine-tuning."""

    tokenizer: PreTrainedTokenizerBase
    model: PreTrainedModel
    device: torch.device
    config: PipelineConfig


class ModelLoader(ABC):
    """Family-specific model loading logic."""

    family: str

    @abstractmethod
    def load_tokenizer(self, config: PipelineConfig) -> PreTrainedTokenizerBase:
        """Download and load the tokenizer."""

    @abstractmethod
    def load_model(
        self,
        config: PipelineConfig,
        *,
        for_inference: bool = True,
    ) -> PreTrainedModel:
        """Download and load the causal language model."""

    def load(self, config: PipelineConfig, *, for_inference: bool = True) -> LoadedModel:
        tokenizer = self.load_tokenizer(config)
        model = self.load_model(config, for_inference=for_inference)
        device = resolve_device(model)
        return LoadedModel(
            tokenizer=tokenizer,
            model=model,
            device=device,
            config=config,
        )


def resolve_device(model: PreTrainedModel) -> torch.device:
    """Return the device where model parameters are located."""
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cpu")


def resolve_torch_dtype() -> torch.dtype:
    """Pick a reasonable default dtype for local inference."""
    if torch.cuda.is_available():
        return torch.float16
    if torch.backends.mps.is_available():
        return torch.float16
    return torch.float32


def move_inputs_to_device(inputs: dict[str, Any], device: torch.device) -> dict[str, Any]:
    """Move tokenized tensors to the target device."""
    moved: dict[str, Any] = {}
    for key, value in inputs.items():
        if hasattr(value, "to"):
            moved[key] = value.to(device)
        else:
            moved[key] = value
    return moved
