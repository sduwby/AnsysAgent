"""嵌入配置管理工具 - 支持对话中查看和修改嵌入配置"""

from __future__ import annotations

from rag.config_manager import (
    get_current_config,
    update_provider,
    update_model,
    update_api_key,
    update_base_url,
    get_supported_models,
    format_config_info,
    format_providers_list,
    add_custom_provider,
    delete_custom_provider,
    get_all_providers,
)


def manage_embedding_config(command: str = "", provider: str = "", model: str = "", api_key: str = "", base_url: str = "", custom_args: list = None) -> str:
    """
    管理嵌入配置的工具函数
    
    参数:
        command: 命令类型 (config/provider/model/key/url/models/providers/add/delete)
        provider: 提供商名称
        model: 模型名称
        api_key: API Key
        base_url: 基础 URL
        custom_args: 自定义参数列表（用于 add 命令）
    
    返回:
        配置信息或操作结果
    """
    if not command:
        return format_config_info(get_current_config())
    
    command = command.lower().strip()
    
    try:
        if command == "config":
            return format_config_info(get_current_config())
        
        elif command == "provider":
            if not provider:
                providers = get_all_providers()
                return f"请指定提供商，支持的选项: {list(providers.keys())}"
            new_config = update_provider(provider)
            return f"提供商已切换为 {provider}。\n\n新配置:\n{format_config_info(new_config)}"
        
        elif command == "model":
            if not model:
                current = get_current_config()
                models = get_supported_models(current.get("provider", ""))
                return f"请指定模型名称。当前提供商支持的模型:\n" + "\n".join(f"  - {m}" for m in models)
            new_config = update_model(model)
            return f"模型已更新为 {model}。\n\n新配置:\n{format_config_info(new_config)}"
        
        elif command == "key":
            if not api_key:
                return "请提供 API Key"
            new_config = update_api_key(api_key)
            return f"API Key 已设置。\n\n新配置:\n{format_config_info(new_config)}"
        
        elif command == "url":
            if not base_url:
                return "请提供 API 基础 URL"
            new_config = update_base_url(base_url)
            return f"基础 URL 已更新为 {base_url}。\n\n新配置:\n{format_config_info(new_config)}"
        
        elif command == "models":
            current = get_current_config()
            models = get_supported_models(current.get("provider", ""))
            return f"当前提供商 ({current.get('provider', '')}) 支持的模型:\n" + "\n".join(f"  - {m}" for m in models)
        
        elif command == "providers":
            return format_providers_list()
        
        elif command == "add":
            if not custom_args or len(custom_args) < 4:
                return "用法: /embed add <name> <api_key> <base_url> <model>\n\n示例:\n  /embed add openai sk-xxx... https://api.openai.com/v1 text-embedding-3-small"
            provider_name = custom_args[0]
            api_key_val = custom_args[1]
            base_url_val = custom_args[2]
            default_model = custom_args[3]
            
            add_custom_provider(provider_name, api_key_val, base_url_val, default_model)
            return f"自定义提供商 '{provider_name}' 已添加成功！\n\n可用提供商列表:\n{format_providers_list()}"
        
        elif command == "delete":
            if not provider:
                return "请指定要删除的提供商名称"
            delete_custom_provider(provider)
            return f"自定义提供商 '{provider}' 已删除成功！\n\n可用提供商列表:\n{format_providers_list()}"
        
        else:
            return f"未知命令: {command}。支持的命令: config, provider, model, key, url, models, providers, add, delete"
    
    except ValueError as e:
        return f"错误: {str(e)}"
    except Exception as e:
        return f"操作失败: {str(e)}"
