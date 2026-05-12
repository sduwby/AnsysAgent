"""
云平台集成工具：支持云HPC资源调度和分布式仿真。

支持的云平台：
- AWS Batch / EC2
- Azure Batch / VM
- 阿里云 ECS / Batch

功能特性：
- 云资源管理（启动/停止实例）
- 分布式仿真调度
- 结果云端存储
- 成本估算和监控

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

# 云平台配置
_CLOUD_PROVIDERS = {
    "aws": {
        "name": "Amazon Web Services",
        "description": "AWS云平台",
        "regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-east-1", "ap-southeast-1"],
    },
    "azure": {
        "name": "Microsoft Azure",
        "description": "Azure云平台",
        "regions": ["eastus", "westus", "northeurope", "southeastasia", "eastasia"],
    },
    "aliyun": {
        "name": "阿里云",
        "description": "阿里云平台",
        "regions": ["cn-hangzhou", "cn-beijing", "cn-shanghai", "ap-southeast-1"],
    },
}

# 全局云客户端
_cloud_clients = {}


def _get_cloud_client(provider: str):
    """获取云客户端（延迟初始化）"""
    if provider not in _cloud_clients:
        _cloud_clients[provider] = _init_cloud_client(provider)
    return _cloud_clients[provider]


def _init_cloud_client(provider: str):
    """初始化云客户端"""
    try:
        if provider == "aws":
            try:
                import boto3
                return boto3.Session()
            except ImportError:
                return {"type": "aws", "mock": True}
        elif provider == "azure":
            try:
                from azure.identity import DefaultAzureCredential
                from azure.mgmt.compute import ComputeManagementClient
                return {"type": "azure", "client": ComputeManagementClient(DefaultAzureCredential(), ""), "mock": False}
            except ImportError:
                return {"type": "azure", "mock": True}
        elif provider == "aliyun":
            try:
                from aliyunsdkcore.client import AcsClient
                return {"type": "aliyun", "client": AcsClient(), "mock": True}
            except ImportError:
                return {"type": "aliyun", "mock": True}
        else:
            return {"type": provider, "mock": True}
    except Exception:
        return {"type": provider, "mock": True}


# ---------------------------------------------------------------------------
# 工具：list_cloud_providers - 列出支持的云平台
# ---------------------------------------------------------------------------

def list_cloud_providers() -> dict:
    """
    列出所有支持的云平台。
    """
    providers = []
    for provider_id, info in _CLOUD_PROVIDERS.items():
        providers.append({
            "provider": provider_id,
            "name": info["name"],
            "description": info["description"],
            "regions": info["regions"],
        })
    
    return _ok({
        "count": len(providers),
        "providers": providers,
        "message": f"支持 {len(providers)} 个云平台",
    })


# ---------------------------------------------------------------------------
# 工具：configure_cloud - 配置云平台
# ---------------------------------------------------------------------------

def configure_cloud(
    provider: str,
    region: str,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    config_file: Optional[str] = None,
) -> dict:
    """
    配置云平台访问凭证。

    Args:
        provider: 云平台标识（aws/azure/aliyun）
        region: 区域
        access_key: 访问密钥（可选，若已配置环境变量）
        secret_key: 密钥（可选）
        config_file: 配置文件路径（可选）
    """
    try:
        if provider not in _CLOUD_PROVIDERS:
            return _err(f"不支持的云平台: {provider}")
        
        if region not in _CLOUD_PROVIDERS[provider]["regions"]:
            return _err(f"无效的区域: {region}")
        
        # 保存配置到环境变量或配置文件
        config = {
            "provider": provider,
            "region": region,
            "access_key": access_key,
            "secret_key": secret_key,
        }
        
        from agent.paths import get_ansys_data_dir
        cloud_config_dir = Path(get_ansys_data_dir()) / "cloud"
        cloud_config_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = cloud_config_dir / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        # 设置环境变量
        if access_key:
            os.environ[f"{provider.upper()}_ACCESS_KEY_ID"] = access_key
        if secret_key:
            os.environ[f"{provider.upper()}_SECRET_ACCESS_KEY"] = secret_key
        os.environ["ANSYS_AGENT_CLOUD_PROVIDER"] = provider
        os.environ["ANSYS_AGENT_CLOUD_REGION"] = region
        
        # 初始化客户端
        _cloud_clients[provider] = _init_cloud_client(provider)
        
        return _ok(ok_message(
            f"云平台配置完成: {_CLOUD_PROVIDERS[provider]['name']} ({region})",
            provider=provider,
            region=region,
            config_path=str(config_path),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_cloud_status - 获取云平台状态
# ---------------------------------------------------------------------------

def get_cloud_status(provider: str) -> dict:
    """
    获取云平台连接状态。

    Args:
        provider: 云平台标识
    """
    try:
        client = _get_cloud_client(provider)
        
        if client.get("mock", False):
            return _ok({
                "provider": provider,
                "connected": False,
                "status": "未安装SDK，使用模拟模式",
                "message": f"{_CLOUD_PROVIDERS[provider]['name']} - 模拟模式",
            })
        
        return _ok({
            "provider": provider,
            "connected": True,
            "status": "已连接",
            "message": f"{_CLOUD_PROVIDERS[provider]['name']} - 已连接",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：launch_hpc_instance - 启动HPC实例
# ---------------------------------------------------------------------------

def launch_hpc_instance(
    provider: str,
    instance_type: str = "c5.4xlarge",
    region: Optional[str] = None,
    instance_count: int = 1,
    spot: bool = False,
) -> dict:
    """
    启动云HPC实例。

    Args:
        provider: 云平台标识
        instance_type: 实例类型
        region: 区域（可选，使用已配置的区域）
        instance_count: 实例数量
        spot: 是否使用竞价实例
    """
    try:
        client = _get_cloud_client(provider)
        
        if client.get("mock", False):
            # 模拟启动实例
            instances = []
            for i in range(instance_count):
                instances.append({
                    "id": f"mock-instance-{i:04d}",
                    "type": instance_type,
                    "status": "running",
                    "public_ip": f"10.0.0.{100 + i}",
                    "private_ip": f"192.168.1.{100 + i}",
                })
            
            return _ok({
                "provider": provider,
                "instance_type": instance_type,
                "count": instance_count,
                "spot": spot,
                "instances": instances,
                "message": f"已启动 {instance_count} 个HPC实例（模拟模式）",
            })
        
        # 实际云平台调用（示例）
        if provider == "aws":
            ec2 = client.resource('ec2', region_name=region)
            instances = ec2.create_instances(
                ImageId='ami-0abc1234',
                MinCount=instance_count,
                MaxCount=instance_count,
                InstanceType=instance_type,
                InstanceMarketOptions={'MarketType': 'spot'} if spot else None,
            )
            instance_info = []
            for inst in instances:
                inst.wait_until_running()
                inst.load()
                instance_info.append({
                    "id": inst.id,
                    "type": inst.instance_type,
                    "status": inst.state['Name'],
                    "public_ip": inst.public_ip_address,
                    "private_ip": inst.private_ip_address,
                })
            
            return _ok({
                "provider": provider,
                "instance_type": instance_type,
                "count": instance_count,
                "spot": spot,
                "instances": instance_info,
                "message": f"已启动 {instance_count} 个HPC实例",
            })
        
        return _err(f"未实现 {provider} 的实例启动")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：list_hpc_instances - 列出HPC实例
# ---------------------------------------------------------------------------

def list_hpc_instances(provider: str, region: Optional[str] = None) -> dict:
    """
    列出云平台上的HPC实例。

    Args:
        provider: 云平台标识
        region: 区域
    """
    try:
        client = _get_cloud_client(provider)
        
        if client.get("mock", False):
            return _ok({
                "provider": provider,
                "instances": [
                    {"id": "mock-instance-0001", "type": "c5.4xlarge", "status": "running"},
                    {"id": "mock-instance-0002", "type": "c5.9xlarge", "status": "stopped"},
                ],
                "message": "列出实例（模拟模式）",
            })
        
        if provider == "aws":
            ec2 = client.resource('ec2', region_name=region)
            instances = []
            for inst in ec2.instances.all():
                instances.append({
                    "id": inst.id,
                    "type": inst.instance_type,
                    "status": inst.state['Name'],
                    "public_ip": inst.public_ip_address,
                    "launch_time": inst.launch_time.isoformat(),
                })
            return _ok({"provider": provider, "instances": instances})
        
        return _err(f"未实现 {provider} 的实例列表")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：terminate_hpc_instances - 终止HPC实例
# ---------------------------------------------------------------------------

def terminate_hpc_instances(provider: str, instance_ids: list[str]) -> dict:
    """
    终止指定的HPC实例。

    Args:
        provider: 云平台标识
        instance_ids: 实例ID列表
    """
    try:
        client = _get_cloud_client(provider)
        
        if client.get("mock", False):
            return _ok({
                "provider": provider,
                "terminated": instance_ids,
                "message": f"已终止 {len(instance_ids)} 个实例（模拟模式）",
            })
        
        if provider == "aws":
            ec2 = client.resource('ec2')
            ec2.instances.filter(InstanceIds=instance_ids).terminate()
            return _ok({"provider": provider, "terminated": instance_ids})
        
        return _err(f"未实现 {provider} 的实例终止")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：submit_cloud_job - 提交云批处理作业
# ---------------------------------------------------------------------------

def submit_cloud_job(
    provider: str,
    job_name: str,
    job_definition: str,
    queue: str = "default",
    array_size: int = 1,
) -> dict:
    """
    提交批处理作业到云平台。

    Args:
        provider: 云平台标识
        job_name: 作业名称
        job_definition: 作业定义（容器镜像或脚本路径）
        queue: 队列名称
        array_size: 数组作业大小
    """
    try:
        client = _get_cloud_client(provider)
        
        if client.get("mock", False):
            job_id = f"mock-job-{int(time.time())}"
            return _ok({
                "provider": provider,
                "job_id": job_id,
                "job_name": job_name,
                "queue": queue,
                "status": "SUBMITTED",
                "message": f"作业已提交: {job_id}（模拟模式）",
            })
        
        if provider == "aws":
            batch = client.client('batch')
            response = batch.submit_job(
                jobName=job_name,
                jobQueue=queue,
                jobDefinition=job_definition,
                arrayProperties={'size': array_size} if array_size > 1 else {},
            )
            return _ok({
                "provider": provider,
                "job_id": response['jobId'],
                "job_name": job_name,
                "queue": queue,
                "status": "SUBMITTED",
            })
        
        return _err(f"未实现 {provider} 的作业提交")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_cloud_job_status - 获取云作业状态
# ---------------------------------------------------------------------------

def get_cloud_job_status(provider: str, job_id: str) -> dict:
    """
    获取云批处理作业状态。

    Args:
        provider: 云平台标识
        job_id: 作业ID
    """
    try:
        client = _get_cloud_client(provider)
        
        if client.get("mock", False):
            return _ok({
                "provider": provider,
                "job_id": job_id,
                "status": "RUNNING",
                "progress": 45,
                "message": "获取作业状态（模拟模式）",
            })
        
        if provider == "aws":
            batch = client.client('batch')
            response = batch.describe_jobs(jobs=[job_id])
            job = response['jobs'][0]
            return _ok({
                "provider": provider,
                "job_id": job_id,
                "status": job['status'],
                "status_reason": job.get('statusReason'),
            })
        
        return _err(f"未实现 {provider} 的作业状态查询")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：upload_to_cloud_storage - 上传文件到云存储
# ---------------------------------------------------------------------------

def upload_to_cloud_storage(
    provider: str,
    local_path: str,
    bucket_name: str,
    remote_path: Optional[str] = None,
) -> dict:
    """
    上传文件到云存储。

    Args:
        provider: 云平台标识
        local_path: 本地文件路径
        bucket_name: 存储桶名称
        remote_path: 远程路径（可选，默认使用本地文件名）
    """
    try:
        if not os.path.exists(local_path):
            return _err(f"文件不存在: {local_path}")
        
        client = _get_cloud_client(provider)
        
        if client.get("mock", False):
            remote_path = remote_path or os.path.basename(local_path)
            return _ok({
                "provider": provider,
                "bucket": bucket_name,
                "local_path": local_path,
                "remote_path": remote_path,
                "message": "文件上传成功（模拟模式）",
            })
        
        if provider == "aws":
            s3 = client.resource('s3')
            remote_path = remote_path or os.path.basename(local_path)
            s3.Bucket(bucket_name).upload_file(local_path, remote_path)
            return _ok({
                "provider": provider,
                "bucket": bucket_name,
                "local_path": local_path,
                "remote_path": remote_path,
            })
        
        return _err(f"未实现 {provider} 的文件上传")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：download_from_cloud_storage - 从云存储下载文件
# ---------------------------------------------------------------------------

def download_from_cloud_storage(
    provider: str,
    bucket_name: str,
    remote_path: str,
    local_path: Optional[str] = None,
) -> dict:
    """
    从云存储下载文件。

    Args:
        provider: 云平台标识
        bucket_name: 存储桶名称
        remote_path: 远程路径
        local_path: 本地路径（可选，默认使用远程文件名）
    """
    try:
        client = _get_cloud_client(provider)
        
        if client.get("mock", False):
            local_path = local_path or os.path.basename(remote_path)
            ensure_parent_dir(local_path)
            with open(local_path, 'w') as f:
                f.write("Mock cloud content")
            return _ok({
                "provider": provider,
                "bucket": bucket_name,
                "remote_path": remote_path,
                "local_path": local_path,
                "message": "文件下载成功（模拟模式）",
            })
        
        if provider == "aws":
            s3 = client.resource('s3')
            local_path = local_path or os.path.basename(remote_path)
            ensure_parent_dir(local_path)
            s3.Bucket(bucket_name).download_file(remote_path, local_path)
            return _ok({
                "provider": provider,
                "bucket": bucket_name,
                "remote_path": remote_path,
                "local_path": local_path,
            })
        
        return _err(f"未实现 {provider} 的文件下载")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：estimate_cloud_cost - 估算云资源成本
# ---------------------------------------------------------------------------

def estimate_cloud_cost(
    provider: str,
    instance_type: str,
    hours: float = 1.0,
    instance_count: int = 1,
    storage_gb: float = 100.0,
) -> dict:
    """
    估算云资源使用成本。

    Args:
        provider: 云平台标识
        instance_type: 实例类型
        hours: 使用时长（小时）
        instance_count: 实例数量
        storage_gb: 存储容量（GB）
    """
    try:
        # 简化的成本估算（实际应调用云平台定价API）
        price_table = {
            "aws": {
                "c5.large": 0.12,
                "c5.xlarge": 0.24,
                "c5.2xlarge": 0.48,
                "c5.4xlarge": 0.96,
                "c5.9xlarge": 2.16,
                "p3.2xlarge": 3.06,
                "p3.8xlarge": 12.24,
            },
            "azure": {
                "Standard_D4s_v3": 0.34,
                "Standard_D8s_v3": 0.68,
                "Standard_NC6": 1.10,
                "Standard_NC24": 4.40,
            },
            "aliyun": {
                "ecs.g6.large": 0.15,
                "ecs.g6.xlarge": 0.30,
                "ecs.g6.4xlarge": 1.20,
                "ecs.p3.8xlarge": 8.00,
            },
        }
        
        storage_price = {
            "aws": 0.023,   # S3标准存储
            "azure": 0.024, # Blob存储
            "aliyun": 0.02, # OSS标准存储
        }
        
        instance_price = price_table.get(provider, {}).get(instance_type, 0.5)
        storage_fee = storage_price.get(provider, 0.02) * storage_gb
        
        total_cost = (instance_price * instance_count * hours) + storage_fee
        
        return _ok({
            "provider": provider,
            "instance_type": instance_type,
            "instance_count": instance_count,
            "hours": hours,
            "storage_gb": storage_gb,
            "instance_cost": round(instance_price * instance_count * hours, 2),
            "storage_cost": round(storage_fee, 2),
            "total_cost": round(total_cost, 2),
            "currency": "USD",
            "message": f"估算成本: ${total_cost:.2f}",
        })
    except Exception as e:
        return _err(str(e))
