"""
项目管理工具：通过 PyAEDT 保存、打开、关闭 AEDT 项目，以及列出和复制设计。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import os

from tools.utils import _ok, _err, ensure_parent_dir, get_design_names, ok_message


def _app():
    """复用 maxwell_tools 中的全局 AEDT app 实例。"""
    from tools import maxwell_tools
    if maxwell_tools._aedt_app is None:
        raise RuntimeError("未连接到 AEDT，请先调用 connect_aedt。")
    return maxwell_tools._aedt_app

# ---------------------------------------------------------------------------
# 工具：save_project - 保存项目
# ---------------------------------------------------------------------------

def save_project(file_path: str = "") -> dict:
    """
    保存当前 AEDT 项目。

    Args:
        file_path: 另存路径（含 .aedt 扩展名），留空则原路径覆盖保存
    """
    try:
        app = _app()
        if file_path:
            if not file_path.endswith(".aedt"):
                file_path += ".aedt"
            ensure_parent_dir(file_path)
            app.save_project(file_name=file_path)
            return _ok(ok_message(f"项目已另存为: {file_path}", file_path=file_path))
        else:
            app.save_project()
            return _ok(ok_message(f"项目已保存: {app.project_file}", file_path=app.project_file))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：open_project - 打开项目
# ---------------------------------------------------------------------------

def open_project(file_path: str) -> dict:
    """
    在当前 AEDT 桌面会话中打开已有项目文件（.aedt）。
    打开后如需切换到该项目的设计，请重新调用 connect_aedt。

    Args:
        file_path: 项目 .aedt 文件绝对路径
    """
    try:
        if not os.path.exists(file_path):
            return _err(f"找不到文件: {file_path}")
        app = _app()
        # 通过 AEDT 桌面 COM 接口打开项目
        app.odesktop.OpenProject(file_path)
        project_name = os.path.splitext(os.path.basename(file_path))[0]
        return _ok(
            f"已在当前 AEDT 会话中打开项目 '{project_name}'。"
            "如需切换到该项目中的特定设计，请重新调用 connect_aedt，传入 project_path 和 design_name。"
        )
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：close_project - 关闭项目
# ---------------------------------------------------------------------------

def close_project(project_name: str = "", save_first: bool = True) -> dict:
    """
    关闭指定项目（或当前活动项目）。

    Args:
        project_name: 要关闭的项目名称，留空则关闭当前活动项目
        save_first: 关闭前是否先保存，默认 True
    """
    try:
        app = _app()
        name = project_name or app.project_name
        if save_first:
            app.save_project()
        app.close_project(name)
        return _ok(ok_message(f"已关闭项目: {name}", project_name=name))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：list_designs - 列出所有设计
# ---------------------------------------------------------------------------

def list_designs() -> dict:
    """
    列出当前项目中所有设计的名称。
    """
    try:
        app = _app()
        designs = get_design_names(app)
        return _ok({
            "project_name": app.project_name,
            "project_file": app.project_file,
            "active_design": app.design_name,
            "designs": designs,
            "count": len(designs),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：copy_design - 复制设计
# ---------------------------------------------------------------------------

def copy_design(source_design: str, new_name: str) -> dict:
    """
    在当前项目中复制一个设计，适用于多方案对比或参数研究。

    Args:
        source_design: 要复制的源设计名称
        new_name: 新设计名称（不能与已有设计重名）
    """
    try:
        app = _app()
        existing_designs = get_design_names(app)
        if source_design not in existing_designs:
            return _err(f"源设计不存在: {source_design}")
        if new_name in existing_designs:
            return _err(f"目标设计名已存在: {new_name}")

        # PyAEDT 通过 oproject COM 接口复制设计
        app.oproject.CopyDesign(source_design)
        app.oproject.PasteDesign(0)  # 粘贴为新设计
        designs_after = get_design_names(app)
        new_design_candidates = [d for d in designs_after if d not in existing_designs]
        if len(new_design_candidates) != 1:
            return _err(
                "复制设计后未能唯一识别新设计，请检查 AEDT 当前设计列表后手动重命名"
            )
        app.oproject.RenameDesign(new_design_candidates[0], new_name)
        return _ok(ok_message(
            f"设计 '{source_design}' 已复制为 '{new_name}'",
            source_design=source_design,
            new_name=new_name,
        ))
    except Exception as e:
        return _err(str(e))
