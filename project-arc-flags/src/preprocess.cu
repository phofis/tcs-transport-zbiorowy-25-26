#include "utils.hpp"

#include <cuda_runtime.h>

#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <math_constants.h>
#include "utils.hpp"

namespace arcflags {
namespace {

void CheckCuda(cudaError_t error, const char* what) {
  if (error != cudaSuccess) {
    throw std::runtime_error(std::string(what) + ": " + cudaGetErrorString(error));
  }
}

std::vector<uint32_t> findBoundaryVertices(const GraphData& graph,
                                           const GraphData& graph_r,
                                           const PartitionData& partition,
                                           std::vector<uint32_t>& boundary_offsets) {
  const uint32_t regions_count = partition.regions_count;
  boundary_offsets.assign(regions_count + 1, 0);

  std::vector<uint32_t> boundary_vertices;
  std::vector<uint32_t> boundary_regions;
  boundary_vertices.reserve(graph.n / 10 + 1);
  boundary_regions.reserve(graph.n / 10 + 1);

  for (uint32_t v = 0; v < graph.n; ++v) {
    const uint32_t region = partition.region[v];
    bool is_boundary = false;

    for (uint32_t e = graph.offsets[v]; e < graph.offsets[v + 1]; ++e) {
      if (partition.region[graph.to[e]] != region) {
        is_boundary = true;
        break;
      }
    }

    if (!is_boundary) {
      for (uint32_t e = graph_r.offsets[v]; e < graph_r.offsets[v + 1]; ++e) {
        if (partition.region[graph_r.to[e]] != region) {
          is_boundary = true;
          break;
        }
      }
    }

    if (is_boundary) {
      boundary_vertices.push_back(v);
      boundary_regions.push_back(region);
      ++boundary_offsets[region + 1];
    }
  }

  for (uint32_t r = 1; r <= regions_count; ++r) {
    boundary_offsets[r] += boundary_offsets[r - 1];
  }

  std::vector<uint32_t> packed(boundary_offsets[regions_count]);
  std::vector<uint32_t> cursor = boundary_offsets;
  for (std::size_t i = 0; i < boundary_vertices.size(); ++i) {
    const uint32_t v = boundary_vertices[i];
    const uint32_t region = boundary_regions[i];
    packed[cursor[region]++] = v;
  }

  return packed;
}

GraphData reverseGraph(const GraphData& graph, std::vector<uint32_t>& rev_edge_id) {
  GraphData reversed;
  reversed.n = graph.n;
  reversed.m = graph.m;
  reversed.offsets.assign(graph.n + 1, 0);
  reversed.to.resize(graph.m);
  reversed.length.resize(graph.m);
  rev_edge_id.resize(graph.m);

  for (uint32_t v = 0; v < graph.n; ++v) {
    for (uint32_t e = graph.offsets[v]; e < graph.offsets[v + 1]; ++e) {
      ++reversed.offsets[graph.to[e] + 1];
    }
  }

  for (uint32_t v = 1; v <= graph.n; ++v) {
    reversed.offsets[v] += reversed.offsets[v - 1];
  }

  std::vector<uint32_t> cursor = reversed.offsets;
  for (uint32_t v = 0; v < graph.n; ++v) {
    for (uint32_t e = graph.offsets[v]; e < graph.offsets[v + 1]; ++e) {
      const uint32_t to = graph.to[e];
      const uint32_t pos = cursor[to]++;
      reversed.to[pos] = v;
      reversed.length[pos] = graph.length[e];
      rev_edge_id[pos] = e;
    }
  }

  return reversed;
}

void set_flag(std::vector<uint32_t>& arc_flags, uint32_t edge_id, uint32_t region, uint32_t region_count) {
  const uint32_t words_per_edge = (region_count + 31) / 32;
  const uint32_t word = region >> 5;
  const uint32_t bit = region & 31u;
  arc_flags[edge_id * words_per_edge + word] |= (1u << (31u - bit));
}

__global__ void reverseDijkstraKernel(const uint32_t* offsets,
                                      const uint32_t* to,
                                      const float* length,
                                      uint32_t n,
                                      uint32_t source,
                                      float* dist,
                                      unsigned char* visited) {
  if (blockIdx.x != 0 || threadIdx.x != 0) {
    return;
  }

  const float INF = CUDART_INF_F;
  for (uint32_t v = 0; v < n; ++v) {
    dist[v] = INF;
    visited[v] = 0;
  }

  dist[source] = 0.0f;

  for (uint32_t iter = 0; iter < n; ++iter) {
    uint32_t best_v = n;
    float best_dist = INF;

    for (uint32_t v = 0; v < n; ++v) {
      if (!visited[v] && dist[v] < best_dist) {
        best_dist = dist[v];
        best_v = v;
      }
    }

    if (best_v == n || best_dist == INF) {
      break;
    }

    visited[best_v] = 1;

    for (uint32_t e = offsets[best_v]; e < offsets[best_v + 1]; ++e) {
      const uint32_t next = to[e];
      const float candidate = best_dist + length[e];
      if (candidate < dist[next]) {
        dist[next] = candidate;
      }
    }
  }
}

__global__ void markFlagsKernel(const uint32_t* offsets,
                                const uint32_t* to,
                                const float* length,
                                const uint32_t* rev_edge_id,
                                const float* dist,
                                uint32_t n,
                                uint32_t region,
                                uint32_t region_count,
                                uint32_t* arc_flags) {
  if (blockIdx.x != 0 || threadIdx.x != 0) {
    return;
  }

  const uint32_t words_per_edge = (region_count + 31) / 32;
  const uint32_t word = region >> 5;
  const uint32_t mask = 1u << (31u - (region & 31u));
  const float eps = 1e-6f;

  for (uint32_t v = 0; v < n; ++v) {
    if (isinf(dist[v])) {
      continue;
    }

    for (uint32_t e = offsets[v]; e < offsets[v + 1]; ++e) {
      const uint32_t next = to[e];
      if (isinf(dist[next])) {
        continue;
      }

      const float candidate = dist[v] + length[e];
      if (fabsf(dist[next] - candidate) <= eps) {
        const uint32_t original_edge = rev_edge_id[e];
        arc_flags[original_edge * words_per_edge + word] |= mask;
      }
    }
  }
}

std::vector<uint32_t> arcFlagsPreprocessingCuda(const GraphData& graph, const PartitionData& partition) {
  const uint32_t n = graph.n;
  const uint32_t m = graph.m;
  const uint32_t regions_count = partition.regions_count;
  const uint32_t words_per_edge = (regions_count + 31) / 32;

  std::vector<uint32_t> arc_flags(m * words_per_edge, 0);
  for (uint32_t e = 0; e < m; ++e) {
    set_flag(arc_flags, e, partition.region[graph.to[e]], regions_count);
  }

  std::vector<uint32_t> rev_edge_id;
  GraphData graph_r = reverseGraph(graph, rev_edge_id);

  std::vector<uint32_t> boundary_offsets;
  std::vector<uint32_t> boundary_vertices = findBoundaryVertices(graph, graph_r, partition, boundary_offsets);

  uint32_t* d_offsets = nullptr;
  uint32_t* d_to = nullptr;
  float* d_length = nullptr;
  uint32_t* d_rev_edge_id = nullptr;
  float* d_dist = nullptr;
  unsigned char* d_visited = nullptr;
  uint32_t* d_arc_flags = nullptr;

  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_offsets), graph_r.offsets.size() * sizeof(uint32_t)), "cudaMalloc offsets");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_to), graph_r.to.size() * sizeof(uint32_t)), "cudaMalloc to");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_length), graph_r.length.size() * sizeof(float)), "cudaMalloc length");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_rev_edge_id), rev_edge_id.size() * sizeof(uint32_t)), "cudaMalloc rev_edge_id");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_dist), n * sizeof(float)), "cudaMalloc dist");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_visited), n * sizeof(unsigned char)), "cudaMalloc visited");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_arc_flags), arc_flags.size() * sizeof(uint32_t)), "cudaMalloc arc_flags");

  CheckCuda(cudaMemcpy(d_offsets, graph_r.offsets.data(), graph_r.offsets.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
            "cudaMemcpy offsets");
  CheckCuda(cudaMemcpy(d_to, graph_r.to.data(), graph_r.to.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
            "cudaMemcpy to");
  CheckCuda(cudaMemcpy(d_length, graph_r.length.data(), graph_r.length.size() * sizeof(float), cudaMemcpyHostToDevice),
            "cudaMemcpy length");
  CheckCuda(cudaMemcpy(d_rev_edge_id, rev_edge_id.data(), rev_edge_id.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
            "cudaMemcpy rev_edge_id");
  CheckCuda(cudaMemcpy(d_arc_flags, arc_flags.data(), arc_flags.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
            "cudaMemcpy arc_flags");

  for (uint32_t source : boundary_vertices) {
    const uint32_t region = partition.region[source];

    reverseDijkstraKernel<<<1, 1>>>(d_offsets, d_to, d_length, n, source, d_dist, d_visited);
    CheckCuda(cudaGetLastError(), "reverseDijkstraKernel launch");
    CheckCuda(cudaDeviceSynchronize(), "reverseDijkstraKernel sync");

    markFlagsKernel<<<1, 1>>>(d_offsets, d_to, d_length, d_rev_edge_id, d_dist, n, region, regions_count, d_arc_flags);
    CheckCuda(cudaGetLastError(), "markFlagsKernel launch");
    CheckCuda(cudaDeviceSynchronize(), "markFlagsKernel sync");
  }

  CheckCuda(cudaMemcpy(arc_flags.data(), d_arc_flags, arc_flags.size() * sizeof(uint32_t), cudaMemcpyDeviceToHost),
            "cudaMemcpy arc_flags back");

  cudaFree(d_offsets);
  cudaFree(d_to);
  cudaFree(d_length);
  cudaFree(d_rev_edge_id);
  cudaFree(d_dist);
  cudaFree(d_visited);
  cudaFree(d_arc_flags);

  return arc_flags;
}

}  // namespace
}  // namespace arcflags

int main(int argc, char** argv) {
  try {
    const arcflags::CliOptions options = arcflags::ParseCliArgs(argc, argv);

    if (options.partition_path.empty()) {
      throw std::runtime_error("Missing required --partition");
    }

    const arcflags::GraphData graph = arcflags::ReadGraph(options);
    const arcflags::PartitionData partition = arcflags::ReadPartition(options, graph.n);
    const std::vector<uint32_t> arc_flags = arcflags::arcFlagsPreprocessingCuda(graph, partition);

    const std::filesystem::path out_path(options.output_path);
    if (out_path.has_parent_path()) {
      std::filesystem::create_directories(out_path.parent_path());
    }

    std::ofstream output(out_path, options.format == arcflags::Encoding::kBin ? std::ios::binary : std::ios::out);
    if (!output) {
      throw std::runtime_error("Cannot open output file: " + options.output_path);
    }

    if (options.format == arcflags::Encoding::kTxt) {
      arcflags::WriteTextVector(output, arc_flags);
    } else {
      arcflags::WriteBinaryVector(output, arc_flags);
    }

    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "preprocess_cuda: " << ex.what() << '\n';
    return 1;
  }
}
