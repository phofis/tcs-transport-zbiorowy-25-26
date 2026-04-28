#!/usr/bin/env python3
"""Convert OSM PBF roads into arc-flags graph format.

Output schema order:
1) N (uint32) number of vertices
2) M (uint32) number of directed edges
3) offsets (uint32[N])
4) to (uint32[M])
5) length (float32[M])
"""

from __future__ import annotations

import argparse
import math
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

import osmium


DRIVABLE_HIGHWAYS = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
    "road",
    "service",
}

ONEWAY_TRUE = {"yes", "true", "1"}
ONEWAY_FALSE = {"no", "false", "0"}


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters."""
    radius = 6371008.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2.0) ** 2)
    )
    return 2.0 * radius * math.asin(math.sqrt(a))


def is_drivable(way: osmium.osm.Way) -> bool:
    highway = way.tags.get("highway")
    if highway is None or highway not in DRIVABLE_HIGHWAYS:
        return False

    if way.tags.get("access") in {"no", "private"}:
        return False

    if way.tags.get("motor_vehicle") == "no":
        return False

    return True


@dataclass(frozen=True)
class Direction:
    forward: bool
    backward: bool


def parse_direction(way: osmium.osm.Way) -> Direction:
    raw = (way.tags.get("oneway") or "").strip().lower()
    if raw == "-1":
        return Direction(forward=False, backward=True)
    if raw in ONEWAY_TRUE:
        return Direction(forward=True, backward=False)
    if raw in ONEWAY_FALSE or raw == "":
        return Direction(forward=True, backward=True)
    return Direction(forward=True, backward=True)


class WaySelectionPass(osmium.SimpleHandler):
    """First pass: keep metadata for drivable ways and collect referenced nodes."""

    def __init__(self) -> None:
        super().__init__()
        self.nodes_used: Set[int] = set()
        self.way_directions: Dict[int, Direction] = {}

    def way(self, way: osmium.osm.Way) -> None:
        if not is_drivable(way):
            return
        if len(way.nodes) < 2:
            return

        self.way_directions[way.id] = parse_direction(way)
        for node_ref in way.nodes:
            self.nodes_used.add(node_ref.ref)


class EdgeBuildPass(osmium.SimpleHandler):
    """Second pass: build directed edges and compact vertex ids."""

    def __init__(self, nodes_used: Set[int], way_directions: Dict[int, Direction]) -> None:
        super().__init__()
        self.nodes_used = nodes_used
        self.way_directions = way_directions
        self.osm_node_to_vid: Dict[int, int] = {}
        self.next_vid = 0
        self.adjacency: Dict[int, List[Tuple[int, float]]] = {}

    def _vertex_id(self, osm_node_id: int) -> int:
        existing = self.osm_node_to_vid.get(osm_node_id)
        if existing is not None:
            return existing
        new_id = self.next_vid
        self.osm_node_to_vid[osm_node_id] = new_id
        self.next_vid += 1
        return new_id

    def _add_edge(self, src_osm: int, dst_osm: int, length: float) -> None:
        src = self._vertex_id(src_osm)
        dst = self._vertex_id(dst_osm)
        self.adjacency.setdefault(src, []).append((dst, length))

    def way(self, way: osmium.osm.Way) -> None:
        direction = self.way_directions.get(way.id)
        if direction is None:
            return

        node_refs = [n for n in way.nodes if n.ref in self.nodes_used and n.location.valid()]
        if len(node_refs) < 2:
            return

        for idx in range(len(node_refs) - 1):
            n1 = node_refs[idx]
            n2 = node_refs[idx + 1]
            length = haversine_meters(n1.lat, n1.lon, n2.lat, n2.lon)
            if direction.forward:
                self._add_edge(n1.ref, n2.ref, length)
            if direction.backward:
                self._add_edge(n2.ref, n1.ref, length)


def to_csr(adjacency: Dict[int, List[Tuple[int, float]]], n_vertices: int) -> Tuple[List[int], List[int], List[float]]:
    offsets: List[int] = [0] * n_vertices
    to: List[int] = []
    length: List[float] = []

    cursor = 0
    for src in range(n_vertices):
        offsets[src] = cursor
        edges = adjacency.get(src, [])
        for dst, dist in edges:
            to.append(dst)
            length.append(dist)
            cursor += 1
    return offsets, to, length


def write_text(path: Path, n: int, m: int, offsets: Sequence[int], to: Sequence[int], length: Sequence[float], precision: int) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"{n}\n")
        handle.write(f"{m}\n")
        handle.write(" ".join(map(str, offsets)) + "\n")
        handle.write(" ".join(map(str, to)) + "\n")
        fmt = f"{{:.{precision}f}}"
        handle.write(" ".join(fmt.format(value) for value in length) + "\n")


def write_bin(path: Path, n: int, m: int, offsets: Sequence[int], to: Sequence[int], length: Sequence[float]) -> None:
    with path.open("wb") as handle:
        handle.write(struct.pack("<II", n, m))
        handle.write(struct.pack(f"<{n}I", *offsets))
        handle.write(struct.pack(f"<{m}I", *to))
        handle.write(struct.pack(f"<{m}f", *length))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert OSM PBF to arc-flags graph arrays.")
    parser.add_argument("--in", dest="input_path", required=True, help="Input .osm.pbf path")
    parser.add_argument("--out", dest="output_path", required=True, help="Output graph path")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("bin", "txt"),
        default="bin",
        help="Output encoding (default: bin)",
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=3,
        help="Decimal precision for txt length values (default: 3)",
    )
    parser.add_argument(
        "--location-cache",
        choices=("ram", "disk"),
        default="ram",
        help="Node location cache backend for geometry processing",
    )
    parser.add_argument(
        "--location-index",
        choices=("sparse", "dense"),
        default="sparse",
        help="Disk cache index type when --location-cache=disk",
    )
    parser.add_argument(
        "--location-cache-file",
        default=None,
        help="Optional cache file path when --location-cache=disk",
    )
    return parser.parse_args()


def build_index_spec(args: argparse.Namespace) -> Tuple[str, tempfile.TemporaryDirectory[str] | None]:
    if args.location_cache == "ram":
        return "flex_mem", None

    if args.location_cache_file:
        cache_path = Path(args.location_cache_file)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if args.location_index == "dense":
            return f"dense_file_array,{cache_path}", None
        return f"sparse_file_array,{cache_path}", None

    temp_dir = tempfile.TemporaryDirectory(prefix="osm2txt-cache-")
    cache_path = Path(temp_dir.name) / "node-location.store"
    if args.location_index == "dense":
        return f"dense_file_array,{cache_path}", temp_dir
    return f"sparse_file_array,{cache_path}", temp_dir


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    select_pass = WaySelectionPass()
    select_pass.apply_file(str(input_path))

    idx_spec, temp_cache = build_index_spec(args)
    try:
        build_pass = EdgeBuildPass(select_pass.nodes_used, select_pass.way_directions)
        build_pass.apply_file(str(input_path), locations=True, idx=idx_spec)
    finally:
        if temp_cache is not None:
            temp_cache.cleanup()

    n = build_pass.next_vid
    offsets, to, length = to_csr(build_pass.adjacency, n)
    m = len(to)

    if args.output_format == "txt":
        write_text(output_path, n, m, offsets, to, length, args.precision)
    else:
        write_bin(output_path, n, m, offsets, to, length)


if __name__ == "__main__":
    main()
