# BrainProject407

本仓库提供 BrainProject407 数据说明及 CSV 矩阵到 DTB 神经元连接表的生成代码。汇交数据来自 8 个数据集，共 588 名被试，每人一个 Shen268 的 268 × 268 矩阵：对角线为 T1w 灰质概率求和代理，非对角线为 DWI 流线计数，小于 2 的连接已置零。数据通过汇交渠道提供，不存放于本仓库。

| 汇交目录 | 来源数据集 | 被试情况 | 数据版本或选择记录 | 汇交人数 |
| --- | --- | --- | --- | ---: |
| BP407-D001 | PD_ds005849 | 帕金森病 DBS 研究样本 | 2.0.1 | 12 |
| BP407-D002 | PPMI | PD 基线选择样本 | PD140 baseline selection | 50 |
| BP407-D003 | MDD_ds006731 | MDD 研究样本 | 1.0.0 | 21 |
| BP407-D004 | Xiangya_Wang101 | 湘雅 Wang MDD 来源样本 | authorized cluster copy | 101 |
| BP407-D005 | Dystonia_ds006395 | 肌张力障碍研究样本 | 1.0.8 | 53 |
| BP407-D006 | SUDMEX_TMS（ds003037） | TMS 研究样本 | 2.1.0 | 26 |
| BP407-D007 | UCLA_ds000030 | UCLA CNP 入选样本 | 未记录 | 125 |
| BP407-D008 | HCP | HCP 入选样本 | 未记录 | 200 |

人数和来源依据 2026-10-10 汇交目录记录；被试情况描述来源研究，不推断本批样本未记录的患者与对照构成。

## 仓库内容

- `csv_to_dtb.py`：读取矩阵，分配 E/I 神经元，采样连接并输出 DTB NPZ。
- `requirements.txt`：运行依赖，仅需 NumPy。

## 快速运行

需要 Python 3.10 或以上。将输入路径替换为汇交目录中的一个 `__Shen268.csv`，输出目录使用新路径。

```bash
git clone https://github.com/ZzSym/BrainProject407.git
cd BrainProject407
python -m pip install -r requirements.txt

python csv_to_dtb.py \
  --input /path/to/subject__Shen268.csv \
  --output /path/to/dtb_output \
  --neurons 2000000 --degree 100 --blocks 2 --seed 407
```

脚本按对角灰质权重分配神经元，每脑区 E/I 比例为 4:1，最少分别为 200/50 个，实际总数因取整和下限略有变化。每个神经元按本地 E、本地 I、外部 E 的 4:1:2 概率抽取输入；外部 E 按去除对角线后的结构矩阵逐行归一化采样。孤立脑区仅保留本地 E/I，概率为 0.8/0.2。源神经元不重复且排除自身，通道权重采用项目既有 uint8 规则。该脚本重新采样连接，不保证与已有连接表逐字节相同。

输出 `module/uint8/block_*.npz` 保存神经元属性和连接；`supplementary_info/` 保存脑区与 E/I 群体、神经元范围及 block 边界等索引；`manifest.json` 记录参数和实际规模。200 万神经元、入度 100 时，连接表约 2.8 GB，生成时另需一个 block 大小的临时磁盘空间。

矩阵行序保持不变，零基脑区编号 `r` 对应 E 群体 `2r` 和 I 群体 `2r+1`。核心连接表仅需 CSV；若另有节点表，可增加 `--nodes-metadata /path/to/nodes_shen268.tsv`，读取 `matrix_index_0based`、`atlas_label`、`is_cortex` 并附带图谱映射。未知皮层属性保存为 `-1`。
