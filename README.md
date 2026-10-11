# BrainProject407 DTB Connection Table Generator

This repository documents BrainProject407 and provides code to generate DTB neuron connection tables from CSV matrices. The submitted data cover 588 participants from 8 datasets, with one 268 x 268 Shen268 matrix per participant. Diagonal entries are regional size proxies based on summed T1w gray matter probabilities; off-diagonal entries are DWI streamline counts, with counts below 2 set to zero. Data are provided separately through the data submission service and are not stored in this repository.

| Submission directory | Source dataset | Participants | Version or selection record | Submitted participants |
| --- | --- | --- | --- | ---: |
| BP407-D001 | PD_ds005849 | Parkinson's disease DBS study sample | 2.0.1 | 12 |
| BP407-D002 | PPMI | Selected PD baseline sample | PD140 baseline selection | 50 |
| BP407-D003 | MDD_ds006731 | MDD study sample | 1.0.0 | 21 |
| BP407-D004 | Xiangya_Wang101 | Xiangya Wang MDD sample | authorized cluster copy | 101 |
| BP407-D005 | Dystonia_ds006395 | Dystonia study sample | 1.0.8 | 53 |
| BP407-D006 | SUDMEX_TMS (ds003037) | TMS study sample | 2.1.0 | 26 |
| BP407-D007 | UCLA_ds000030 | Selected UCLA CNP sample | Not recorded | 125 |
| BP407-D008 | HCP | Selected HCP sample | Not recorded | 200 |

## Repository contents

- `csv_to_dtb.py`: reads a matrix, allocates excitatory (E) and inhibitory (I) neurons, samples connections, and writes DTB NPZ files.
- `requirements.txt`: runtime dependency (NumPy only).

## Quick start

Requires Python 3.10 or later. Set the input path to a `__Shen268.csv` file in a submission directory and choose a new output directory.

```bash
git clone https://github.com/ZzSym/BrainProject407-DTB-Generator.git
cd BrainProject407-DTB-Generator
python -m pip install -r requirements.txt

python csv_to_dtb.py \
  --input /path/to/subject__Shen268.csv \
  --output /path/to/dtb_output \
  --neurons 2000000 --degree 100 --blocks 2
```

Neurons are allocated using the diagonal gray matter weights, with an E:I ratio of 4:1 and minimum counts of 200 E and 50 I neurons per region. Rounding and minimum counts may change the actual total. Each neuron samples inputs from local E, local I, and external E populations in a 4:1:2 ratio. External E inputs follow the structural matrix after removing the diagonal and normalizing each row. Isolated regions use only local E/I inputs, with probabilities of 0.8/0.2.

Outputs include `module/uint8/block_*.npz` for neuron properties and connections, `supplementary_info/` for region and E/I population mappings, neuron ranges, and block boundaries, and `manifest.json` for parameters and actual network size. With 2 million neurons and an in-degree of 100, the connection tables occupy approximately 2.8 GB. Generation also requires temporary disk space for one block.
