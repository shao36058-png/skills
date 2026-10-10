# HFSS 操作与弱耦合验证

## 恢复最佳模型与脚本使用

在 HFSS 选择 File → Restore Archive，将 `assets/te01-24ghz-best.aedtz` 恢复到用户选定工作目录。确认只有 `TE01_24GHz_Best` 设计及 `PhaseCheck24` 设置。归档无网格/场解，需要实际求解才能生成当前环境的原生结果；原始参考结果在分发 CSV 中。归档已经过恢复、边界数量、孔距、唯一设计/设置及几何验证，无需为了安装 skill 再运行完整求解。

导出环境需安装 PyAEDT 与 psutil，并能够连接用户许可的 HFSS。将下例中的 PID 和工程名换成实际已打开会话；`coupler.csv` 使用方便的输出路径：

```bash
python scripts/export_hfss.py --pid 12345 --project MyCoupler --design TE01_24GHz_Best --output coupler.csv
python scripts/coupler_metrics.py --csv coupler.csv --target-ghz 24 --min-directivity 40
python scripts/coupler_metrics.py --csv assets/reference-results.csv --min-directivity 40
```

自定义端口对应时传入 `--input-mode`、`--through-mode`、`--coupled-port`、`--isolated-port`；输出 metadata JSON 记录映射。CSV 中 S3/S4 等固定列名分别表示耦合、隔离和同模传输等语义，实际端口映射以 metadata 为准。

## 连接现有会话

先调用可用的 `list_aedt_sessions` 或枚举进程。明确 PID、项目及设计；不要自动选择另一台 Desktop，也不要因名称拼错创建空工程。`scripts/export_hfss.py` 在连接后先检查已打开工程和设计。传入 `--aedt-root` 时才设置对应 ANSYSEM_ROOT 环境变量；不沿用作者的本机安装路径。

PyAEDT 示例：

```python
from ansys.aedt.core import Hfss
hfss = Hfss(project=project, design=design, version=version,
            aedt_process_id=pid, new_desktop=False, close_on_exit=False)
# operations
hfss.desktop_class.release_desktop(close_projects=False, close_on_exit=False)
```

释放连接不关闭用户工程或 Desktop。只读查验和 CSV 审核不需要启动新求解。

## 几何与端口

- 从 CreateBox/CreateCylinder 历史及坐标系原点推导全局位置，不只看变量表。局部 CS 可以把模型看起来正确的 dx/dz 映射到另一传播方向。
- 对副波导轴 X、耦合壁法向 Y 的布局，宽边应沿 Z；宽边 8.16 mm 沿 Y 会把孔接到窄壁。轴线改变后重新推导方向，不能固定某一全球坐标为宽边。
- 检查完整孔中心距、边缘距和两孔是否重叠。钻孔柱需要与两个空气体积重叠；Unite 后残留孔端盖通常表示未贯通。
- 模型再生会改变面编号。先根据端口面空间位置及面积匹配，再编辑波端口；其余外表面赋 PEC。不要在孔壁或端口错误添加 PEC，也不要保留失效的面编号。
- Driven Terminal 中暂时看不到原 Modal 端口不等于模型从未设置端口。先核对原定义再转换求解类型，避免重复创建。
- 模态设置使用 Zwave，是否重归一化及去嵌入按测量定义决定。本案例无重归一化、无去嵌入。圆波导模数要由截止频率、工作带和目标模式决定，本案例 12 模不能当作通用常数。

## PyAEDT 实际行为

`boundary.props` 可能从上次保存的项目文件加载，几何与原生边界编辑后在当前 Python 对象中保持旧值。修改后保存，重新绑定 Hfss 并核对原生边界和空间面。

边界属性包含 COM/gRPC 引用时不能直接 deepcopy。需要纯属性字典时可 JSON round-trip；下例仅用于可 JSON 序列化属性。

```python
import json
from ansys.aedt.core.generic.data_handlers import _dict2arg
props = json.loads(json.dumps(dict(boundary.props)))
props["Faces"] = [matched_face_id]
args = ["NAME:" + boundary.name]
_dict2arg(props, args)
hfss.oboundary.EditWavePort(boundary.name, args)
```

模型历史的 `child_object.SetPropValue("Center Position/X", expression)` 可以编辑创建步骤。每次再生后重新获得该历史节点；不要对只读 `Command` 属性写入。孔和矩形尺寸可使用参数表达式，改动后验证端口面及贯通性。

`get_expression_data` 返回 (横轴数组, 数值数组)，不只是一个 y 向量；NumPy 值存入 JSON 前应转 `.tolist()`。标明单位与实际求解频点。

## TE01 模态识别

TE01 的理想横截面电场为环向，中心接近零，轴向电场接近零。导出至少中心和环形多点的复数电场，计算径向、环向和轴向分量。场图和截止频率共同支持识别，不以编号或传输接近 0 dB 单独定论。

在圆波导中 TE01 与 TM11 截止频率相同，且 TM11 有角向简并，求解器端口基可能旋转。临时改变源用于场检查时保存并恢复完整源幅相；当用户要将模型改为 TE01 激励，可有意设置目标模式 1 W、其他模式 0 W 并保存。源设置改变场后处理，不改变已经计算的线性 S 矩阵。

## 孔距与相位

两孔隔离方向相消要求两个复数贡献幅度相近且相位接近相反。正交结构需同时考虑主波导到孔的传播路径与副波导从孔到观察端口的传播路径。相位常数、孔处的场分布、有限孔尺寸和壁厚会影响最佳位置；不能只按自由空间四分之一波长设孔距。

可用 24 GHz 的传播相位常数粗估位移，再用少量相邻几何试算读取复数 S 参数指导修改。在深隔离谷底附近，只看 dB 幅值会丢失残余信号的符号和相位。

关于两孔隔离端的相位叠加，可参考 [Purdue《Theory of Microwave and Optical Waveguides》4.4.1 节，第 166 页](https://engineering.purdue.edu/wcchew/course/tgwAll20121211.pdf#page=176)。其并行波导例子说明相消原理；不能把并行几何的孔距公式原样应用到正交圆波导结构。

## 求解与清理

小孔弱输出远小于主波导传输。全矩阵 absolute Delta S=0.02 对 −100 dB 信号没有足够解释力。局部网格、目标项幅相收敛以及多轮输出稳定性都需要记录。数值阈值随目标精度选择，不把本案例阈值当作普适认证。

```python
setup.use_matrix_convergence(entry_selection=2, custom_entries=[
    [input_mode, through_mode, 1e-3, 0.2],
    [input_mode, coupled_port, 1e-6, 0.5],
    [input_mode, isolated_port, 1e-7, 1.0],
])
```

确认当前求解对应当前几何；插值扫频有 non-passive basis 警告时，用离散频点检查弱信号。本案例 BandCheck 使用 23.5…24.5 GHz 五个离散点。需要带宽边界时另外细扫，不宣称五点折线的峰形就是精确频率响应。

用户授权只留最佳版时，保存最终 S 数据，删去其他设计和停用的求解设置；通过 `osolution.ListVariations` 取得准确参数字符串，仅对非最终变体调用 `cleanup_solution(variations=[...])`。不要用默认 `variations="All"`。重读最终 S 参数确认一致，再保存工程。文件系统清理限于本任务生成的对比文件、备份和临时输出；保留原文献和无关工程。
