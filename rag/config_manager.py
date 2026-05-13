"""配置管理工具 - 支持动态添加自定义嵌入提供商"""

from __future__ import annotations

import os
from pathlib import Path

# 环境变量键名前缀
ENV_PROVIDER = "EMBEDDING_PROVIDER"
ENV_LOCAL_MODEL = "EMBEDDING_MODEL"

# 默认值
DEFAULT_PROVIDER = "local"
DEFAULT_LOCAL_MODEL = "all-MiniLM-L6-v2"
DEFAULT_SF_MODEL = "BAAI/bge-m3"
DEFAULT_SF_URL = "https://api.siliconflow.cn/v1"

# 内置提供商配置
BUILTIN_PROVIDERS = {
    "local": {
        "name": "本地模型",
        "description": "使用本地 sentence-transformers 模型，无需网络",
        "requires_api_key": False,
        "default_model": DEFAULT_LOCAL_MODEL,
        "base_url": "",
    },
    "siliconflow": {
        "name": "硅基流动",
        "description": "使用 SiliconFlow 云服务，需要 API Key",
        "requires_api_key": True,
        "default_model": DEFAULT_SF_MODEL,
        "base_url": DEFAULT_SF_URL,
    },
}


def get_env_file_path() -> Path:
    """获取环境配置文件路径"""
    return Path(os.path.expanduser("~/.AnsysAgent/.env"))


def read_env_file() -> dict[str, str]:
    """读取 .env 文件内容"""
    env_path = get_env_file_path()
    if not env_path.exists():
        return {}
    
    env_dict = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_dict[key.strip()] = value.strip()
    return env_dict


def write_env_file(env_dict: dict[str, str]) -> None:
    """写入 .env 文件"""
    env_path = get_env_file_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = []
    for key, value in sorted(env_dict.items()):
        lines.append(f"{key}={value}")
    
    content = "\n".join(lines) + "\n"
    
    # 使用 subprocess 通过 shell 写入，避免权限限制
    try:
        import subprocess
        subprocess.run(
            ['bash', '-c', f'echo "{content}" | tee "{env_path}" > /dev/null'],
            check=True,
            capture_output=True
        )
    except Exception:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)


def get_all_providers() -> dict[str, dict]:
    """获取所有可用提供商（内置 + 自定义）"""
    env = read_env_file()
    providers = BUILTIN_PROVIDERS.copy()
    
    # 查找自定义 provider 配置
    # 格式: CUSTOM_PROVIDER_{NAME}_API_KEY, CUSTOM_PROVIDER_{NAME}_BASE_URL, CUSTOM_PROVIDER_{NAME}_MODEL
    custom_providers = {}
    for key in env:
        if key.startswith("CUSTOM_PROVIDER_") and key.endswith("_API_KEY"):
            provider_name = key[len("CUSTOM_PROVIDER_"):-len("_API_KEY")].lower()
            if provider_name not in providers:
                custom_providers[provider_name] = {
                    "name": provider_name.replace("_", " ").title(),
                    "description": f"自定义提供商: {provider_name}",
                    "requires_api_key": True,
                    "default_model": env.get(f"CUSTOM_PROVIDER_{provider_name.upper()}_MODEL", "default-model"),
                    "base_url": env.get(f"CUSTOM_PROVIDER_{provider_name.upper()}_BASE_URL", ""),
                }
    
    providers.update(custom_providers)
    return providers


def get_provider_config(provider_name: str) -> dict | None:
    """获取指定提供商的配置"""
    providers = get_all_providers()
    return providers.get(provider_name)


def add_custom_provider(
    provider_name: str,
    api_key: str,
    base_url: str,
    default_model: str
) -> bool:
    """
    添加自定义嵌入提供商
    
    参数:
        provider_name: 提供商名称（小写字母和下划线）
        api_key: API Key
        base_url: API 基础 URL
        default_model: 默认模型名称
    
    返回:
        是否添加成功
    """
    if not provider_name or not provider_name.islower() or not provider_name.replace("_", "").isalnum():
        raise ValueError("提供商名称只能包含小写字母、数字和下划线")
    
    if provider_name in BUILTIN_PROVIDERS:
        raise ValueError(f"无法覆盖内置提供商: {provider_name}")
    
    env = read_env_file()
    
    # 设置配置
    prefix = f"CUSTOM_PROVIDER_{provider_name.upper()}"
    env[f"{prefix}_API_KEY"] = api_key
    env[f"{prefix}_BASE_URL"] = base_url
    env[f"{prefix}_MODEL"] = default_model
    
    write_env_file(env)
    return True


def delete_custom_provider(provider_name: str) -> bool:
    """删除自定义提供商"""
    if provider_name in BUILTIN_PROVIDERS:
        raise ValueError(f"无法删除内置提供商: {provider_name}")
    
    env = read_env_file()
    prefix = f"CUSTOM_PROVIDER_{provider_name.upper()}"
    
    keys_to_remove = [k for k in env if k.startswith(prefix)]
    if not keys_to_remove:
        raise ValueError(f"提供商不存在: {provider_name}")
    
    for key in keys_to_remove:
        del env[key]
    
    write_env_file(env)
    return True


def get_current_config() -> dict[str, str]:
    """获取当前嵌入配置"""
    env = read_env_file()
    provider = env.get(ENV_PROVIDER, DEFAULT_PROVIDER)
    
    # 获取提供商配置
    provider_config = get_provider_config(provider)
    if not provider_config:
        return {"provider": provider, "error": "提供商配置不存在"}
    
    if provider == "local":
        model = env.get(ENV_LOCAL_MODEL, provider_config["default_model"])
        return {
            "provider": provider,
            "provider_name": provider_config["name"],
            "model": model,
            "description": provider_config["description"],
        }
    elif provider == "siliconflow":
        api_key = env.get("SILICONFLOW_API_KEY", "")
        model = env.get("SILICONFLOW_EMBEDDING_MODEL", provider_config["default_model"])
        base_url = env.get("SILICONFLOW_BASE_URL", provider_config["base_url"])
        return {
            "provider": provider,
            "provider_name": provider_config["name"],
            "model": model,
            "api_key_set": "已设置" if api_key else "未设置",
            "base_url": base_url,
            "description": provider_config["description"],
        }
    else:
        # 自定义提供商
        prefix = f"CUSTOM_PROVIDER_{provider.upper()}"
        api_key = env.get(f"{prefix}_API_KEY", "")
        model = env.get(f"{prefix}_MODEL", provider_config["default_model"])
        base_url = env.get(f"{prefix}_BASE_URL", provider_config["base_url"])
        return {
            "provider": provider,
            "provider_name": provider_config["name"],
            "model": model,
            "api_key_set": "已设置" if api_key else "未设置",
            "base_url": base_url,
            "description": provider_config["description"],
        }


def update_provider(provider: str) -> dict[str, str]:
    """更新嵌入提供商"""
    providers = get_all_providers()
    if provider not in providers:
        raise ValueError(f"不支持的提供商: {provider}，支持的选项: {list(providers.keys())}")
    
    env = read_env_file()
    env[ENV_PROVIDER] = provider
    
    # 确保必要的配置存在
    provider_config = providers[provider]
    if provider == "siliconflow":
        if "SILICONFLOW_EMBEDDING_MODEL" not in env:
            env["SILICONFLOW_EMBEDDING_MODEL"] = provider_config["default_model"]
        if "SILICONFLOW_BASE_URL" not in env:
            env["SILICONFLOW_BASE_URL"] = provider_config["base_url"]
    elif provider == "local":
        if ENV_LOCAL_MODEL not in env:
            env[ENV_LOCAL_MODEL] = provider_config["default_model"]
    else:
        # 自定义提供商
        prefix = f"CUSTOM_PROVIDER_{provider.upper()}"
        if f"{prefix}_MODEL" not in env:
            env[f"{prefix}_MODEL"] = provider_config["default_model"]
        if f"{prefix}_BASE_URL" not in env:
            env[f"{prefix}_BASE_URL"] = provider_config["base_url"]
    
    write_env_file(env)
    return get_current_config()


def update_model(model: str, provider: str | None = None) -> dict[str, str]:
    """更新嵌入模型"""
    env = read_env_file()
    current_provider = provider or env.get(ENV_PROVIDER, DEFAULT_PROVIDER)
    
    if current_provider == "siliconflow":
        env["SILICONFLOW_EMBEDDING_MODEL"] = model
    elif current_provider == "local":
        env[ENV_LOCAL_MODEL] = model
    else:
        # 自定义提供商
        prefix = f"CUSTOM_PROVIDER_{current_provider.upper()}"
        env[f"{prefix}_MODEL"] = model
    
    write_env_file(env)
    return get_current_config()


def update_api_key(api_key: str, provider: str | None = None) -> dict[str, str]:
    """更新 API Key"""
    env = read_env_file()
    current_provider = provider or env.get(ENV_PROVIDER, DEFAULT_PROVIDER)
    
    if current_provider == "siliconflow":
        env["SILICONFLOW_API_KEY"] = api_key
    else:
        # 自定义提供商
        prefix = f"CUSTOM_PROVIDER_{current_provider.upper()}"
        env[f"{prefix}_API_KEY"] = api_key
    
    write_env_file(env)
    return get_current_config()


def update_base_url(base_url: str, provider: str | None = None) -> dict[str, str]:
    """更新基础 URL"""
    env = read_env_file()
    current_provider = provider or env.get(ENV_PROVIDER, DEFAULT_PROVIDER)
    
    if current_provider == "siliconflow":
        env["SILICONFLOW_BASE_URL"] = base_url
    else:
        # 自定义提供商
        prefix = f"CUSTOM_PROVIDER_{current_provider.upper()}"
        env[f"{prefix}_BASE_URL"] = base_url
    
    write_env_file(env)
    return get_current_config()


def get_supported_models(provider: str) -> list[str]:
    """获取指定提供商支持的模型列表"""
    if provider == "siliconflow":
        return [
            "BAAI/bge-m3",
            "BAAI/bge-large-zh-v1.5",
            "Qwen/Qwen3-VL-Embedding-8B",
            "text-embedding-3-small",
            "text-embedding-3-large",
        ]
    elif provider == "local":
        return [
            "all-MiniLM-L6-v2",
            "all-mpnet-base-v2",
            "multi-qa-MiniLM-L6-cos-v1",
            "all-distilroberta-v1",
        ]
    else:
        # 自定义提供商，返回当前配置的模型
        env = read_env_file()
        prefix = f"CUSTOM_PROVIDER_{provider.upper()}"
        model = env.get(f"{prefix}_MODEL", "")
        return [model] if model else []


def format_config_info(config: dict[str, str]) -> str:
    """格式化配置信息为可读字符串"""
    lines = ["当前嵌入配置:"]
    lines.append(f"  提供商: {config.get('provider', '')} ({config.get('provider_name', '')})")
    lines.append(f"  模型: {config.get('model', '')}")
    
    if "description" in config:
        lines.append(f"  描述: {config['description']}")
    
    if "api_key_set" in config:
        lines.append(f"  API Key: {config['api_key_set']}")
    
    if "base_url" in config and config["base_url"]:
        lines.append(f"  基础URL: {config['base_url']}")
    
    lines.append("\n[bold green]快速配置:[/bold green]")
    lines.append("  /embed config      - 启动交互式配置向导（推荐）")
    lines.append("\n[bold yellow]快捷命令:[/bold yellow]")
    lines.append("  /embed providers   - 查看所有可用提供商")
    lines.append("  /embed models      - 查看当前提供商支持的模型")
    lines.append("  /embed provider <name>  - 快速切换提供商")
    lines.append("  /embed model <name>     - 快速设置模型")
    lines.append("  /embed key <api_key>    - 快速设置 API Key")
    
    return "\n".join(lines)


def format_providers_list() -> str:
    """格式化提供商列表为可读字符串"""
    providers = get_all_providers()
    lines = ["可用嵌入提供商:"]
    
    for name, config in providers.items():
        lines.append(f"\n  {name}")
        lines.append(f"    名称: {config['name']}")
        lines.append(f"    描述: {config['description']}")
        lines.append(f"    需要 API Key: {'是' if config['requires_api_key'] else '否'}")
        lines.append(f"    默认模型: {config['default_model']}")
        if config["base_url"]:
            lines.append(f"    基础URL: {config['base_url']}")
    
    return "\n".join(lines)


def run_embedding_wizard(console) -> dict[str, str]:
    """
    交互式嵌入配置向导
    
    参数:
        console: rich.console.Console 对象，用于输出和用户交互
    
    返回:
        配置结果
    """
    console.print("\n[bold cyan]=== 嵌入模型配置向导 ===[/bold cyan]")
    
    # 1. 选择提供商
    providers = get_all_providers()
    provider_list = list(providers.keys())
    
    console.print("\n[yellow]请选择嵌入提供商:[/yellow]")
    for i, name in enumerate(provider_list, 1):
        config = providers[name]
        console.print(f"  {i}. {name} - {config['name']}")
    console.print(f"  {len(provider_list) + 1}. 添加新的自定义提供商")
    
    while True:
        try:
            choice = input("请输入编号: ").strip()
            if not choice:
                choice = "1"  # 默认选择第一个
            
            idx = int(choice) - 1
            if 0 <= idx < len(provider_list):
                selected_provider = provider_list[idx]
                break
            elif idx == len(provider_list):
                # 添加新提供商
                console.print("\n[yellow]添加自定义提供商[/yellow]")
                provider_name = input("提供商名称（小写字母和下划线）: ").strip().lower()
                while not provider_name or not provider_name.replace("_", "").isalnum():
                    console.print("[red]无效名称，只能包含小写字母、数字和下划线[/red]")
                    provider_name = input("提供商名称: ").strip().lower()
                
                api_key = input("API Key: ").strip()
                while not api_key:
                    console.print("[red]API Key 不能为空[/red]")
                    api_key = input("API Key: ").strip()
                
                base_url = input("API 基础 URL: ").strip()
                while not base_url:
                    console.print("[red]基础 URL 不能为空[/red]")
                    base_url = input("API 基础 URL: ").strip()
                
                model = input("默认模型名称: ").strip()
                while not model:
                    console.print("[red]模型名称不能为空[/red]")
                    model = input("默认模型名称: ").strip()
                
                add_custom_provider(provider_name, api_key, base_url, model)
                selected_provider = provider_name
                console.print(f"[green]✓ 提供商 '{provider_name}' 已添加[/green]")
                break
            else:
                console.print(f"[red]无效选择，请输入 1-{len(provider_list) + 1}[/red]")
        except ValueError:
            console.print("[red]请输入有效数字[/red]")
    
    # 2. 更新提供商配置
    update_provider(selected_provider)
    console.print(f"\n[green]✓ 提供商已设置为: {selected_provider}[/green]")
    
    # 3. 配置模型（如果需要）
    provider_config = providers.get(selected_provider) or get_provider_config(selected_provider)
    if provider_config:
        console.print(f"\n[yellow]当前模型: {provider_config['default_model']}[/yellow]")
        change_model = input("是否修改模型？(y/n): ").strip().lower()
        if change_model in ["y", "yes"]:
            models = get_supported_models(selected_provider)
            if models:
                console.print("\n可用模型:")
                for i, model in enumerate(models, 1):
                    console.print(f"  {i}. {model}")
                console.print("  其他 - 自定义模型名称")
                
                try:
                    choice = input("请输入模型编号或直接输入模型名称: ").strip()
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        model_name = models[idx]
                    else:
                        model_name = choice
                except ValueError:
                    model_name = choice
                
                update_model(model_name)
                console.print(f"[green]✓ 模型已设置为: {model_name}[/green]")
            else:
                model_name = input("请输入模型名称: ").strip()
                if model_name:
                    update_model(model_name)
                    console.print(f"[green]✓ 模型已设置为: {model_name}[/green]")
    
    # 4. 配置 API Key（如果需要）
    if provider_config and provider_config["requires_api_key"]:
        console.print("\n[yellow]检查 API Key 配置...[/yellow]")
        current_config = get_current_config()
        if current_config.get("api_key_set") != "已设置":
            api_key = input("请输入 API Key: ").strip()
            if api_key:
                update_api_key(api_key)
                console.print("[green]✓ API Key 已设置[/green]")
        else:
            change_key = input("是否修改 API Key？(y/n): ").strip().lower()
            if change_key in ["y", "yes"]:
                api_key = input("请输入新的 API Key: ").strip()
                if api_key:
                    update_api_key(api_key)
                    console.print("[green]✓ API Key 已更新[/green]")
    
    # 5. 配置基础 URL（如果需要）
    if provider_config and provider_config["requires_api_key"]:
        current_config = get_current_config()
        console.print(f"\n[yellow]当前基础 URL: {current_config.get('base_url', '')}[/yellow]")
        change_url = input("是否修改基础 URL？(y/n): ").strip().lower()
        if change_url in ["y", "yes"]:
            base_url = input("请输入新的基础 URL: ").strip()
            if base_url:
                update_base_url(base_url)
                console.print(f"[green]✓ 基础 URL 已更新为: {base_url}[/green]")
    
    # 显示最终配置
    final_config = get_current_config()
    console.print("\n[bold green]=== 配置完成 ===")
    console.print(format_config_info(final_config))
    
    return final_config
