# 矩阵检查与脑区边表导出

本教程说明如何在本地读取已获授权的 BrainProject407 矩阵。公开仓库提供工具与说明，实际矩阵、受试者信息、节点映射表和转换结果均由使用者在仓库外保存。下文的 `/path/to/...` 都是占位路径，请替换为本机的外部输入或输出路径。

目标矩阵是没有行列标题、逗号分隔的 `268 × 268` 数值 CSV。非对角元素是 DWI 流线计数，生成阶段已将小于 2 的非对角值置零；这些被置零的原始值不能由当前文件恢复。对角元素是 T1w 灰质概率求和代理，**不能解释为自连接**，也不能直接视为神经元数量或未经核实的物理体积。工具始终从边表中排除对角，并可将对角代理单独导出。

这些工具输出的是 **Shen268 脑区级边表**，不是 DTB 神经元级连接表，也不执行由脑区连接推导神经元连接的建模。

## 安装

在仓库根目录运行。需要 Python 3.10 或以上；第三方依赖只有 NumPy。

```bash
python -m pip install -r requirements.txt
```

## 检查一个外部文件

将矩阵路径替换为自己获授权的数据文件路径。若要导出对角代理，请预先创建仓库外的输出目录；输出文件本身必须不存在。

```bash
python scripts/inspect_matrix.py "/path/to/authorized_data/matrix.csv"
python scripts/inspect_matrix.py "/path/to/authorized_data/matrix.csv" --diagonal-output "/path/to/local_outputs/diagonal_proxy.csv"
```

检查结果以 JSON 输出至终端，包含矩阵形状、非有限值和负值数量、非对角正值数量，以及非对角对应位置的最大绝对对称偏差。非方阵、空文件、无法解析的 CSV、NaN、无穷值或负值均返回退出码 `2`；有效非负方阵返回 `0`。对称性在摘要中单独报告，非对称本身不会导致检查工具返回失败。工具不会修改原矩阵，也不会覆盖已存在的对角输出文件。

对角 CSV 字段是 `node_index,gray_matter_probability_sum_proxy`。`node_index` 从 1 开始，与矩阵的行列顺序一致。

工具也接受其他尺寸的方阵，因此返回 `0` 不表示图谱已经确认。分析本项目数据时还应确认摘要中的 `shape` 为 `[268, 268]`，并使用与该矩阵配套的 Shen268 节点表。

## 在 Python 中读取矩阵与外部节点表

节点映射表不随公开仓库提供，应从获授权的数据交付中取得。以下示例显式指定矩阵和节点表的外部路径，保留灰质代理，并取得对角已清零的结构矩阵：

```python
import csv
from pathlib import Path

import numpy as np

matrix_path = Path("/path/to/authorized_data/matrix.csv")
nodes_path = Path("/path/to/authorized_metadata/nodes_shen268.tsv")

A = np.loadtxt(matrix_path, delimiter=",", ndmin=2)
if A.shape != (268, 268):
    raise ValueError(f"Expected a 268 x 268 matrix, got {A.shape}")
if not np.isfinite(A).all() or (A < 0).any():
    raise ValueError("Matrix must contain finite, nonnegative values")

gray_matter_proxy = np.diag(A).copy()
structural = A.copy()
np.fill_diagonal(structural, 0)

with nodes_path.open(encoding="utf-8-sig", newline="") as stream:
    nodes = list(csv.DictReader(stream, delimiter="\t"))
if [int(row["matrix_index_0based"]) for row in nodes] != list(range(268)):
    raise ValueError("Node table must list matrix_index_0based 0..267 in matrix order")
# structural[i, j] 的图谱标签分别由 nodes[i] 和 nodes[j] 的 atlas_label 取得。
```

示例只在内存中创建数组，不改写输入文件，也不下载节点映射。节点表应包含 `matrix_index_0based`、`atlas_label` 和 `is_cortex`；字段含义和版本应以配套数据说明为准。

## 导出脑区级边表

必须显式选择 `--direction`。以下示例保留每个非零非对角矩阵位置，`A[i,j]` 写成从节点 `i+1` 到 `j+1` 的一行：

```bash
python scripts/matrix_to_edges.py "/path/to/authorized_data/matrix.csv" "/path/to/local_outputs/regional_edges.csv" --direction directed
```

这里的 `directed` 是边表的记录方式，**不代表 DWI 数据已提供或证实生物学连接方向**。如果原矩阵对称，两个方向都会输出，进行总权重或边数统计时应考虑这一点。

如果所做分析将连接视为无向，并且矩阵通过对称性检查，可使用：

```bash
python scripts/matrix_to_edges.py "/path/to/authorized_data/matrix.csv" "/path/to/local_outputs/regional_edges_undirected.csv" --direction undirected
```

无向导出默认要求非对角元素严格对称，只读取上三角 `i < j`，每对节点输出一次，不平均两侧权重。若确认差异只是可接受的数值误差，可以显式指定绝对容差，例如 `--symmetry-atol 1e-8`。容差不是修复操作：工具只检查对应两侧值的绝对差是否在容差内，**仍输出上三角的原值，另一侧数值不写入边表**。不能用放宽容差来掩盖来源不明的不对称。

输出 CSV 有三个字段：

| 字段 | 含义 |
| --- | --- |
| `source_node` | 矩阵行位置，从 1 开始 |
| `target_node` | 矩阵列位置，从 1 开始 |
| `weight` | 对应非对角元素原值 |

节点编号与外部节点表中的 `matrix_index_0based` 按 `source_node - 1` 或 `target_node - 1` 对齐，再读取 `atlas_label` 和 `is_cortex`。不要仅凭名称假设 `atlas_label` 与边表的节点编号相同。导出脚本不读取节点映射表，也不自动将节点编号替换为图谱标签。

默认省略零权重位置；加上 `--include-zero` 可以保留零权重位置，对角仍然排除。导出不再阈值化、不归一化、不取绝对值，也不四舍五入为整数。数值以 float64 读取并以最多 17 位有效数字写出，以保留解析后的数值精度；CSV 的原始文本表示可能变化。

输出路径必须不存在，父目录必须已存在。验证失败时不会创建输出文件；输出存在时会返回退出码 `2` 并保留原文件。输出与输入使用同一路径也会被拒绝。成功返回 `0`。请将派生边表和对角代理继续保存在自己的外部工作目录。

## 运行合成数据测试

```bash
python -m unittest discover -s tests -v
```

测试矩阵由测试代码在运行时生成，临时文件随测试结束清理。测试不需要受试者数据或节点映射，覆盖对角排除、方向选择、非对称矩阵、非有限值、负值、零权重、容差、空或不规则 CSV，以及已有文件保护。
