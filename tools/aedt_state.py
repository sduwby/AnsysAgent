"""
AEDT 状态管理模块。

提供线程本地存储的 AEDT 实例管理，避免全局状态导致的并发冲突。
支持 Maxwell, Icepak, Motor-CAD, MAPDL, Mechanical 等多种 AEDT 应用。
"""

from __future__ import annotations
import logging
import threading
from typing import Any, Optional
from contextlib import contextmanager

_log = logging.getLogger(__name__)


class AEDTStateManager:
    """管理线程本地 AEDT 实例的单一状态管理器。"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._states: dict[str, threading.local] = {}
    
    def get_local_state(self, app_type: str) -> threading.local:
        """获取或创建指定应用类型的线程本地状态。"""
        with self._lock:
            if app_type not in self._states:
                self._states[app_type] = threading.local()
            return self._states[app_type]
    
    def set_app(self, app_type: str, app: Any) -> None:
        """设置当前线程的 AEDT 实例。"""
        local_state = self.get_local_state(app_type)
        local_state.app = app
    
    def get_app(self, app_type: str) -> Optional[Any]:
        """获取当前线程的 AEDT 实例。"""
        local_state = self.get_local_state(app_type)
        return getattr(local_state, "app", None)
    
    def clear_app(self, app_type: str) -> None:
        """清除当前线程的 AEDT 实例并释放资源。"""
        local_state = self.get_local_state(app_type)
        if hasattr(local_state, "app") and local_state.app is not None:
            app = local_state.app
            try:
                self._close_app(app)
                _log.info("[%s] 资源已释放", app_type)
            except Exception as e:
                _log.error("[%s] 资源释放失败：%s", app_type, e, exc_info=True)
                raise
            finally:
                del local_state.app
    
    @staticmethod
    def _close_app(app: Any) -> None:
        """关闭 AEDT 实例并释放资源。"""
        if hasattr(app, "desktop") and hasattr(app.desktop, "CloseDesktop"):
            try:
                app.desktop.CloseDesktop()
            except Exception as e:
                _log.warning("CloseDesktop 失败：%s", e)
        if hasattr(app, "close"):
            try:
                app.close()
            except Exception as e:
                _log.warning("close 方法失败：%s", e)


# 全局状态管理器单例
_manager = None
_manager_lock = threading.Lock()


def get_manager() -> AEDTStateManager:
    """获取或创建全局状态管理器单例。"""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = AEDTStateManager()
        return _manager


# 便捷函数 - 为每个应用类型创建包装器

# Maxwell
_maxwell_manager = get_manager()


def get_maxwell_app() -> Optional[Any]:
    """获取当前线程的 Maxwell 实例。"""
    return _maxwell_manager.get_app("maxwell")


def set_maxwell_app(app: Any) -> None:
    """设置当前线程的 Maxwell 实例。"""
    _maxwell_manager.set_app("maxwell", app)


def clear_maxwell_app() -> None:
    """清除当前线程的 Maxwell 实例并释放资源。"""
    _maxwell_manager.clear_app("maxwell")


# Icepak
_icepak_manager = get_manager()


def get_icepak_app() -> Optional[Any]:
    """获取当前线程的 Icepak 实例。"""
    return _icepak_manager.get_app("icepak")


def set_icepak_app(app: Any) -> None:
    """设置当前线程的 Icepak 实例。"""
    _icepak_manager.set_app("icepak", app)


def clear_icepak_app() -> None:
    """清除当前线程的 Icepak 实例并释放资源。"""
    _icepak_manager.clear_app("icepak")


# Motor-CAD
_mcad_manager = get_manager()


def get_mcad_app() -> Optional[Any]:
    """获取当前线程的 Motor-CAD 实例。"""
    return _mcad_manager.get_app("motorcad")


def set_mcad_app(app: Any) -> None:
    """设置当前线程的 Motor-CAD 实例。"""
    _mcad_manager.set_app("motorcad", app)


def clear_mcad_app() -> None:
    """清除当前线程的 Motor-CAD 实例并释放资源。"""
    _mcad_manager.clear_app("motorcad")


# MAPDL
_mapdl_manager = get_manager()


def get_mapdl_app() -> Optional[Any]:
    """获取当前线程的 MAPDL 实例。"""
    return _mapdl_manager.get_app("mapdl")


def set_mapdl_app(app: Any) -> None:
    """设置当前线程的 MAPDL 实例。"""
    _mapdl_manager.set_app("mapdl", app)


def clear_mapdl_app() -> None:
    """清除当前线程的 MAPDL 实例并释放资源。"""
    _mapdl_manager.clear_app("mapdl")


# Mechanical
_mech_manager = get_manager()


def get_mech_app() -> Optional[Any]:
    """获取当前线程的 Mechanical 实例。"""
    return _mech_manager.get_app("mech")


def set_mech_app(app: Any) -> None:
    """设置当前线程的 Mechanical 实例。"""
    _mech_manager.set_app("mech", app)


def clear_mech_app() -> None:
    """清除当前线程的 Mechanical 实例并释放资源。"""
    _mech_manager.clear_app("mech")


# Circuit
_circuit_manager = get_manager()


def get_circuit_app() -> Optional[Any]:
    """获取当前线程的 Circuit 实例。"""
    return _circuit_manager.get_app("circuit")


def set_circuit_app(app: Any) -> None:
    """设置当前线程的 Circuit 实例。"""
    _circuit_manager.set_app("circuit", app)


def clear_circuit_app() -> None:
    """清除当前线程的 Circuit 实例并释放资源。"""
    _circuit_manager.clear_app("circuit")


# RMXprt
_rmxprt_manager = get_manager()


def get_rmxprt_app() -> Optional[Any]:
    """获取当前线程的 RMXprt 实例。"""
    return _rmxprt_manager.get_app("rmxprt")


def set_rmxprt_app(app: Any) -> None:
    """设置当前线程的 RMXprt 实例。"""
    _rmxprt_manager.set_app("rmxprt", app)


def clear_rmxprt_app() -> None:
    """清除当前线程的 RMXprt 实例并释放资源。"""
    _rmxprt_manager.clear_app("rmxprt")


# NVH
# 注意：nvh_mech_manager 和 nvh_mapdl_manager 是同一个实例（单例模式）
# NVH Mechanical 和 NVH MAPDL 共享同一个状态管理器，因为它们是同一线程的
# 不同应用类型由内部的 app_type 区分
_nvh_mech_manager = get_manager()
_nvh_mapdl_manager = _nvh_mech_manager  # 明确声明为同一实例


def get_nvh_mech_app() -> Optional[Any]:
    """获取当前线程的 NVH Mechanical 实例。"""
    return _nvh_mech_manager.get_app("nvh_mech")


def set_nvh_mech_app(app: Any) -> None:
    """设置当前线程的 NVH Mechanical 实例。"""
    _nvh_mech_manager.set_app("nvh_mech", app)


def clear_nvh_mech_app() -> None:
    """清除当前线程的 NVH Mechanical 实例并释放资源。"""
    _nvh_mech_manager.clear_app("nvh_mech")


def get_nvh_mapdl_app() -> Optional[Any]:
    """获取当前线程的 NVH MAPDL 实例。"""
    return _nvh_mapdl_manager.get_app("nvh_mapdl")


def set_nvh_mapdl_app(app: Any) -> None:
    """设置当前线程的 NVH MAPDL 实例。"""
    _nvh_mapdl_manager.set_app("nvh_mapdl", app)


def clear_nvh_mapdl_app() -> None:
    """清除当前线程的 NVH MAPDL 实例并释放资源。"""
    _nvh_mapdl_manager.clear_app("nvh_mapdl")


# EV Powertrain
_ev_circuit_manager = get_manager()


def get_ev_circuit_app() -> Optional[Any]:
    """获取当前线程的 EV Circuit 实例。"""
    return _ev_circuit_manager.get_app("ev_circuit")


def set_ev_circuit_app(app: Any) -> None:
    """设置当前线程的 EV Circuit 实例。"""
    _ev_circuit_manager.set_app("ev_circuit", app)


def clear_ev_circuit_app() -> None:
    """清除当前线程的 EV Circuit 实例并释放资源。"""
    _ev_circuit_manager.clear_app("ev_circuit")


@contextmanager
def aedt_session(app_type: str):
    """
    上下文管理器：自动管理 AEDT 连接生命周期。
    
    用法:
        with aedt_session("maxwell"):
            app = get_maxwell_app()
            # 使用 app
        # 自动关闭
        
    参数:
        app_type: 应用类型，支持 "maxwell", "icepak", "motorcad", "mapdl", 
                 "mech", "circuit", "rmxprt", "nvh_mech", "nvh_mapdl", "ev_circuit"
    
    异常:
        ValueError: 当 app_type 不支持时抛出
    """
    managers = {
        "maxwell": (_maxwell_manager, set_maxwell_app, clear_maxwell_app),
        "icepak": (_icepak_manager, set_icepak_app, clear_icepak_app),
        "motorcad": (_mcad_manager, set_mcad_app, clear_mcad_app),
        "mapdl": (_mapdl_manager, set_mapdl_app, clear_mapdl_app),
        "mech": (_mech_manager, set_mech_app, clear_mech_app),
        "circuit": (_circuit_manager, set_circuit_app, clear_circuit_app),
        "rmxprt": (_rmxprt_manager, set_rmxprt_app, clear_rmxprt_app),
        "nvh_mech": (_nvh_mech_manager, set_nvh_mech_app, clear_nvh_mech_app),
        "nvh_mapdl": (_nvh_mapdl_manager, set_nvh_mapdl_app, clear_nvh_mapdl_app),
        "ev_circuit": (_ev_circuit_manager, set_ev_circuit_app, clear_ev_circuit_app),
    }
    
    if app_type not in managers:
        raise ValueError(f"未知的应用类型：{app_type}，支持的值：{list(managers.keys())}")
    
    manager, setter, closer = managers[app_type]
    setter(None)  # 清除之前的状态
    try:
        yield
    finally:
        closer()  # 确保清理