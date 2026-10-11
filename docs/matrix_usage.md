# �������������߱�����

���̳�˵������ڱ��ض�ȡ�ѻ���Ȩ�� BrainProject407 ���󡣹����ֿ��ṩ������˵����ʵ�ʾ�����������Ϣ���ڵ�ӳ�����ת���������ʹ�����ڲֿ��Ᵽ�档���ĵ� `/path/to/...` ����ռλ·�������滻Ϊ�������ⲿ��������·����

Ŀ�������û�����б��⡢���ŷָ��� `268 �� 268` ��ֵ CSV���ǶԽ�Ԫ���� DWI ���߼��������ɽ׶��ѽ�С�� 2 �ķǶԽ�ֵ���㣻��Щ�������ԭʼֵ�����ɵ�ǰ�ļ��ָ����Խ�Ԫ���� T1w ���ʸ�����ʹ�����**���ܽ���Ϊ������**��Ҳ����ֱ����Ϊ��Ԫ������δ����ʵ���������������ʼ�մӱ߱����ų��Խǣ����ɽ��ԽǴ�������������

��Щ����������� **Shen268 �������߱�**������ DTB ��Ԫ�����ӱ���Ҳ��ִ�������������Ƶ���Ԫ���ӵĽ�ģ��

## ��װ

�ڲֿ��Ŀ¼���С���Ҫ Python 3.10 �����ϣ�����������ֻ�� NumPy��

```bash
python -m pip install -r requirements.txt
```

## ���һ���ⲿ�ļ�

������·���滻Ϊ�Լ�����Ȩ�������ļ�·������Ҫ�����ԽǴ�������Ԥ�ȴ����ֿ�������Ŀ¼������ļ��������벻���ڡ�

```bash
python scripts/inspect_matrix.py "/path/to/authorized_data/matrix.csv"
python scripts/inspect_matrix.py "/path/to/authorized_data/matrix.csv" --diagonal-output "/path/to/local_outputs/diagonal_proxy.csv"
```

������� JSON ������նˣ�����������״��������ֵ�͸�ֵ�������ǶԽ���ֵ�������Լ��ǶԽǶ�Ӧλ�õ������ԶԳ�ƫ��Ƿ��󡢿��ļ����޷������� CSV��NaN������ֵ��ֵ�������˳��� `2`����Ч�Ǹ����󷵻� `0`���Գ�����ժҪ�е������棬�ǶԳƱ������ᵼ�¼�鹤�߷���ʧ�ܡ����߲����޸�ԭ����Ҳ���Ḳ���Ѵ��ڵĶԽ�����ļ���

�Խ� CSV �ֶ��� `node_index,gray_matter_probability_sum_proxy`��`node_index` �� 1 ��ʼ������������˳��һ�¡�

����Ҳ���������ߴ�ķ�����˷��� `0` ����ʾͼ���Ѿ�ȷ�ϡ���������Ŀ����ʱ��Ӧȷ��ժҪ�е� `shape` Ϊ `[268, 268]`����ʹ����þ������׵� Shen268 �ڵ����

## �� Python �ж�ȡ�������ⲿ�ڵ��

�ڵ�ӳ������湫���ֿ��ṩ��Ӧ�ӻ���Ȩ�����ݽ�����ȡ�á�����ʾ����ʽָ������ͽڵ�����ⲿ·�����������ʴ�������ȡ�öԽ�������Ľṹ����

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
# structural[i, j] ��ͼ�ױ�ǩ�ֱ��� nodes[i] �� nodes[j] �� atlas_label ȡ�á�
```

ʾ��ֻ���ڴ��д������飬����д�����ļ���Ҳ�����ؽڵ�ӳ�䡣�ڵ��Ӧ���� `matrix_index_0based`��`atlas_label` �� `is_cortex`���ֶκ���Ͱ汾Ӧ����������˵��Ϊ׼��

## �����������߱�

������ʽѡ�� `--direction`������ʾ������ÿ������ǶԽǾ���λ�ã�`A[i,j]` д�ɴӽڵ� `i+1` �� `j+1` ��һ�У�

```bash
python scripts/matrix_to_edges.py "/path/to/authorized_data/matrix.csv" "/path/to/local_outputs/regional_edges.csv" --direction directed
```

����� `directed` �Ǳ߱��ļ�¼��ʽ��**������ DWI �������ṩ��֤ʵ����ѧ���ӷ���**�����ԭ����Գƣ��������򶼻������������Ȩ�ػ����ͳ��ʱӦ������һ�㡣

�������������������Ϊ���򣬲��Ҿ���ͨ���Գ��Լ�飬��ʹ�ã�

```bash
python scripts/matrix_to_edges.py "/path/to/authorized_data/matrix.csv" "/path/to/local_outputs/regional_edges_undirected.csv" --direction undirected
```

���򵼳�Ĭ��Ҫ��ǶԽ�Ԫ���ϸ�Գƣ�ֻ��ȡ������ `i < j`��ÿ�Խڵ����һ�Σ���ƽ������Ȩ�ء���ȷ�ϲ���ֻ�ǿɽ��ܵ���ֵ��������ʽָ�������ݲ���� `--symmetry-atol 1e-8`���ݲ���޸�����������ֻ����Ӧ����ֵ�ľ��Բ��Ƿ����ݲ��ڣ�**����������ǵ�ԭֵ����һ����ֵ��д��߱�**�������÷ſ��ݲ����ڸ���Դ�����Ĳ��Գơ�

��� CSV �������ֶΣ�

| �ֶ� | ���� |
| --- | --- |
| `source_node` | ������λ�ã��� 1 ��ʼ |
| `target_node` | ������λ�ã��� 1 ��ʼ |
| `weight` | ��Ӧ�ǶԽ�Ԫ��ԭֵ |

�ڵ������ⲿ�ڵ���е� `matrix_index_0based` �� `source_node - 1` �� `target_node - 1` ���룬�ٶ�ȡ `atlas_label` �� `is_cortex`����Ҫ��ƾ���Ƽ��� `atlas_label` ��߱��Ľڵ�����ͬ�������ű�����ȡ�ڵ�ӳ�����Ҳ���Զ����ڵ����滻Ϊͼ�ױ�ǩ��

Ĭ��ʡ����Ȩ��λ�ã����� `--include-zero` ���Ա�����Ȩ��λ�ã��Խ���Ȼ�ų�������������ֵ��������һ������ȡ����ֵ��Ҳ����������Ϊ��������ֵ�� float64 ��ȡ������� 17 λ��Ч����д�����Ա������������ֵ���ȣ�CSV ��ԭʼ�ı���ʾ���ܱ仯��

���·�����벻���ڣ���Ŀ¼�����Ѵ��ڡ���֤ʧ��ʱ���ᴴ������ļ����������ʱ�᷵���˳��� `2` ������ԭ�ļ������������ʹ��ͬһ·��Ҳ�ᱻ�ܾ����ɹ����� `0`���뽫�����߱��ͶԽǴ��������������Լ����ⲿ����Ŀ¼��

## ���кϳ����ݲ���

```bash
python -m unittest discover -s tests -v
```

���Ծ����ɲ��Դ���������ʱ���ɣ���ʱ�ļ�����Խ������������Բ���Ҫ���������ݻ�ڵ�ӳ�䣬���ǶԽ��ų�������ѡ�񡢷ǶԳƾ��󡢷�����ֵ����ֵ����Ȩ�ء��ݲ�ջ򲻹��� CSV���Լ������ļ�������
