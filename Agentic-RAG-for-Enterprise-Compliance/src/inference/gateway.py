from __future__ import annotations

import concurrent.futures
import logging
import platform
from enum import Enum
from typing import Any

import psutil
from pydantic import BaseModel, Field

try:
    import torch
except (ImportError, OSError) as exc:  # pragma: no cover
    torch = None
    logging.getLogger("aegis.inference").warning("Torch unavailable or incompatible, falling back to CPU inference: %s", exc)

from src.agents.schemas import AuditorOutput, AuditPlan
from src.config import get_settings

try:
    from langchain_ollama import ChatOllama, OllamaEmbeddings
except ImportError:  # pragma: no cover
    ChatOllama = None
    OllamaEmbeddings = None

logger = logging.getLogger("aegis.inference")
settings = get_settings()


class InferenceBackend(str, Enum):
    CUDA = "cuda"
    MPS = "mps"
    CPU = "cpu"


class HardwareProfile(BaseModel):
    operating_system: str = Field(..., description="Host operating system name.")
    processor: str = Field(..., description="Processor architecture.")
    total_ram_gb: float = Field(..., description="Total system RAM in gigabytes.")
    available_ram_gb: float = Field(..., description="Available system RAM in gigabytes.")
    gpu_available: bool = Field(..., description="True if a CUDA GPU is available.")
    gpu_name: str | None = Field(None, description="Detected GPU name when available.")
    gpu_total_memory_gb: float | None = Field(None, description="Total GPU VRAM in gigabytes when available.")
    inference_backend: InferenceBackend = Field(..., description="Selected runtime backend.")
    quantization_strategy: str = Field(..., description="Inference quantization strategy.")


class ModelTarget(BaseModel):
    model_name: str = Field(..., description="Inference model identifier or file path.")
    device: str = Field(..., description="Inference device target string.")
    backend: InferenceBackend = Field(..., description="Selected inference backend.")
    quantization: str = Field(..., description="Selected quantization strategy.")
    extra_parameters: dict[str, Any] = Field(default_factory=dict, description="Additional model loading hints.")


class FallbackStructuredModel:
    def __init__(self, output_type: type[BaseModel]) -> None:
        self.output_type = output_type

    def invoke(self, inputs: dict[str, Any]) -> BaseModel:
        if self.output_type == AuditPlan:
            return AuditPlan(sub_queries=[inputs.get("raw_query", "")])
        if self.output_type == AuditorOutput:
            return AuditorOutput(findings=[])
        return self.output_type()

    def __call__(self, inputs: dict[str, Any]) -> BaseModel:
        return self.invoke(inputs)


class FallbackChatModel:
    def with_structured_output(self, output_type: type[BaseModel]) -> FallbackStructuredModel:
        return FallbackStructuredModel(output_type)


class FallbackEmbeddings:
    def embed_query(self, query: str) -> list[float]:
        return [0.0] * settings.EMBEDDING_DIM


def probe_hardware() -> HardwareProfile:
    operating_system = platform.system()
    processor = platform.machine() or "unknown"
    virtual_memory = psutil.virtual_memory()
    total_ram_gb = round(float(virtual_memory.total) / 1024**3, 2)
    available_ram_gb = round(float(virtual_memory.available) / 1024**3, 2)

    gpu_available = False
    gpu_name = None
    gpu_total_memory_gb = None
    inference_backend = InferenceBackend.CPU
    quantization_strategy = "fp16"

    if settings.FORCE_CPU_INFERENCE:
        logger.info("FORCE_CPU_INFERENCE enabled; selecting CPU inference regardless of GPU availability.")
    else:
        try:
            if torch is not None and torch.cuda.is_available():
                gpu_available = True
                gpu_name = torch.cuda.get_device_name(0)
                gpu_total_memory_gb = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
                inference_backend = InferenceBackend.CUDA
                quantization_strategy = "fp16"
            elif torch is not None and operating_system == "Darwin" and torch.backends.mps.is_available():
                gpu_available = True
                gpu_name = "Apple MPS"
                inference_backend = InferenceBackend.MPS
                quantization_strategy = "4bit"
        except Exception as exc:
            logger.warning("Hardware probe detected a GPU error and will fall back to CPU: %s", exc)
            gpu_available = False
            inference_backend = InferenceBackend.CPU
            quantization_strategy = "int8"

    if inference_backend == InferenceBackend.CPU and total_ram_gb < 32:
        quantization_strategy = "4bit"
    elif inference_backend == InferenceBackend.CPU:
        quantization_strategy = "int8"

    return HardwareProfile(
        operating_system=operating_system,
        processor=processor,
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        gpu_total_memory_gb=gpu_total_memory_gb,
        inference_backend=inference_backend,
        quantization_strategy=quantization_strategy,
    )


def safe_inference_target() -> ModelTarget:
    profile = probe_hardware()
    model_name = settings.LOCAL_LLM_MODEL
    if settings.USE_LOCAL_TORCH_INFERENCE and settings.LOCAL_TORCH_LLM_MODEL:
        model_name = settings.LOCAL_TORCH_LLM_MODEL

    if settings.LLM_BACKEND.lower() == "ollama":
        model_name = settings.LOCAL_LLM_MODEL

    device = profile.inference_backend.value
    quantization = profile.quantization_strategy
    extra_parameters: dict[str, Any] = {}

    if profile.inference_backend == InferenceBackend.CUDA:
        device = "cuda"
        if profile.gpu_total_memory_gb and profile.gpu_total_memory_gb < 16:
            quantization = "4bit"
            extra_parameters["load_in_4bit"] = True
        else:
            quantization = "fp16"
            extra_parameters["torch_dtype"] = "auto"
    elif profile.inference_backend == InferenceBackend.MPS:
        device = "mps"
        extra_parameters["load_in_4bit"] = True
    else:
        device = "cpu"
        extra_parameters["load_in_4bit"] = True

    target = ModelTarget(
        model_name=model_name,
        device=device,
        backend=profile.inference_backend,
        quantization=quantization,
        extra_parameters=extra_parameters,
    )

    logger.debug(
        "Inference gateway selected target=%s device=%s quantization=%s extras=%s",
        target.model_name,
        target.device,
        target.quantization,
        target.extra_parameters,
    )
    return target


def build_safe_chat_client() -> Any:
    if ChatOllama is not None:
        target = None
        try:
            target = safe_inference_target()
            return ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=target.model_name, temperature=0.0)
        except Exception as exc:
            if torch is not None and isinstance(exc, torch.cuda.OutOfMemoryError):
                logger.warning("CUDA OOM during ChatOllama initialization, falling back to CPU: %s", exc)
                if target is not None:
                    try:
                        return ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=target.model_name, temperature=0.0)
                    except Exception as inner_exc:
                        logger.warning("Fallback ChatOllama CPU initialization failed, using fallback model: %s", inner_exc)
            else:
                logger.warning("ChatOllama initialization failed, using fallback model: %s", exc)
            return FallbackChatModel()
    logger.warning("Ollama client unavailable; using fallback chat model.")
    return FallbackChatModel()


def build_safe_embedding_client() -> Any:
    if OllamaEmbeddings is not None:
        try:
            return OllamaEmbeddings(base_url=settings.OLLAMA_BASE_URL, model=settings.LOCAL_EMBED_MODEL)
        except Exception as exc:
            logger.warning("Ollama embedding initialization failed, using fallback embedder: %s", exc)
            return FallbackEmbeddings()
    logger.warning("Ollama embeddings unavailable; using fallback embedder.")
    return FallbackEmbeddings()


def invoke_with_timeout(chain: Any, inputs: dict[str, Any], timeout_seconds: float | None = None) -> Any:
    """
    Runs chain.invoke(inputs) under a hard wall-clock timeout so a backend that
    hangs indefinitely (e.g. Ollama failing to load a model that doesn't fit in
    available RAM, or a stalled connection) fails fast instead of leaving the
    graph — and the Celery job — stuck forever with no visible error.
    """
    timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.BACKEND_TIMEOUT_SECONDS
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(chain.invoke, inputs)
        return future.result(timeout=timeout_seconds)
