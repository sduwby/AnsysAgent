---
name: maxwell-motor-workflow
description: Maxwell 2D 永磁同步电机电磁仿真标准流程（建模→材料→绕组→仿真→结果）
---

# Maxwell 电机仿真标准流程

## 适用场景
用于完成永磁同步电机（PMSM）从零开始的 Maxwell 2D 电磁仿真，覆盖从参数确认到结果提取的全流程。

## 前置确认（执行前须与用户核实）
- 极槽配合（默认 36 槽 / 6 极）
- 定子外径 / 内径（mm）
- 转子外径 / 永磁体厚度（mm）
- 额定转速（rpm）、额定电流（A 峰值）
- 磁钢牌号（如 N35、N42）

## 执行流程

### Step 1 — 连接 AEDT
```
delegate_to_agent(agent_name="maxwell", task="connect_aedt: 连接 Maxwell 2D 设计环境")
```

### Step 2 — 建立电机几何
```
delegate_to_agent(agent_name="maxwell", task="create_motor_geometry:
  slots=36, poles=6,
  stator_outer_diameter=150, stator_inner_diameter=90,
  rotor_outer_diameter=89.5, magnet_thickness=5,
  stack_length=80")
```

### Step 3 — 分配材料
```
delegate_to_agent(agent_name="maxwell", task="assign_material:
  - 定子铁芯 → 硅钢片（M19_24G 或 create_custom_material 自定义 B-H 曲线）
  - 永磁体  → N35（coercivity / remanence 参数参考供应商数据）
  - 绕组    → copper（电导率 5.8e7 S/m）")
```

### Step 4 — 配置绕组激励
```
delegate_to_agent(agent_name="maxwell", task="setup_winding:
  phases=3, layers=2, current_amplitude={额定电流}, frequency=50")
```

### Step 5 — 添加求解设置
```
delegate_to_agent(agent_name="maxwell", task="add_solution_setup:
  stop_time=0.02, time_step=0.0002, mesh_link=True")
```

### Step 6 — 运行仿真
```
delegate_to_agent(agent_name="maxwell", task="run_simulation")
```

### Step 7 — 提取结果
```
delegate_to_agent(agent_name="maxwell", task="get_torque: 提取平均转矩和转矩脉动")
delegate_to_agent(agent_name="maxwell", task="get_back_emf: 提取反电动势波形")
delegate_to_agent(agent_name="maxwell", task="get_losses: 提取铜损和铁损")
```

## 常见问题与处理

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 仿真不收敛 | 时间步过大 | 将 time_step 减半 |
| 转矩脉动过大 | 槽口宽度不合适 | 调整 slot_opening 参数 |
| 铁损偏高 | B-H 曲线缺少高频项 | 补充 Kh/Kc/Ke 系数 |

## 注意事项
- 建立几何前务必与用户确认关键参数，几何创建后修改代价较高
- 仿真完成后，将关键数值（转矩、效率、温升上限）汇报给用户
- 如需热分析，完成本流程后调用 `thermal-em-coupling` 技能
