#include "utils.hpp"

#include <metis.h>

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

#ifndef PARTITION_REGIONS
#define PARTITION_REGIONS 64
#endif

#ifndef PARTITION_SEED
#define PARTITION_SEED 42
#endif

namespace arcflags {
namespace {

void WritePartitionText(const std::string& path, const GraphData& graph, const uint32_t regions_count,
                        const std::vector<uint32_t>& regions) {
  std::ofstream output(path);
  if (!output) {
    throw std::runtime_error("Cannot open output file: " + path);
  }
  output << graph.n << '\n';
  output << graph.m << '\n';
  WriteTextVector(output, graph.offsets);
  WriteTextVector(output, graph.to);

  output << std::setprecision(9);
  WriteTextVector(output, graph.length);
  output << regions_count << '\n';
  WriteTextVector(output, regions);
}

void WritePartitionBinary(const std::string& path, const GraphData& graph, const uint32_t regions_count,
                          const std::vector<uint32_t>& regions) {
  std::ofstream output(path, std::ios::binary);
  if (!output) {
    throw std::runtime_error("Cannot open output file: " + path);
  }
  output.write(reinterpret_cast<const char*>(&graph.n), sizeof(uint32_t));
  output.write(reinterpret_cast<const char*>(&graph.m), sizeof(uint32_t));
  WriteBinaryVector(output, graph.offsets);
  WriteBinaryVector(output, graph.to);
  WriteBinaryVector(output, graph.length);
  output.write(reinterpret_cast<const char*>(&regions_count), sizeof(uint32_t));
  WriteBinaryVector(output, regions);
}

void WritePartition(const CliOptions& options, const GraphData& graph, const uint32_t regions_count,
                    const std::vector<uint32_t>& regions) {
  const std::filesystem::path out_path(options.output_path);
  if (out_path.has_parent_path()) {
    std::filesystem::create_directories(out_path.parent_path());
  }

  if (options.format == Encoding::kTxt) {
    WritePartitionText(options.output_path, graph, regions_count, regions);
  } else {
    WritePartitionBinary(options.output_path, graph, regions_count, regions);
  }
}

std::vector<uint32_t> ComputeRegionsWithMetis(const GraphData& graph, const uint32_t regions_count) {
  if (regions_count == 0) {
    throw std::runtime_error("PARTITION_REGIONS must be > 0.");
  }
  if (graph.n == 0) {
    return {};
  }

  if (graph.n > static_cast<uint32_t>(std::numeric_limits<idx_t>::max())) {
    throw std::runtime_error("Graph too large for this METIS idx_t width.");
  }

  std::vector<std::vector<idx_t>> undirected_neighbors(graph.n);
  std::unordered_set<uint64_t> seen_edges;
  seen_edges.reserve(static_cast<std::size_t>(graph.m));

  for (uint32_t src = 0; src < graph.n; ++src) {
    const uint32_t begin = graph.offsets[src];
    const uint32_t end = (src + 1 < graph.n) ? graph.offsets[src + 1] : graph.m;
    for (uint32_t edge_id = begin; edge_id < end; ++edge_id) {
      const uint32_t dst = graph.to[edge_id];
      if (src == dst) {
        continue;
      }
      const uint32_t a = std::min(src, dst);
      const uint32_t b = std::max(src, dst);
      const uint64_t key = (static_cast<uint64_t>(a) << 32u) | static_cast<uint64_t>(b);
      if (!seen_edges.insert(key).second) {
        continue;
      }
      undirected_neighbors[a].push_back(static_cast<idx_t>(b));
      undirected_neighbors[b].push_back(static_cast<idx_t>(a));
    }
  }

  std::vector<uint32_t> regions(graph.n, 0);
  std::size_t total_adjacency = 0;
  for (const auto& nbrs : undirected_neighbors) {
    total_adjacency += nbrs.size();
  }
  if (total_adjacency == 0) {
    for (uint32_t i = 0; i < graph.n; ++i) {
      regions[i] = i % regions_count;
    }
    return regions;
  }

  std::vector<idx_t> xadj(graph.n + 1, 0);
  std::vector<idx_t> adjncy;
  adjncy.reserve(total_adjacency);
  idx_t cursor = 0;
  for (uint32_t v = 0; v < graph.n; ++v) {
    xadj[v] = cursor;
    for (const idx_t to : undirected_neighbors[v]) {
      adjncy.push_back(to);
      ++cursor;
    }
  }
  xadj[graph.n] = cursor;

  const uint32_t effective_parts = std::min(regions_count, graph.n);
  idx_t nvtxs = static_cast<idx_t>(graph.n);
  idx_t ncon = 1;
  idx_t nparts = static_cast<idx_t>(effective_parts);
  idx_t objval = 0;
  std::vector<idx_t> part(graph.n, 0);
  idx_t options[METIS_NOPTIONS];
  METIS_SetDefaultOptions(options);
  options[METIS_OPTION_NUMBERING] = 0;
  options[METIS_OPTION_SEED] = PARTITION_SEED;

  const int status =
      METIS_PartGraphKway(&nvtxs, &ncon, xadj.data(), adjncy.data(), nullptr, nullptr, nullptr, &nparts, nullptr,
                          nullptr, options, &objval, part.data());
  if (status != METIS_OK) {
    throw std::runtime_error("METIS_PartGraphKway failed with status " + std::to_string(status));
  }

  for (uint32_t i = 0; i < graph.n; ++i) {
    const idx_t value = part[i];
    if (value < 0 || value >= nparts) {
      throw std::runtime_error("METIS produced an out-of-range partition id.");
    }
    regions[i] = static_cast<uint32_t>(value);
  }
  return regions;
}

}  // namespace
}  // namespace arcflags

int main(int argc, char** argv) {
  try {
    for (int i = 1; i < argc; ++i) {
      const std::string arg = argv[i];
      if (arg == "--help" || arg == "-h") {
        std::cout << arcflags::UsageText() << '\n';
        return 0;
      }
    }
    const arcflags::CliOptions options = arcflags::ParseCliArgs(argc, argv);
    const arcflags::GraphData graph = arcflags::ReadGraph(options);
    const uint32_t regions_count = static_cast<uint32_t>(PARTITION_REGIONS);
    const std::vector<uint32_t> regions = arcflags::ComputeRegionsWithMetis(graph, regions_count);
    arcflags::WritePartition(options, graph, regions_count, regions);
    std::cerr << "partition: wrote " << graph.n << " vertices, " << graph.m << " edges, R=" << regions_count
              << " in " << arcflags::EncodingName(options.format) << " format\n";
    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "partition: " << ex.what() << '\n';
    return 1;
  }
}
