"""Generate neuron-level DTB NPZ blocks from a BrainProject407 Shen268 CSV."""

import argparse
import csv
import json
from pathlib import Path
import tempfile

import numpy as np


PROPERTY = np.array([
    0, 0, 0, 0, 1, 5, .03, -75, -50, -65,
    .008, .008, .0015, 0, 0, 0, -70, -100, 2, 2, 10, 50,
], dtype=np.float32)


def population_model(matrix, neurons):
    grey = np.diag(matrix).copy()
    structural = matrix.copy()
    np.fill_diagonal(structural, 0)
    row_sum = structural.sum(axis=1, keepdims=True)
    regional = np.divide(structural, row_sum, out=np.zeros_like(structural),
                         where=row_sum > 0)
    regions = len(grey)
    probability = np.zeros((2 * regions, 2 * regions))
    for region in range(regions):
        probability[2 * region:2 * region + 2, ::2] = regional[region] * (2 / 7)
        probability[2 * region:2 * region + 2, 2 * region:2 * region + 2] = [4 / 7, 1 / 7]
    # An isolated region retains only its local E/I inputs, normalized to 0.8/0.2.
    probability /= probability.sum(axis=1, keepdims=True)
    fractions = (grey[:, None] / grey.sum() * [0.8, 0.2]).ravel()
    sizes = np.maximum(fractions * neurons, np.tile([200, 50], regions)).astype(np.int64)
    base = np.r_[0, np.cumsum(sizes)]
    return grey, structural, probability, sizes, base


def sample_sources(rng, source_population, targets, population, sizes, base):
    """Sample distinct source neurons per target, excluding self-connections."""
    degree = source_population.shape[1]
    ordered = np.sort(source_population, axis=1).ravel()
    starts = np.flatnonzero(np.r_[True, (ordered[1:] != ordered[:-1]) |
                                  (np.arange(1, ordered.size) % degree == 0)])
    available = sizes[ordered[starts]] - (ordered[starts] == population)
    if np.any(np.diff(np.r_[starts, ordered.size]) > available):
        raise ValueError("Sampled degree exceeds a source population; increase --neurons or lower --degree")

    def draw(source, target):
        same = source == population
        local = rng.integers(sizes[source] - same)
        local += same & (local >= target - base[population])
        return base[source] + local

    sources = draw(source_population, targets[:, None])
    while True:
        order = np.argsort(sources, axis=1, kind="stable")
        ordered_sources = np.take_along_axis(sources, order, axis=1)
        rows, columns = np.nonzero(ordered_sources[:, 1:] == ordered_sources[:, :-1])
        if not len(rows):
            return sources
        columns = order[rows, columns + 1]
        sources[rows, columns] = draw(source_population[rows, columns], targets[rows])


def write_block(output, block, threshold, sizes, base, probability, degree, seed):
    start, stop = map(int, threshold[block:block + 2])
    neurons, edges = stop - start, (stop - start) * degree
    specs = {
        "property": ((neurons, 22), "float32"),
        "output_neuron_idx": ((edges,), "uint32"),
        "input_block_idx": ((edges,), "int16"),
        "input_neuron_idx": ((edges,), "uint32"),
        "input_channel_offset": ((edges,), "uint8"),
        "weight": ((edges, 2), "uint8"),
    }
    rng = np.random.default_rng(np.random.SeedSequence([seed, block]))
    # Disk-backed arrays bound working memory; NPZ must use uncompressed storage.
    with tempfile.TemporaryDirectory(prefix=".build_", dir=output) as scratch:
        arrays = {name: np.lib.format.open_memmap(Path(scratch) / (name + ".npy"),
                  mode="w+", dtype=dtype, shape=shape) for name, (shape, dtype) in specs.items()}
        try:
            arrays["property"][:] = PROPERTY
            arrays["property"][:, 3] = np.searchsorted(base, np.arange(start, stop), side="right") - 1
            for population in range(len(sizes)):
                first, last = max(start, int(base[population])), min(stop, int(base[population + 1]))
                cumulative = np.cumsum(probability[population])
                cumulative[-1] = 1.0
                for left in range(first, last, 2048):
                    targets = np.arange(left, min(left + 2048, last))
                    shape = (len(targets), degree)
                    source_population = np.searchsorted(cumulative, rng.random(shape), side="right")
                    sources = sample_sources(rng, source_population, targets, population, sizes, base)
                    source_block = np.searchsorted(threshold, sources, side="right") - 1
                    order = np.argsort(source_block, axis=1, kind="stable")
                    source_block = np.take_along_axis(source_block, order, axis=1)
                    sources = np.take_along_axis(sources, order, axis=1)
                    source_population = np.take_along_axis(source_population, order, axis=1)
                    weights = rng.integers(0, 256, size=shape + (2,), dtype=np.uint8)
                    external = source_population // 2 != population // 2
                    weights[:, :, 1][external] = 0
                    weights[:, :, 0][~external & (source_population % 2 == 0)] = 0
                    section = slice((left - start) * degree, (left - start + len(targets)) * degree)
                    arrays["output_neuron_idx"][section] = np.repeat(targets - start, degree)
                    arrays["input_block_idx"][section] = (source_block - block).ravel()
                    arrays["input_neuron_idx"][section] = (sources - threshold[source_block]).ravel()
                    arrays["input_channel_offset"][section] = (2 * (source_population % 2)).ravel()
                    arrays["weight"][section] = weights.reshape(-1, 2)
            path = output / "module" / "uint8" / f"block_{block}.npz"
            np.savez(path, **arrays)
        finally:
            for array in arrays.values():
                array.flush()
                array._mmap.close()
    print(f"block {block}: {neurons:,} neurons, {edges:,} connections", flush=True)


def generate(args):
    matrix = np.loadtxt(args.input, delimiter=",", dtype=np.float64)
    if matrix.shape != (268, 268) or not np.isfinite(matrix).all() or (matrix < 0).any():
        raise ValueError("Input must be a finite, nonnegative 268 x 268 CSV")
    if (np.diag(matrix) <= 0).any() or min(args.neurons, args.degree, args.blocks) < 1 or args.seed < 0:
        raise ValueError("Positive diagonal, neurons, degree and blocks; nonnegative seed required")
    grey, structural, probability, sizes, base = population_model(matrix, args.neurons)
    total = int(base[-1])
    if not 1 <= args.blocks <= min(total, 32767) or total > np.iinfo(np.uint32).max:
        raise ValueError("Requested size exceeds DTB block/neuron index limits")
    block_sizes = np.full(args.blocks, total // args.blocks, dtype=np.int64)
    block_sizes[:total % args.blocks] += 1
    if int(block_sizes.max()) * max(args.degree, 22) > np.iinfo(np.uint32).max:
        raise ValueError("Block arrays exceed the DTB uint32 limit; increase --blocks")
    threshold = np.r_[0, np.cumsum(block_sizes)]

    nodes = None
    if args.nodes_metadata:
        with args.nodes_metadata.open(encoding="utf-8-sig", newline="") as stream:
            nodes = list(csv.DictReader(stream, delimiter="\t"))
        if [int(row["matrix_index_0based"]) for row in nodes] != list(range(268)):
            raise ValueError("Node metadata must follow the 268 matrix rows")
        labels = np.array([int(row["atlas_label"]) for row in nodes])
        cortex = np.array([int(row["is_cortex"]) if row["is_cortex"] in ("0", "1") else -1
                           for row in nodes], dtype=np.int8)

    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "module" / "uint8").mkdir(parents=True)
    supplementary = args.output / "supplementary_info"
    supplementary.mkdir()
    for name, value in {
        "population_sizes": sizes, "population_base": base, "block_threshold": threshold,
        "region_population_map": np.arange(536).reshape(268, 2), "csv_row_index": np.arange(268),
        "grey_matter_weights": grey, "structural_matrix": structural,
        "population_probability": probability, "degree_scale": np.ones(536),
        "isolated_csv_rows": np.flatnonzero(structural.sum(axis=1) == 0),
    }.items():
        np.save(supplementary / (name + ".npy"), value)
    if nodes is not None:
        (supplementary / "nodes_shen268.tsv").write_bytes(args.nodes_metadata.read_bytes())
        np.savez(supplementary / "atlas_region.npz", atlas_region=labels, uni_region=labels,
                 is_cortex=cortex, region_in_data=np.ones(268, dtype=bool), voxel_label=labels,
                 nonzero_all=np.arange(268))
    manifest = dict(generator="BrainProject407 csv_to_dtb", input=args.input.name,
                    requested_neurons=args.neurons, actual_neurons=total, regions=268,
                    populations=536, blocks=args.blocks, degree=args.degree, seed=args.seed,
                    weights_dtype="uint8", numpy_version=np.__version__,
                    node_metadata_supplied=nodes is not None, status="generating")
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for block in range(args.blocks):
        write_block(args.output, block, threshold, sizes, base, probability, args.degree, args.seed)
    manifest["status"] = "generated"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {total:,} neurons to {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    parser.add_argument("--neurons", type=int, default=2_000_000)
    parser.add_argument("--degree", type=int, default=100)
    parser.add_argument("--blocks", type=int, default=2)
    parser.add_argument("--seed", type=int, default=407)
    parser.add_argument("--nodes-metadata", type=Path, help="Optional external Shen268 node TSV")
    generate(parser.parse_args())
