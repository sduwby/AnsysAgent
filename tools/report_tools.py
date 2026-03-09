"""
报告生成工具：自动整合仿真结果，生成 PDF/HTML 格式的电机仿真报告。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Any


def _ok(result: Any = None) -> dict:
    return {"success": True, "result": result}


def _err(msg: str) -> dict:
    return {"success": False, "error": msg}


# ---------------------------------------------------------------------------
# 工具：generate_report - 生成仿真报告
# ---------------------------------------------------------------------------

def generate_report(
    output_path: str,
    motor_name: str = "PMSM Motor",
    results: dict | None = None,
    format: str = "html",
) -> dict:
    """
    生成电机仿真报告（HTML 格式，可在浏览器查看）。

    Args:
        output_path: 报告输出路径（.html 或 .md）
        motor_name: 电机名称，显示在报告标题
        results: 仿真结果字典（由其他工具返回的结果汇总）
        format: 报告格式，"html" 或 "markdown"
    """
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results = results or {}

        if format == "html":
            content = _build_html_report(motor_name, now, results)
            if not output_path.endswith(".html"):
                output_path = output_path.rstrip(".") + ".html"
        else:
            content = _build_markdown_report(motor_name, now, results)
            if not output_path.endswith(".md"):
                output_path = output_path.rstrip(".") + ".md"

        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return _ok(f"报告已生成：{output_path}")
    except Exception as e:
        return _err(str(e))


def _build_html_report(motor_name: str, timestamp: str, results: dict) -> str:
    """构建 HTML 报告内容。"""
    # 提取常用结果
    torque = results.get("torque", {})
    losses = results.get("losses", {})
    back_emf = results.get("back_emf", {})
    thermal = results.get("thermal", {})
    optimization = results.get("optimization", {})

    rows = []

    if torque:
        avg = torque.get("avg_torque_Nm", "N/A")
        rows.append(f"<tr><td>平均转矩</td><td>{avg} Nm</td></tr>")

    if losses:
        core = losses.get("avg_core_loss_W", "N/A")
        ohmic = losses.get("avg_copper_loss_W", "N/A")
        total = losses.get("total_loss_W", "N/A")
        rows.append(f"<tr><td>铁耗</td><td>{core} W</td></tr>")
        rows.append(f"<tr><td>铜耗</td><td>{ohmic} W</td></tr>")
        rows.append(f"<tr><td>总损耗</td><td>{total} W</td></tr>")

    if back_emf:
        peak = back_emf.get("peak_emf_V", "N/A")
        rows.append(f"<tr><td>反电动势峰值</td><td>{peak} V</td></tr>")

    if thermal:
        for part, temps in thermal.items():
            if isinstance(temps, dict) and "max_temp_C" in temps:
                rows.append(f"<tr><td>{part} 最高温度</td><td>{temps['max_temp_C']} °C</td></tr>")

    if optimization:
        best = optimization.get("best_design", {})
        for k, v in best.items():
            rows.append(f"<tr><td>最优 {k}</td><td>{v}</td></tr>")

    table_content = "\n".join(rows) if rows else "<tr><td colspan='2'>暂无仿真结果数据</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{motor_name} 仿真报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }}
        h2 {{ color: #283593; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 600px; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px 14px; text-align: left; }}
        th {{ background: #e8eaf6; font-weight: bold; }}
        tr:nth-child(even) {{ background: #f5f5f5; }}
        .footer {{ color: #999; font-size: 12px; margin-top: 40px; border-top: 1px solid #eee; padding-top: 10px; }}
        .badge {{ display: inline-block; background: #1a237e; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>⚡ {motor_name} 电磁仿真报告</h1>
    <p>生成时间：{timestamp} &nbsp; <span class="badge">Ansys Agent</span></p>

    <h2>📊 主要性能指标</h2>
    <table>
        <tr><th>指标</th><th>数值</th></tr>
        {table_content}
    </table>

    <h2>📋 原始数据</h2>
    <pre style="background:#f5f5f5;padding:15px;border-radius:6px;overflow:auto;font-size:13px;">{json.dumps(results, ensure_ascii=False, indent=2)}</pre>

    <div class="footer">
        本报告由 AnsysAgent 自动生成 | Powered by Ansys + DeepSeek
    </div>
</body>
</html>"""


def _build_markdown_report(motor_name: str, timestamp: str, results: dict) -> str:
    """构建 Markdown 报告内容。"""
    lines = [
        f"# {motor_name} 电磁仿真报告",
        f"",
        f"**生成时间**：{timestamp}",
        f"",
        f"## 主要性能指标",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
    ]

    torque = results.get("torque", {})
    if torque:
        lines.append(f"| 平均转矩 | {torque.get('avg_torque_Nm', 'N/A')} Nm |")

    losses = results.get("losses", {})
    if losses:
        lines.append(f"| 铁耗 | {losses.get('avg_core_loss_W', 'N/A')} W |")
        lines.append(f"| 铜耗 | {losses.get('avg_copper_loss_W', 'N/A')} W |")
        lines.append(f"| 总损耗 | {losses.get('total_loss_W', 'N/A')} W |")

    back_emf = results.get("back_emf", {})
    if back_emf:
        lines.append(f"| 反电动势峰值 | {back_emf.get('peak_emf_V', 'N/A')} V |")

    lines.extend([
        f"",
        f"## 原始数据",
        f"",
        f"```json",
        json.dumps(results, ensure_ascii=False, indent=2),
        f"```",
        f"",
        f"---",
        f"*本报告由 AnsysAgent 自动生成*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 工具：export_aedt_report - 从 AEDT 直接导出报告
# ---------------------------------------------------------------------------

def export_aedt_report(
    output_dir: str,
    aedt_app=None,
    report_names: list[str] | None = None,
) -> dict:
    """
    将 AEDT 中已有的 Report 导出为图片和 CSV。

    Args:
        output_dir: 输出目录
        aedt_app: AEDT 应用实例（可从 maxwell_tools._aedt_app 获取）
        report_names: 要导出的报告名列表，None 则导出全部
    """
    try:
        if aedt_app is None:
            from tools.maxwell_tools import _aedt_app as app
        else:
            app = aedt_app

        if app is None:
            return _err("未连接到 AEDT，无法导出报告")

        os.makedirs(output_dir, exist_ok=True)
        exported = []
        all_reports = app.post.all_report_names
        targets = report_names or all_reports

        for name in targets:
            if name not in all_reports:
                continue
            # 导出 CSV
            csv_path = os.path.join(output_dir, f"{name}.csv")
            app.post.export_report_to_file(name, csv_path)
            # 导出图片
            img_path = os.path.join(output_dir, f"{name}.png")
            try:
                app.post.export_report_to_jpg(name, img_path)
            except Exception:
                pass
            exported.append(name)

        return _ok({
            "exported_reports": exported,
            "output_dir": output_dir,
        })
    except Exception as e:
        return _err(str(e))
