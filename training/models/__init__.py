"""Model loader registry."""

from __future__ import annotations

from training.config import PipelineConfig
from training.models.base import LoadedModel, ModelLoader
from training.models.qwen import QwenModelLoader

_LOADERS: dict[str, ModelLoader] = {
    QwenModelLoader.family: QwenModelLoader(),
}


def get_model_loader(config: PipelineConfig) -> ModelLoader:
    """Return the loader for the configured model family."""
    loader = _LOADERS.get(config.model.family)
    if loader is None:
        supported = ", ".join(sorted(_LOADERS))
        raise ValueError(
            f"Unsupported model family '{config.model.family}'. Supported families: {supported}"
        )
    return loader


def load_model_bundle(
    config: PipelineConfig,
    *,
    for_inference: bool = True,
) -> LoadedModel:
    """Load tokenizer and model using the configured family loader."""
    return get_model_loader(config).load(config, for_inference=for_inference)
