---
name: hfss-et-divider
description: Inspect and tune HFSS rectangular-waveguide E-plane T power dividers with symmetric matching irises. Use for input reflection, equal split, modal phase, iris dimensions, arm length changes, reverse combining, and saved-result checks in existing AEDT projects.
license: MIT
metadata:
  author: shao36058-png
  version: "0.1.0"
---

# HFSS E 面 T 形功分器

处理现有 HFSS E-T 二路功分器的检查、对称膜片匹配、尺寸调整和结果交付。先读取当前工程及已有结果；案例的端口编号、频段、尺寸与模式数不是新工程的默认要求。简单的尺寸或结果解释可直接使用已有记录，无需启动求解。

## 按任务读取

- 建模、修改横臂/输入支路长度、解释开口/深入/厚度或相位：读 [几何与电磁约定](references/et-design.md)。其中有 60 mm 横臂、30 mm 输入支路的完整案例。
- 连接已打开 AEDT、提取结果、调整端口、创建扫频、恢复求解或归档：读 [AEDT 操作与结果完整性](references/aedt-workflow.md)。先核实会话、绝对工程路径、设计和物理输入端口。
- 只审核导出的复数 S 参数：使用下方离线工具。它不连接 AEDT，不创建工程，也不求解。

## 调参与判断

确认用户频段、输入端口/模式、结构约束和目标指标。保留当前精度设置开展初次调参。目标应覆盖指定频段最差输入反射，并同时检查两路幅度、相对相位和功率去向；只改善一个频率处的凹点不能代表全带改善。

区分宽边开口 `w`、单侧深入 `(a-w)/2`、沿传播方向厚度 `t` 和从 T 结外壁到膜片中心的距离 `di`。膜片的近面/远面距离为 `di∓t/2`。支路加长不意味着膜片位置按比例放大；先保持结区参考位置，再按实际结果决定是否调参。

在用户要求的对称 E-T 结构内，优先调两片的开口和位置。使用有限候选或有界优化，保留已验证最好结果；一轮结束报告改进和剩余问题，再决定是否有必要继续。除非发现具体精度问题或用户要求，不因曲线尚能改善而反复加密网格、增加模式或离散频点。

读取实际输入列的模态 S 参数。本例端口 2 馈入时检查 `S(2:1,2:1)`、`S(1:1,2:1)`、`S(3:1,2:1)`。每路约 −3.01 dB 是理想等分量级，不能当作导体耗散。功率和须考虑其他传播模及实际损耗通道。

在一致的输出模式极性/积分线及参考面下，E-T 两路约相差 180°；端口积分线翻转会改变报告相位。反向合成需要让 `S21*a1` 与 `S23*a3` 同相，不能把任意两路信号接入后就保证高效合成。

区分自适应网格收敛、插值精度和独立离散求解。下方案例是 21 个插值输出样点。PEC 匹配数据不能作为无氧铜、空气、水冷条件下的连续功率额定值；若用户要求容量，另按实际圆角、损耗和热边界评估。

## 离线审核

需要 Python 3.10+，仅使用标准库。在当前技能目录执行：

```bash
python scripts/divider_metrics.py --input assets/reference-case.json --max-reflection-db -25 --min-frequency-ghz 23 --max-frequency-ghz 25
```

输入 JSON 必须包含 `frequencies_GHz` 和 `data`；每个 S 表达式包含等长 `real`、`imag` 数组。可选 `parameters` 使用案例参数名和 mm 单位。可选 `sweep_type`、`setup_sweep` 和 `validation` 用于记录来源；工具无法仅凭这些标签证明求解类型或收敛。复用时导出当前工程的实际数据，勿将案例文件作为待检查工程的结果。

默认公共端口为 2，输出为 1/3；用 `--reflection-expression` 和 `--output-expressions` 修改。用 `--expected-phase-deg` 修改相位基准，`--output` 保存报告到工作目录。数值检查失败返回非零状态；无阈值时只计算指标。零幅度造成的无定义值报告为 `null`。

参考案例最差输入反射约 −28.342 dB，两路相对 180° 的最大误差约 0.0465°，最大幅度差约 0.00321 dB。完整案例数据见 [reference-case.json](assets/reference-case.json)，证据范围见几何参考。实际 HFSS 二进制工程和引用论文不随此技能分发。

交付时说明当前几何、真实求解/扫频设置、指标及其适用范围。用户要求仅留最好一版或迁移目录时，先验证最终工程与匹配结果可重开，再只清理获授权的候选文件；不触及共享桌面中的其他工程。
