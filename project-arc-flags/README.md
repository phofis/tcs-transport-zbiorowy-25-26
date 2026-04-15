# Arc-flags shortest paths

Educational implementation of **arc-flags** preprocessing for fast **point-to-point** shortest-path queries, following *Fast Point-to-Point Shortest Path Computations with Arc-Flags* (Hilger, Köhler, Möhring, Schilling, 2006).

## Data

Road graphs as `.osm.pbf` from [Geofabrik](https://download.geofabrik.de/) (OpenStreetMap, ODbL). This project does not redistribute map data.

## Programs

1. **osm2txt** (C++) — Reads `.osm.pbf`, extracts a simplified directed road graph, writes a compact `.txt` format (edge list / adjacency; see source for schema).
2. **partition** - Partitions the graph for further processing(**C++**), writes  `.txt`.
3. **preprocess** — Computes arc-flags labels on a graph. Two builds: **plain C++** and **CUDA C++**, same output format, for runtime comparison. Writes a preprocessed `.txt`.
4. **query** — Loads the preprocessed graph and answers batches of `(source, target)` pairs (stdin or file; TBD).

## Format

All intermediate graph files are stored as arrays in this order. Vertex and edge IDs are `0..N-1` and `0..M-1`.

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

Contains everything from `osm2txt`, plus:
- `R` (`uint32`) - number of regions (constant configured in partition source)
- `region` (`uint32[N]`) - region ID for each vertex (`0..R-1`)

### 3) `preprocess` output

Contains everything from `partition`, plus:
- `arcFlags` (`uint32[M * ceil(R/32)]`) - arc-flags bitset per edge.  
  Each bit is one region flag, starting from the most significant bit in each `uint32`.

If `R` is not divisible by 32, unused bits are left as padding.

### 4) Query input

`query` reads:
1. preprocessed graph file (from `preprocess`)
2. query file with `Q` pairs `(s, t)` (source, target)

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

All programs use explicit input/output paths and a selectable encoding:

- `--in <path>` input file
- `--out <path>` output file
- `--format bin|txt` output encoding (`bin` default)

```bash
osm2txt --in poland-latest.osm.pbf --out graph.bin --format bin
osm2txt --in poland-latest.osm.pbf --out graph.txt --format txt
partition --in graph.bin --out partition.bin --format bin
partition --in graph.txt --out partition.txt --format txt
preprocess --in partition.bin --out preprocessed.bin --format bin
preprocess_cuda --in partition.bin --out preprocessed_cuda.bin --format bin
preprocess --in partition.txt --out preprocessed.txt --format txt
query --graph preprocessed.bin --queries queries.txt --format bin
query --graph preprocessed.txt --queries queries.txt --format txt
```

## Build

GCC C++, CUDA toolkit, Make
