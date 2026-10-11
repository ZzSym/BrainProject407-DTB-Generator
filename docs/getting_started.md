# 接收数据后的操作流程

本教程适用于通过授权渠道收到 `BP407-D001` 至 `BP407-D008` 的使用者。所有检查和转换都在自己的存储空间完成，输出文件不提交到公开仓库。

## 1. 把数据和教程分开存放

建议使用如下布局。尖括号内是格式占位符，不是真实被试记录；数据父目录不必叫 `data_root`。

```text
work/
├── BrainProject407/                 # 克隆的公开教程仓库
├── data_root/                       # 授权获取的数据
│   ├── BP407-D001/
│   │   └── <subject-folder>/
│   │       └── <subject-folder>__Shen268.csv
│   ├── BP407-D002/
│   ├── ...
│   └── BP407-D008/
├── authorized_metadata/             # 如管理方另行提供配套索引
│   ├── participants.tsv
│   ├── files_manifest.tsv
│   └── nodes_shen268.tsv
└── outputs/                         # 自己的分析输出
```

`<subject-folder>` 遵循 `Sxxxx__orig-<source-id>` 命名格式。`Sxxxx` 是项目编号；`<source-id>` 是来源被试编号或去标识化索引。原始编号可能自带 `sub-` 前缀，应完整保留。D004 的来源字段是伪名索引，不是原始姓名。

不要将 `BP407-D00*` 数据目录整体复制到公开 Git 仓库后执行 `git add .`。本仓库的忽略规则减少误添加，但不能替代提交前检查。

## 2. 明确手头有哪些材料

| 已获得材料 | 可以完成 | 仍需要的材料 |
| --- | --- | --- |
| 只有八个数据目录及其中的 CSV | 检查文件形状和数值；分离对角代理；导出脑区位置索引边表 | 解剖学解释所需节点表；逐人来源映射；既有校验清单 |
| 另有节点表 | 将矩阵行列对应到图谱标签 | 原始被试信息仍以授权来源映射为准 |
| 另有 files_manifest.tsv | 对列出的 CSV 校验路径、存在性和 SHA-256 | 校验清单本身须来自可信的交付渠道 |
| 被试目录中另有 dtb_2m_d100_blocks2_int_ext | 按对应 manifest、补充数组与匹配的 DTB 环境读取连接表 | DTB 模型代码、环境与格式说明 |

metadata 本身也可能包含受限制的信息，因此它不在这个公开仓库里。缺少哪一项就向数据管理方索取对应版本；不要生成空的映射表来代替真实来源，也不要把新计算的哈希当作独立证明原文件正确的依据。

## 3. 安装教程依赖

在仓库目录安装 NumPy 即可使用矩阵工具，完整性检查器只用 Python 标准库：

```bash
python -m pip install -r requirements.txt
```

这些依赖只支持本仓库的读取和转换脚本，不等同于完整 DTB 运行环境。

## 4. 有清单时先检查完整性

```bash
python scripts/verify_collection.py --data-root "/path/to/data_root" --manifest "/path/to/authorized_metadata/files_manifest.tsv"
```

`--data-root` 必须是八个 `BP407-D00*` 的共同父目录，不能指向其中某个被试目录。清单中的 `path` 相对于这个父目录。`--manifest` 是必填参数，仓库不提供隐式默认清单。

程序仅读取清单明确列出的 CSV，报告记录数、检查文件数、SHA-256 检查数和错误数。返回码 0 表示本次清单检查通过，1 表示失败；`--skip-hash` 只检查路径和文件存在性，不能据此确认文件内容。

程序不扫描未列出的文件，不验证 NPZ，不检查影像质量，也不通过哈希推断矩阵的科学意义。如果文件缺失或哈希不一致，保留原文件并与数据管理方核对；不要直接重存 CSV 来“修复”校验错误。

## 5. 检查单个矩阵并提取对角代理

```bash
python scripts/inspect_matrix.py "/path/to/subject_matrix__Shen268.csv"
python scripts/inspect_matrix.py "/path/to/subject_matrix__Shen268.csv" --diagonal-output "/path/to/new_diagonal_proxy.csv"
```

确认形状为 `[268, 268]`、数值有限且非负。对称性是单独的报告字段；非对称不会被工具自动修复。孤立脑区不应直接删除，零连接也不应通过任意小常数替代。

提取的对角代理应单独保存，之后分析非对角结构连接。输出文件的父目录须已存在，输出路径本身必须不存在。

## 6. 根据分析目的选择输出

如果只需脑区网络分析，按[矩阵使用教程](matrix_usage.md)导出边表。节点编号从 1 开始，必须用授权节点表中的 `matrix_index_1based` 或 `matrix_index_0based + 1` 解释。

如果需要 DTB 神经元连接，继续阅读[连接表处理说明](dtb_tables.md)。现有矩阵不是可直接启动仿真的神经元突触表；缺少外部生成器或运行环境时，应先补齐这些依赖。

## 7. 保存自己的处理记录

在数据的受控存储位置记录输入文件校验值、数据交付版本、节点表版本、教程仓库 commit、命令、依赖版本及输出位置。保留未经改写的原 CSV，分析产物另存。提交到这个公开仓库的内容仅限通用说明和代码，不包括自己的处理结果、被试列表或逐文件运行记录。
