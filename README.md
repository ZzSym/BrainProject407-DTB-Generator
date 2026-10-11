# BrainProject407 数据处理说明与教程

本仓库是 `BP407-D001` 至 `BP407-D008` 数据汇交的公开使用手册，说明目录编号对应的数据来源、矩阵含义、metadata 字段和处理步骤，并提供可在本地运行的教程脚本。

**仓库不托管研究数据，也不提供研究数据下载。** 矩阵、被试映射、逐文件校验清单、节点映射表和 DTB 连接表均由数据管理方通过授权渠道提供。示例采用占位路径；测试所用小矩阵在运行时合成。

## 目录编号对应哪些数据集

下表转录项目来源记录，用于解释汇交目录编号。`BP407-D00*` 是本项目内部编号，不是上游数据库登录号。人数是 2026-10-10 已核查交付范围的汇总，不是上游数据集的完整人数。

| 汇交目录 | 来源数据集记录 | 上游标识 | 版本或选择说明 | 汇交人数 |
| --- | --- | --- | --- | ---: |
| BP407-D001 | PD_ds005849（PD DBS） | ds005849 | 2.0.1 | 12 |
| BP407-D002 | PPMI（PD baseline） | 未记录 accession | PD140 baseline selection | 50 |
| BP407-D003 | MDD_ds006731 | ds006731 | 1.0.0 | 21 |
| BP407-D004 | Xiangya_Wang101（湘雅 Wang MDD） | 内部来源 | authorized cluster copy | 101 |
| BP407-D005 | Dystonia_ds006395 | ds006395 | 1.0.8 | 53 |
| BP407-D006 | SUDMEX_TMS | ds003037 | 2.1.0 | 26 |
| BP407-D007 | UCLA_ds000030（UCLA CNP） | ds000030 | 版本未记录 | 125 |
| BP407-D008 | HCP（Human Connectome Project） | 未记录 accession | 版本未记录 | 200 |

2026-10-10 的交付目录共有 **588 个 Shen268 矩阵**，其中 **8 名被试另有 DTB 神经元连接表**；其余 580 名被试仍为脑区矩阵。该目录中没有 Shen217 矩阵。这里描述的是已检查的目录快照，后续交付内容以随数据提供的版本记录为准。

## 从哪里开始

| 目的 | 教程 |
| --- | --- |
| 只收到 D001–D008，了解目录和操作顺序 | [接收数据后的操作流程](docs/getting_started.md) |
| 理解原始编号、脑区索引、质量状态和校验字段 | [Metadata 字段字典](docs/metadata.md) |
| 读取 CSV、提取对角灰质代理、导出脑区边表 | [矩阵读取与边表导出](docs/matrix_usage.md) |
| 理解或进一步生成 DTB 神经元连接表 | [DTB 连接表处理说明](docs/dtb_tables.md) |
| 查阅来源依据、检查范围与复现限制 | [来源和版本说明](docs/provenance.md) |

## 矩阵最重要的两个含义

`__Shen268.csv` 是无表头、逗号分隔的 268 × 268 矩阵。

- **对角线**：T1w 灰质概率求和得到的脑区权重代理；不是自连接强度，也不是实测神经元数。
- **非对角线**：DWI 纤维追踪得到的流线计数。项目来源记录说明，小于 2 的连接已置零；零值和孤立脑区应保留。

分析前应单独提取对角线，将结构矩阵的对角置零。不要把灰质代理和流线计数当作同一含义的权重一起归一化。脑区身份必须按对应版本的节点表解释，不能凭矩阵序号猜测解剖名称。

**脑区边表不等于 DTB 神经元连接表。** 本仓库的边表工具只展开脑区矩阵；DTB 连接生成还涉及神经元规模、E/I 群体分配和连接采样，依赖外部模型代码。

## 快速运行

需要 Python 3.10 或以上。在仓库根目录运行，路径均替换为自己的本地路径：

```bash
git clone https://github.com/ZzSym/BrainProject407.git
cd BrainProject407
python -m pip install -r requirements.txt

# 无需额外 metadata 即可检查一个 CSV 的数值和形状。
python scripts/inspect_matrix.py "/path/to/subject_matrix__Shen268.csv"

# 导出脑区边表：排除对角、保留各个非零非对角矩阵位置。
python scripts/matrix_to_edges.py "/path/to/subject_matrix__Shen268.csv" "/path/to/new_regional_edges.csv" --direction directed

# 如已获得授权的逐文件校验清单，再检查整个交付目录。
python scripts/verify_collection.py --data-root "/path/to/data_root" --manifest "/path/to/authorized_metadata/files_manifest.tsv"
```

`directed` 表示分别记录 `A[i,j]` 和 `A[j,i]`，不代表 DWI 已证实生物学连接方向。输出文件必须是新文件，不会覆盖原矩阵。检查器支持任意非负方阵，因此本次数据还应确认输出形状为 `[268, 268]`。

## 仓库内容

```text
README.md                  入口与八个数据集的来源对照
docs/                      处理步骤、字段字典、复现说明
scripts/                   通用的本地检查与转换教程代码
tests/                     运行时合成数据的脚本测试
requirements.txt           基础工具依赖
CONTRIBUTING.md             文档更新和不上传数据的约定
```

实际的 `participants.tsv`、`files_manifest.tsv`、`nodes_shen268.tsv` 等文件不包含在仓库中。只拿到 D001–D008 时，仍可检查和数值处理矩阵；若要关联脑区身份、追溯原始编号或按既有 SHA-256 检查完整性，请向数据管理方获取对应交付版本的配套 metadata。具体要求见[操作流程](docs/getting_started.md)。

## 质量状态与使用范围

原始矩阵记录中有 580 条 `candidate_pending_human_review` 和 8 条 `available_with_isolated_nodes`。这套矩阵质量状态与“8 人已有 DTB 连接表”是独立概念，不能混同。文档整理不代表重新完成影像人工复核。

来源名称和版本在此按项目记录保留，未独立核验上游所有发布版本或许可。公开处理教程不改变原始数据的访问、使用和引用条件；D004 的去标识化编号也不能用于恢复真实身份。

运行代码测试：

```bash
python -m unittest discover -s tests -v
```
