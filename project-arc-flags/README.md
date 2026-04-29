# Arc-flags shortest paths

Educational implementation of **arc-flags** preprocessing for fast **point-to-point** shortest-path queries, following *Fast Point-to-Point Shortest Path Computations with Arc-Flags* (Hilger, Köhler, Möhring, Schilling, 2006).

## Makefile quick usage

From `project-arc-flags/`:

```bash
# Build partition binary (defaults: METIS in /usr/local, R=64)
make partition

# Build partition binary with custom METIS install prefix
make partition METIS_PREFIX=$HOME/local

# Main pipeline entrypoint (requires only graph + queries)
make run GRAPH_IN=graph.bin QUERIES_IN=queries.txt METIS_PREFIX=$HOME/local

# Run partition stage explicitly on binary graph input
make partition-bin GRAPH_IN=graph.bin METIS_PREFIX=$HOME/local
# writes: partition/partition.graph.bin

# Run partition stage explicitly on text graph input
make partition-txt GRAPH_IN=graph.txt METIS_PREFIX=$HOME/local
# writes: partition/partition.graph.txt
```

Key Makefile variables:
- `METIS_PREFIX` path containing `include/metis.h` and `lib/libmetis.so`
- `GRAPH_IN` input graph file produced by `osm2txt`
- `QUERIES_IN` query file for the final stage input
- `PARTITION_DIR` default `partition`
- `FLAGS_DIR` default `flags`
- `OUT_DIR` default `out`
- `REGION_COUNT` compile-time region count for partitioning (`R`)
- `PARTITION_SEED` compile-time METIS seed for reproducibility

Default folder layout:
- `partition/` — partition stage outputs
- `flags/` — preprocess stage outputs
- `out/` — final query outputs

## Data

Road graphs as `.osm.pbf` from [Geofabrik](https://download.geofabrik.de/) (OpenStreetMap, ODbL). This project does not redistribute map data.

## Programs

1. **osm2txt** (Python, `pyosmium`) — Reads `.osm.pbf`, extracts a simplified directed road graph, writes `N, M, offsets, to, length` in `.txt` or `.bin`.
2. **partition** - Partitions the graph for further processing(**C++**), writes  `.txt`.
3. **preprocess** — Computes arc-flags labels on a graph. Two builds: **plain C++** and **CUDA C++**, same output format, for runtime comparison. Writes a preprocessed `.txt`.
4. **query** — Loads the preprocessed graph and answers batches of `(source, target)` pairs (stdin or file; TBD).

## Format

Pipeline files are **incremental**:
- each stage writes only the new data produced by that stage
- downstream stages read multiple input files (`osm2txt` base graph + stage-specific label files)

Vertex and edge IDs are `0..N-1` and `0..M-1` with respect to the base graph from `osm2txt`.

### 1) `osm2txt` output

Header:
- `N` (`uint32`) - number of vertices
- `M` (`uint32`) - number of edges

Tables:
1. `offsets` (`uint32[N]`) - CSR-like prefix starts of outgoing edges per vertex.  
   `offsets[i]` is the first index in `to[]` for vertex `i`.
2. `to` (`uint32[M]`) - destination vertex for each edge.  
   Edges are grouped by source vertex: first `k0` edges for vertex `0`, then `k1` for vertex `1`, etc.
3. `length` (`float32[M]`) - real-world edge length for each edge in `to[]`.

Notes:
- For `i < N-1`: `k_i = offsets[i+1] - offsets[i]`
- For `i = N-1`: `k_i = M - offsets[N-1]`

### 2) `partition` output

- `R` (`uint32`) - number of regions (constant configured in partition source)
- `region` (`uint32[N]`) - region ID for each vertex (`0..R-1`)

### 3) `preprocess` output

- `arcFlags` (`uint32[M * ceil(R/32)]`) - arc-flags bitset per edge.  
  Each bit is one region flag, starting from the most significant bit in each `uint32`.

If `R` is not divisible by 32, unused bits are left as padding.

### 4) Query input

`query` reads:
1. base graph file (from `osm2txt`)
2. partition labels file (from `partition`)
3. arc-flags file (from `preprocess`)
4. query file with `Q` pairs `(s, t)` (source, target)

#### Structure
1. First line: `Q` (`uint32`) - number of queries.
2. Next `Q` lines: two vertex IDs per line:
   - `s t`
   - where `s` is source and `t` is target
Vertex IDs are 0-based and must satisfy:
- `0 <= s < N`
- `0 <= t < N`
#### Example
```txt
5
0 10
12 44
7 7
100 230
15 2
```

## Encodings

Each stage (`osm2txt`, `partition`, `preprocess`) supports two encodings:

- **Binary (`.bin`)** - default for performance
- **Text (`.txt`)** - human-readable debug/export format

Use CLI flag:
- `--format bin` or `--format txt`

Binary rules:
- fixed-width types: `uint32`, `float32`
- little-endian
- tables are written in the exact order defined below for each stage

## CLI conventions

All programs use explicit paths and a selectable encoding.

- `--in <path>` primary input file
- `--out <path>` output file
- `--format bin|txt` output encoding (`bin` default)

Downstream tools can take additional stage files as separate inputs (for example partition labels and arc-flags labels).

### File naming convention

Generated pipeline artifacts should follow:

- `program.sourceName.format`

Examples:
- `partition/partition.malo.bin`
- `partition/partition.malo.txt`
- `flags/preprocess.malo.bin`
- `out/query.malo.txt`

```bash
python3 osm2txt.py --in poland-latest.osm.pbf --out graph.bin --format bin
python3 osm2txt.py --in poland-latest.osm.pbf --out graph.txt --format txt
partition --in graph.bin --out partition.graph.bin --format bin
partition --in graph.txt --out partition.graph.txt --format txt
preprocess --graph graph.bin --partition partition.graph.bin --out preprocess.graph.bin --format bin
preprocess_cuda --graph graph.bin --partition partition.graph.bin --out preprocess_cuda.graph.bin --format bin
preprocess --graph graph.txt --partition partition.graph.txt --out preprocess.graph.txt --format txt
query --graph graph.bin --partition partition.graph.bin --flags preprocess.graph.bin --queries queries.txt --format bin
query --graph graph.txt --partition partition.graph.txt --flags preprocess.graph.txt --queries queries.txt --format txt
```

### `osm2txt.py` specific options

Install dependency:

```bash
python3 -m pip install osmium
```

Large-file cache backend (for node locations used in edge length computation):

- `--location-cache ram|disk` (`ram` default)
- `--location-index sparse|dense` (when cache is `disk`)
- `--location-cache-file <path>` optional on-disk cache file path

Examples:

```bash
# RAM-backed location cache (default)
python3 osm2txt.py --in poland-latest.osm.pbf --out graph.bin --format bin

# Disk-backed sparse location cache with explicit cache file
python3 osm2txt.py --in poland-latest.osm.pbf --out graph.bin --format bin \
  --location-cache disk --location-index sparse \
  --location-cache-file /tmp/osm2txt-location.store

# Text output with custom length precision
python3 osm2txt.py --in poland-latest.osm.pbf --out graph.txt --format txt --precision 4
```

## Build

GCC C++, CUDA toolkit, Make

### Install METIS (from GitHub source)

`partition` uses the METIS C library. A straightforward way is to build and install METIS (and GKlib) into a local prefix, then point this project Makefile to that prefix.

1. Install build dependencies (Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git
```

2. Build and install GKlib:

```bash
git clone https://github.com/KarypisLab/GKlib.git
cd GKlib
make config prefix=$HOME/local
make install
```

3. Build and install METIS:

```bash
git clone https://github.com/KarypisLab/METIS.git
cd METIS
make config shared=1 cc=gcc prefix=$HOME/local gklib_path=$HOME/local
make install
```

This installs artifacts to:

- `$HOME/local/include` (headers, including `metis.h`)
- `$HOME/local/lib` (library, e.g. `libmetis.so`)
- `$HOME/local/bin` (METIS tools)

4. Use these paths when compiling `partition`:

```bash
make METIS_PREFIX=$HOME/local
```

If your Makefile does not yet expose `METIS_PREFIX`, pass equivalent flags explicitly:

- include path: `-I$HOME/local/include`
- library path: `-L$HOME/local/lib`
- link: `-lmetis`

Reference: [KarypisLab/METIS](https://github.com/KarypisLab/METIS/tree/master)
