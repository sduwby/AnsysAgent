"""
LLM 配置管理。

职责：
1. 从环境变量 / 用户数据目录 .env 读取当前 LLM 配置
2. 为 ChatAgent 提供 provider 元数据、回退链和能力判断
3. 通过 /config 向导将配置持久化到 ANSYS_DATA_DIR/.env
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from agent.paths import ANSYS_DATA_DIR

ENV_PATH = ANSYS_DATA_DIR / ".env"

PROVIDERS: dict[str, dict[str, Any]] = {
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "openai/gpt-oss-120b:free",
            "qwen/qwen3-next-80b-a3b-instruct:free",
            "z-ai/glm-4.5-air:free",
            "minimax/minimax-m2.5:free",
        ],
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["GPT-5.2", "gpt-4o"],
    },
    "qwen": {
        "name": "Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"],
    },
    "gemini": {
        "name": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "models": ["gemini-3.0-flash"],
    },
    "glm": {
        "name": "GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "models": ["glm-4.6", "glm-4.7"],
    },
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimaxi.com/v1",
        "models": ["minimax-m2"],
    },
}

FALLBACK_CHAIN = ["openrouter", "openai", "glm", "minimax"]

_LEGACY_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "glm": "ZHIPUAI_API_KEY",
    "minimax": "MINIMAX_API_KEY",
}

_BUILTIN_API_KEYS = {
    "gemini": "AIzaSyCKqwy6JrrhnPq0tGRvvfiQLN1MTbQsgqo",
}

_THINKING_MODEL_HINTS = {
    "openrouter": (
        "openai/gpt-oss-120b",
        "z-ai/glm-4.5-air",
        "minimax/minimax-m2.5",
    ),
    "deepseek": ("deepseek-reasoner",),
    "openai": ("gpt-5", "o1", "o3", "o4"),
    "qwen": (),
    "gemini": ("gemini-3.0", "gemini-2.5", "gemini-2.0-thinking"),
    "glm": ("glm-4.6", "glm-4.7"),
    "minimax": ("minimax-m2", "minimax-m2.5"),
}

_PROVIDER_CHOICES = [
    ("openrouter", "OpenRouter"),
    ("deepseek", "DeepSeek"),
    ("openai", "ChatGPT"),
    ("qwen", "Qwen"),
    ("gemini", "Gemini"),
    ("glm", "GLM"),
    ("minimax", "MiniMax"),
]


@dataclass(slots=True)
class LLMConfig:
    provider: str
    api_key: str
    model: str
    base_url: str
    thinking_enabled: bool = False


def _ensure_env_loaded() -> None:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on", "y", "开启"}


def _normalize_provider(provider: str | None) -> str:
    key = (provider or "").strip().lower()
    return key if key in PROVIDERS else "openrouter"


def get_provider_api_key(provider: str) -> str:
    _ensure_env_loaded()
    provider = _normalize_provider(provider)

    generic_key = os.getenv("LLM_API_KEY", "").strip()
    provider_key = os.getenv(f"LLM_API_KEY_{provider.upper()}", "").strip()
    legacy_key = os.getenv(_LEGACY_KEY_ENV.get(provider, ""), "").strip()
    builtin_key = _BUILTIN_API_KEYS.get(provider, "")

    if provider_key:
        return provider_key
    if generic_key and provider == _normalize_provider(os.getenv("LLM_PROVIDER")):
        return generic_key
    if legacy_key:
        return legacy_key
    if builtin_key:
        return builtin_key
    if generic_key:
        return generic_key
    return ""


def load_llm_config() -> LLMConfig:
    _ensure_env_loaded()

    provider = _normalize_provider(os.getenv("LLM_PROVIDER"))
    provider_info = PROVIDERS[provider]
    model = (os.getenv("LLM_MODEL") or "").strip() or provider_info["models"][0]
    api_key = get_provider_api_key(provider)
    thinking_enabled = _truthy(os.getenv("LLM_THINKING"))

    return LLMConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=provider_info["base_url"],
        thinking_enabled=thinking_enabled,
    )


def model_supports_thinking(provider: str, model: str) -> bool:
    provider = _normalize_provider(provider)
    normalized_model = (model or "").strip().lower()
    hints = _THINKING_MODEL_HINTS.get(provider, ())
    return any(hint.lower() in normalized_model for hint in hints)


def _persist_env_value(key: str, value: str) -> None:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_PATH.exists():
        ENV_PATH.write_text("", encoding="utf-8")
    set_key(str(ENV_PATH), key, value, quote_mode="never")
    os.environ[key] = value


def set_thinking_enabled(enabled: bool) -> None:
    _persist_env_value("LLM_THINKING", "true" if enabled else "false")


def _set_provider_config(provider: str, api_key: str, model: str) -> None:
    _persist_env_value("LLM_PROVIDER", provider)
    _persist_env_value("LLM_MODEL", model)
    if api_key.strip():
        _persist_env_value(f"LLM_API_KEY_{provider.upper()}", api_key.strip())
        if provider == _normalize_provider(os.getenv("LLM_PROVIDER")):
            _persist_env_value("LLM_API_KEY", api_key.strip())


def run_config_wizard(console: Console) -> None:
    _ensure_env_loaded()
    current = load_llm_config()

    lines = []
    for idx, (key, label) in enumerate(_PROVIDER_CHOICES, start=1):
        marker = "  [green](当前)[/green]" if key == current.provider else ""
        lines.append(f"[{idx}] {label}{marker}")

    console.print(Panel(
        "\n".join(lines),
        title="LLM 配置向导",
        border_style="green",
        padding=(0, 2),
    ))

    default_index = next(
        (str(idx) for idx, (key, _) in enumerate(_PROVIDER_CHOICES, start=1) if key == current.provider),
        "1",
    )
    provider_input = Prompt.ask("请选择提供商", default=default_index).strip()
    try:
        provider = _PROVIDER_CHOICES[int(provider_input) - 1][0]
    except (ValueError, IndexError):
        console.print("[red]无效的提供商编号。[/red]")
        return

    provider_info = PROVIDERS[provider]
    current_key = get_provider_api_key(provider)
    key_hint = current_key[:6] + "..." if current_key else "未配置"
    api_key = Prompt.ask(
        f"请输入 API Key [dim](留空则保留当前：{key_hint})[/dim]",
        default="",
        show_default=False,
    ).strip() or current_key

    model_lines = [f"[{idx}] {name}" for idx, name in enumerate(provider_info["models"], start=1)]
    console.print(Panel(
        "\n".join(model_lines),
        title=f"{provider_info['name']} 可选模型",
        border_style="cyan",
        padding=(0, 2),
    ))

    current_model = current.model if current.provider == provider else provider_info["models"][0]
    default_model_index = next(
        (str(idx) for idx, name in enumerate(provider_info["models"], start=1) if name == current_model),
        "1",
    )
    model_input = Prompt.ask("请选择模型编号", default=default_model_index).strip()
    try:
        model = provider_info["models"][int(model_input) - 1]
    except (ValueError, IndexError):
        console.print("[red]无效的模型编号。[/red]")
        return

    _set_provider_config(provider, api_key, model)

    if not model_supports_thinking(provider, model):
        set_thinking_enabled(False)
    elif "LLM_THINKING" not in os.environ:
        set_thinking_enabled(False)

    console.print(
        f"[green]✓ 配置已保存[/green]\n"
        f"[dim]Provider:[/dim] {provider_info['name']}\n"
        f"[dim]Model:[/dim] {model}"
    )
