"""
整车碰撞安全仿真工具包入口（重导出）。

子模块：
  crash_deck.py        — Deck 构建、材料/截面/部件/接触/壁障、工况设置、求解
  crash_postprocess.py — 后处理解析（GLSTAT/NODOUT/RCFORC/BNDOUT）、损伤指标计算
  crash_setup.py       — Deck 关键字装配（集合、约束、曲线、安全带、假人、气囊）
  crash_compliance.py  — 合规评估（Euro NCAP / FMVSS 208 / C-NCAP）、报告生成
"""

from tools.crash_deck import (
    _get_deck,
    _ensure_deck,
    _crash_config,
    create_crash_deck,
    load_vehicle_model,
    add_crash_material,
    add_crash_section,
    add_crash_part,
    add_crash_contact,
    add_rigid_wall,
    setup_frontal_crash,
    setup_side_crash,
    setup_rear_crash,
    setup_pedestrian_protection,
    add_initial_velocity,
    add_gravity_load,
    list_deck_keywords,
    export_crash_model,
    run_crash_simulation,
    get_crash_results,
    get_dummy_injury_criteria,
    disconnect_crash_solver,
)

from tools.crash_postprocess import (
    parse_glstat,
    parse_nodout,
    parse_rcforc,
    parse_bndout,
    compute_hic,
    compute_chest_3ms,
    compute_nij,
    check_energy_balance,
    get_intrusion_at_node,
)

from tools.crash_setup import (
    add_node_set,
    add_segment_set,
    add_part_set,
    add_constrained_rigid_bodies,
    define_curve,
    add_joint,
    add_seatbelt,
    place_rigid_wall_occ,
    import_barrier_model,
    place_dummy_model,
    setup_airbag,
    add_pretensioner,
)

from tools.crash_compliance import (
    evaluate_ncap_frontal,
    generate_crash_report,
)

__all__ = [
    "_get_deck", "_ensure_deck", "_crash_config",
    "create_crash_deck", "load_vehicle_model", "add_crash_material",
    "add_crash_section", "add_crash_part", "add_crash_contact", "add_rigid_wall",
    "setup_frontal_crash", "setup_side_crash", "setup_rear_crash",
    "setup_pedestrian_protection", "add_initial_velocity", "add_gravity_load",
    "list_deck_keywords", "export_crash_model", "run_crash_simulation",
    "get_crash_results", "get_dummy_injury_criteria", "disconnect_crash_solver",
    "parse_glstat", "parse_nodout", "parse_rcforc", "parse_bndout",
    "compute_hic", "compute_chest_3ms", "compute_nij",
    "check_energy_balance", "get_intrusion_at_node",
    "add_node_set", "add_segment_set", "add_part_set",
    "add_constrained_rigid_bodies", "define_curve", "add_joint", "add_seatbelt",
    "place_rigid_wall_occ", "import_barrier_model", "place_dummy_model",
    "setup_airbag", "add_pretensioner",
    "evaluate_ncap_frontal", "generate_crash_report",
]
