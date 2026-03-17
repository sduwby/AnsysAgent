---
name: thermal-em-coupling
description: Maxwell-Icepak 电磁-热耦合仿真流程（损耗映射→热仿真→温升提取→迭代收敛）
---

# 电磁-热耦合仿真流程

## 适用场景
在完成 Maxwell 电磁仿真后，将铜损和铁损映射到 Icepak 进行稳态热仿真，评估绕组温升和热点分布是否满足绝缘等级要求。

## 前置条件
- 已完成 Maxwell 电磁仿真并获取损耗数据（`get_losses` 结果可用）
- 已知散热条件：冷却方式（自然冷却 / 液冷 / 强迫风冷）、环境温度
- 已知绝缘等级限制温度（如 F 级 155°C）

## 执行流程

### Step 1 — 链接 Maxwell 损耗到 Icepak
```
link_maxwell_to_icepak(
    maxwell_design="Motor_2D",
    icepak_design="Motor_Thermal"
)
```
> 此步骤由 Main Agent 直接执行（跨软件协调工具）。

### Step 2 — 配置热仿真模型
```
delegate_to_agent(agent_name="icepak", task="setup_motor_thermal:
  cooling_type='liquid',        # 液冷
  coolant_temperature=25,       # 冷却液温度 °C
  flow_rate=5.0,               # 流量 L/min
  ambient_temperature=25")
```

### Step 3 — 运行热仿真
```
delegate_to_agent(agent_name="icepak", task="run_thermal_simulation")
```

### Step 4 — 提取温升结果
```
delegate_to_agent(agent_name="icepak", task="get_temperature_results:
  components=['winding_A', 'winding_B', 'winding_C', 'magnet', 'stator_core']")
```

### Step 5 — 迭代收敛（可选）
若温升影响磁钢性能（如 Br 随温度变化 > 5%），需要进行 EM-热迭代：
```
run_em_thermal_iteration(max_iterations=3, convergence_criterion=2.0)
```
> 由 Main Agent 直接执行。

## 结果评估标准

| 部件 | 绝缘等级 F 限制 | 绝缘等级 H 限制 |
|------|--------------|--------------|
| 绕组最高温度 | 155°C | 180°C |
| 永磁体温度 | < 120°C（防退磁） | < 120°C |
| 定子铁芯 | < 130°C | < 155°C |

## 注意事项
- 首次运行散热不达标时，先检查铜损计算是否正确（电流有效值 vs 峰值）
- 液冷设计中，冷却液流量对最高温度影响显著，建议做参数扫描
- 完成后提供温升汇总表和热点位置说明
