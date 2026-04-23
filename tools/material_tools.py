"""Material library tools – manage a local JSON-backed material database.

Library file: <ANSYS_DATA_DIR>/materials/library.json
Schema per entry:
{
    "category":       str,
    "description":    str,
    "conductivity":   float | None,   # S/m
    "mass_density":   float | None,   # kg/m³
    "bh_curve":       [[H, B], ...] | None,
    "core_loss_kh":   float | None,
    "core_loss_kc":   float | None,
    "core_loss_ke":   float | None,
    "remanence_br":   float | None,   # T
    "coercivity_hcb": float | None,   # A/m
    "energy_product": float | None,   # kJ/m³
    "tags":           [str, ...],
    "_builtin":       bool            # protected from accidental deletion
}
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from agent.paths import ANSYS_DATA_DIR
from tools.utils import _err, _ok, ensure_parent_dir, ok_message

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LIB_PATH: Path = ANSYS_DATA_DIR / "materials" / "library.json"


def _load_library() -> dict[str, dict]:
    """Load the material library from disk; return empty dict if not found."""
    if not _LIB_PATH.exists():
        return {}
    with open(_LIB_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _save_library(lib: dict[str, dict]) -> None:
    """Persist the material library to disk, creating parent dirs as needed."""
    ensure_parent_dir(str(_LIB_PATH))
    with open(_LIB_PATH, "w", encoding="utf-8") as fh:
        json.dump(lib, fh, ensure_ascii=False, indent=2)


def _material_matches(name: str, entry: dict, query: str) -> bool:
    """Return True if *query* (case-insensitive) appears in name/description/tags."""
    q = query.lower()
    if q in name.lower():
        return True
    if q in entry.get("description", "").lower():
        return True
    for tag in entry.get("tags") or []:
        if q in tag.lower():
            return True
    return False


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------


def add_material(
    name: str,
    category: str = "",
    description: str = "",
    conductivity: float | None = None,
    mass_density: float | None = None,
    bh_curve: list[list[float]] | None = None,
    core_loss_kh: float | None = None,
    core_loss_kc: float | None = None,
    core_loss_ke: float | None = None,
    remanence_br: float | None = None,
    coercivity_hcb: float | None = None,
    energy_product: float | None = None,
    tags: list[str] | None = None,
    overwrite: bool = False,
) -> dict:
    """Add or update a material entry in the local material library.

    Args:
        name: Unique material name (case-sensitive key).
        category: Material category, e.g. 'steel', 'magnet', 'copper'.
        description: Human-readable description.
        conductivity: Electrical conductivity in S/m.
        mass_density: Mass density in kg/m³.
        bh_curve: B-H curve as a list of [H, B] pairs (A/m, T).
        core_loss_kh: Hysteresis loss coefficient.
        core_loss_kc: Classical eddy-current loss coefficient.
        core_loss_ke: Excess (anomalous) loss coefficient.
        remanence_br: Remanent flux density in T (for permanent magnets).
        coercivity_hcb: Coercivity in A/m.
        energy_product: Maximum energy product in kJ/m³.
        tags: Arbitrary search tags.
        overwrite: If False (default) refuse to overwrite an existing entry.
    """
    try:
        name = name.strip()
        if not name:
            return _err("材料名称不能为空")
        lib = _load_library()
        if name in lib and not overwrite:
            return _err(f"材料 '{name}' 已存在，如需覆盖请设置 overwrite=True")
        action = "更新" if name in lib else "添加"
        entry: dict[str, Any] = {
            "category": category or "",
            "description": description or "",
            "conductivity": conductivity,
            "mass_density": mass_density,
            "bh_curve": bh_curve,
            "core_loss_kh": core_loss_kh,
            "core_loss_kc": core_loss_kc,
            "core_loss_ke": core_loss_ke,
            "remanence_br": remanence_br,
            "coercivity_hcb": coercivity_hcb,
            "energy_product": energy_product,
            "tags": tags or [],
            "_builtin": lib.get(name, {}).get("_builtin", False),
        }
        lib[name] = entry
        _save_library(lib)
        action = "更新" if name in lib else "添加"
        return _ok(ok_message(
            f"材料 '{name}' 已{action}至本地库",
            name=name,
            library_path=str(_LIB_PATH),
            total_materials=len(lib),
        ))
    except Exception as exc:
        return _err(str(exc))


def list_materials(
    category: str = "",
    query: str = "",
    top_k: int = 50,
) -> dict:
    """List materials from the local library, with optional filtering.

    Args:
        category: Filter by category (empty string = all categories).
        query: Fuzzy keyword filter applied to name, description, and tags.
        top_k: Maximum number of results to return.
    """
    try:
        if top_k <= 0:
            return _err("top_k 必须为正整数")
        lib = _load_library()
        results = []
        for name, entry in lib.items():
            if category and entry.get("category", "") != category:
                continue
            if query and not _material_matches(name, entry, query):
                continue
            results.append({
                "name": name,
                "category": entry.get("category", ""),
                "description": entry.get("description", ""),
                "tags": entry.get("tags") or [],
                "_builtin": entry.get("_builtin", False),
            })
        truncated = len(results) > top_k
        results = results[:top_k]
        return _ok(ok_message(
            f"共找到 {len(results)} 条材料记录" + ("（已截断）" if truncated else ""),
            count=len(results),
            truncated=truncated,
            category_filter=category or None,
            query_filter=query or None,
            materials=results,
        ))
    except Exception as exc:
        return _err(str(exc))


def get_material(name: str) -> dict:
    """Retrieve the full material entry by name.

    Args:
        name: Exact material name (case-sensitive).
    """
    try:
        name = name.strip()
        lib = _load_library()
        if name not in lib:
            return _err(f"材料 '{name}' 不存在于本地库中")
        entry = dict(lib[name])
        return _ok(ok_message(
            f"已获取材料 '{name}'",
            name=name,
            **entry,
        ))
    except Exception as exc:
        return _err(str(exc))


def delete_material(name: str, force: bool = False) -> dict:
    """Delete a material entry from the local library.

    Args:
        name: Exact material name to delete.
        force: If False (default), built-in materials are protected.
    """
    try:
        name = name.strip()
        lib = _load_library()
        if name not in lib:
            return _err(f"材料 '{name}' 不存在，无需删除")
        entry = lib[name]
        if entry.get("_builtin") and not force:
            return _err(
                f"材料 '{name}' 是内置材料，受保护。如需删除请设置 force=True"
            )
        del lib[name]
        _save_library(lib)
        return _ok(ok_message(
            f"材料 '{name}' 已从本地库删除",
            name=name,
            remaining_materials=len(lib),
        ))
    except Exception as exc:
        return _err(str(exc))


def import_bh_from_csv(
    material_name: str,
    csv_path: str,
    h_column: int = 0,
    b_column: int = 1,
    skip_header: bool = True,
    create_if_missing: bool = False,
    category: str = "",
) -> dict:
    """Import a B-H curve from a CSV file into the specified material.

    The CSV must contain at least two numeric columns: H (A/m) and B (T).

    Args:
        material_name: Target material name.
        csv_path: Absolute path to the CSV file.
        h_column: Zero-based column index for H values (default 0).
        b_column: Zero-based column index for B values (default 1).
        skip_header: Skip the first row if it contains column headers.
        create_if_missing: Create a new material entry if it doesn't exist.
        category: Category to assign when creating a new material.
    """
    try:
        csv_path = os.path.expanduser(csv_path)
        if not os.path.isfile(csv_path):
            return _err(f"CSV 文件不存在: {csv_path}")

        bh_pairs: list[list[float]] = []
        with open(csv_path, encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            for row_idx, row in enumerate(reader):
                if skip_header and row_idx == 0:
                    continue
                if not row:
                    continue
                try:
                    h_val = float(row[h_column])
                    b_val = float(row[b_column])
                    bh_pairs.append([h_val, b_val])
                except (IndexError, ValueError) as parse_err:
                    return _err(
                        f"CSV 第 {row_idx + 1} 行解析失败: {parse_err} | 行内容: {row}"
                    )

        if not bh_pairs:
            return _err("CSV 中未找到有效的 B-H 数据行")

        lib = _load_library()
        if material_name not in lib:
            if not create_if_missing:
                return _err(
                    f"材料 '{material_name}' 不存在。如需自动创建请设置 create_if_missing=True"
                )
            lib[material_name] = {
                "category": category or "",
                "description": "",
                "conductivity": None,
                "mass_density": None,
                "bh_curve": None,
                "core_loss_kh": None,
                "core_loss_kc": None,
                "core_loss_ke": None,
                "remanence_br": None,
                "coercivity_hcb": None,
                "energy_product": None,
                "tags": [],
                "_builtin": False,
            }

        lib[material_name]["bh_curve"] = bh_pairs
        _save_library(lib)
        return _ok(ok_message(
            f"已将 {len(bh_pairs)} 个 B-H 数据点导入材料 '{material_name}'",
            material_name=material_name,
            num_points=len(bh_pairs),
            csv_path=csv_path,
            h_column=h_column,
            b_column=b_column,
        ))
    except Exception as exc:
        return _err(str(exc))


def export_material_for_aedt(name: str) -> dict:
    """Export a material entry as a Maxwell/AEDT material definition string.

    The returned string uses the ``$begin 'Material' ... $end 'Material'``
    format understood by Ansys Maxwell and AEDT.

    Args:
        name: Exact material name to export.
    """
    try:
        name = name.strip()
        lib = _load_library()
        if name not in lib:
            return _err(f"材料 '{name}' 不存在于本地库中")
        m = lib[name]

        lines: list[str] = [f"\t$begin 'Material'"]
        lines.append(f"\t\tName('{name}')")

        if m.get("conductivity") is not None:
            lines.append(f"\t\tbulk_conductivity='{m['conductivity']}'")
        if m.get("mass_density") is not None:
            lines.append(f"\t\tmass_density='{m['mass_density']}'")
        if m.get("core_loss_kh") is not None:
            lines.append(f"\t\tcore_loss_kh='{m['core_loss_kh']}'")
        if m.get("core_loss_kc") is not None:
            lines.append(f"\t\tcore_loss_kc='{m['core_loss_kc']}'")
        if m.get("core_loss_ke") is not None:
            lines.append(f"\t\tcore_loss_ke='{m['core_loss_ke']}'")
        if m.get("remanence_br") is not None:
            lines.append(f"\t\tremanence_br='{m['remanence_br']}'")
        if m.get("coercivity_hcb") is not None:
            lines.append(f"\t\tcoercivity_hcb='{m['coercivity_hcb']}'")
        if m.get("energy_product") is not None:
            lines.append(f"\t\tenergy_product='{m['energy_product']}'")

        bh = m.get("bh_curve")
        if bh:
            bh_str = ", ".join(f"({p[0]}, {p[1]})" for p in bh)
            lines.append(f"\t\tbh_curve='{bh_str}'")

        lines.append("\t$end 'Material'")
        aedt_str = "\n".join(lines)

        return _ok(ok_message(
            f"已生成材料 '{name}' 的 AEDT 定义",
            name=name,
            aedt_definition=aedt_str,
        ))
    except Exception as exc:
        return _err(str(exc))


def update_material_metadata(
    name: str,
    description: str | None = None,
    tags: list[str] | None = None,
    core_loss_kh: float | None = None,
    core_loss_kc: float | None = None,
    core_loss_ke: float | None = None,
    conductivity: float | None = None,
    mass_density: float | None = None,
) -> dict:
    """Update selected metadata fields of an existing material (B-H curve preserved).

    Only the explicitly-provided (non-None) arguments are updated; all other
    fields—including ``bh_curve``—are left unchanged.

    Args:
        name: Exact material name to update.
        description: New description text.
        tags: Replace the tag list (pass empty list to clear).
        core_loss_kh: Hysteresis loss coefficient.
        core_loss_kc: Classical eddy-current loss coefficient.
        core_loss_ke: Excess loss coefficient.
        conductivity: Electrical conductivity in S/m.
        mass_density: Mass density in kg/m³.
    """
    try:
        name = name.strip()
        lib = _load_library()
        if name not in lib:
            return _err(f"材料 '{name}' 不存在于本地库中")

        entry = lib[name]
        updated_fields: list[str] = []

        if description is not None:
            entry["description"] = description
            updated_fields.append("description")
        if tags is not None:
            entry["tags"] = tags
            updated_fields.append("tags")
        if core_loss_kh is not None:
            entry["core_loss_kh"] = core_loss_kh
            updated_fields.append("core_loss_kh")
        if core_loss_kc is not None:
            entry["core_loss_kc"] = core_loss_kc
            updated_fields.append("core_loss_kc")
        if core_loss_ke is not None:
            entry["core_loss_ke"] = core_loss_ke
            updated_fields.append("core_loss_ke")
        if conductivity is not None:
            entry["conductivity"] = conductivity
            updated_fields.append("conductivity")
        if mass_density is not None:
            entry["mass_density"] = mass_density
            updated_fields.append("mass_density")

        if not updated_fields:
            return _err("未提供任何要更新的字段（所有参数均为 None）")

        lib[name] = entry
        _save_library(lib)
        return _ok(ok_message(
            f"材料 '{name}' 元数据已更新",
            name=name,
            updated_fields=updated_fields,
            library_path=str(_LIB_PATH),
        ))
    except Exception as exc:
        return _err(str(exc))
