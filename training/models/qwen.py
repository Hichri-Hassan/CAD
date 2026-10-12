"""Qwen model family loader."""

from __future__ import annotations

from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from training.config import PipelineConfig
from training.models.base import ModelLoader, resolve_torch_dtype


def _hf_kwargs(config: PipelineConfig) -> dict:
    kwargs = {"trust_remote_code": config.model.trust_remote_code}
    if config.paths.hf_cache is not None:
        kwargs["cache_dir"] = str(config.paths.hf_cache)
    return kwargs


class QwenModelLoader(ModelLoader):
    family = "qwen"

    def load_tokenizer(self, config: PipelineConfig) -> PreTrainedTokenizerBase:
        return AutoTokenizer.from_pretrained(
            config.model.hf_model_id,
            **_hf_kwargs(config),
        )

    def load_model(
        self,
        config: PipelineConfig,
        *,
        for_inference: bool = True,
    ) -> PreTrainedModel:
        dtype = resolve_torch_dtype()
        model_kwargs: dict = {
            **_hf_kwargs(config),
            "dtype": dtype,
        }

        # QLoRA hooks will attach here later when training.qlora.enabled is true.
        if for_inference:
            model_kwargs["device_map"] = "auto" if _supports_device_map() else None

        model = AutoModelForCausalLM.from_pretrained(
            config.model.hf_model_id,
            **model_kwargs,
        )

        if model_kwargs.get("device_map") is None:
            model = model.to(_fallback_device())

        if for_inference:
            model.eval()

        return model


def _supports_device_map() -> bool:
    import torch

    return torch.cuda.is_available()


def _fallback_device():
    import torch

    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
