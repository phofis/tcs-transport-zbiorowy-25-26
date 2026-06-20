#include "utils.hpp"

#include <cuda_runtime.h>

#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
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

struct RelaxUpdate {
  uint32_t vertex;
  uint32_t bucket;
};

struct GPUDeltaSteppingState {
  uint32_t* frontier_queue;
  uint32_t* frontier_tail;
  uint32_t current_bucket;
  uint32_t max_bucket;
  bool finished;
};

__device__ float atomicMinFloat(float* address, float value) {
  int* address_as_int = reinterpret_cast<int*>(address);
  int old = *address_as_int;

  while (__int_as_float(old) > value) {
    const int assumed = old;
    old = atomicCAS(address_as_int, assumed, __float_as_int(value));
    if (old == assumed) {
      break;
    }
  }

  return __int_as_float(old);
}

__global__ void initSingleSourceKernel(float* dist, uint32_t n, uint32_t source) {
  const uint32_t v = blockIdx.x * blockDim.x + threadIdx.x;
  if (v >= n) {
    return;
  }

  dist[v] = CUDART_INF_F;
  if (v == source) {
    dist[v] = 0.0f;
  }
}

__global__ void deltaSteppingPersistentKernel(
    const uint32_t* rev_offsets,
    const uint32_t* rev_to,
    const float* rev_length,
    uint32_t n,
    uint32_t source,
    float delta,
    float* dist,
    uint32_t* frontier_queue,
    uint32_t* frontier_tail,
    uint32_t queue_capacity,
    bool* d_finished) {
  const uint32_t thread_id = threadIdx.x;
  __shared__ uint32_t shared_bucket;
  __shared__ uint32_t shared_queue_start;
  __shared__ uint32_t shared_queue_end;
  __shared__ bool shared_finished;

  if (thread_id == 0) {
    shared_bucket = 0;
    shared_queue_start = 1;
    shared_queue_end = 1;
    shared_finished = false;
  }
  __syncthreads();

  while (!shared_finished) {
    __syncthreads();

    const uint32_t queue_start = shared_queue_start;
    const uint32_t queue_end = shared_queue_end;

    if (queue_start < queue_end) {
      for (uint32_t idx = queue_start + thread_id; idx < queue_end; idx += blockDim.x) {
        if (idx >= queue_capacity) continue;
        
        const uint32_t u = frontier_queue[idx];
        if (u >= n) continue;
        
        const float du = dist[u];
        if (!isfinite(du)) continue;

        for (uint32_t e = rev_offsets[u]; e < rev_offsets[u + 1]; ++e) {
          const float w = rev_length[e];
          if (w > delta) continue;

          const uint32_t v = rev_to[e];
          if (v >= n) continue;
          
          const float candidate = du + w;
          const float previous = atomicMinFloat(&dist[v], candidate);
          if (candidate < previous) {
            const uint32_t next_bucket = static_cast<uint32_t>(floorf(candidate / delta));
            if (next_bucket == shared_bucket) {
              const uint32_t slot = atomicAdd(frontier_tail, 1u);
              if (slot < queue_capacity) {
                frontier_queue[slot] = v;
              }
            }
          }
        }
      }
    }

    __syncthreads();

    if (thread_id == 0) {
      const uint32_t new_queue_end = *frontier_tail;
      if (new_queue_end == queue_end) {
        shared_finished = true;
        *d_finished = true;
      } else {
        shared_bucket++;
        shared_queue_start = queue_end;
        shared_queue_end = new_queue_end;
      }
    }
    __syncthreads();
  }
}

__global__ void markFlagsKernel(
    const uint32_t* rev_edge_id,
    const uint32_t* to,
    const uint32_t* rev_to,
    const float* rev_length,
    const float* dist,
    uint32_t m,
    uint32_t region,
    uint32_t region_count,
    uint32_t* arc_flags
) {
    uint32_t rev_e = blockIdx.x * blockDim.x + threadIdx.x;
    if (rev_e >= m) return;

    uint32_t e = rev_edge_id[rev_e];

    uint32_t u = to[e];
    uint32_t v = rev_to[rev_e];

    float w = rev_length[rev_e];

    float du = dist[u];
    float dv = dist[v];

    if (!isfinite(du) || !isfinite(dv)) return;

    float candidate = du + w;
    const float eps = (1e-7f * fabsf(candidate) > 1e-6f) ? (1e-7f * fabsf(candidate)) : 1e-6f;

    if (fabsf(dv - candidate) <= eps) {
        uint32_t words_per_edge = (region_count + 31) / 32;
        uint32_t word = region >> 5;
        uint32_t mask = 1u << (31u - (region & 31u));

        atomicOr(&arc_flags[e * words_per_edge + word], mask);
    }
}


std::vector<uint32_t> arcFlagsPreprocessingCuda(const GraphData& graph, const PartitionData& partition) {
  const uint32_t n = graph.n;
  const uint32_t m = graph.m;
  const uint32_t regions_count = partition.regions_count;
  const uint32_t words_per_edge = (regions_count + 31) / 32;
  constexpr float delta = 5.0f;

  std::vector<uint32_t> arc_flags(m * words_per_edge, 0);
  for (uint32_t e = 0; e < m; ++e) {
    set_flag(arc_flags, e, partition.region[graph.to[e]], regions_count);
  }

  std::vector<uint32_t> rev_edge_id;
  GraphData graph_r = reverseGraph(graph, rev_edge_id);

  std::vector<uint32_t> boundary_offsets;
  std::vector<uint32_t> boundary_vertices = findBoundaryVertices(graph, graph_r, partition, boundary_offsets);

  uint32_t* d_rev_offsets = nullptr;
  
  uint32_t* d_rev_to = nullptr;
  float* d_rev_length = nullptr;
  uint32_t* d_rev_edge_id = nullptr;
  uint32_t* d_to = nullptr;
  float* d_dist = nullptr;
  RelaxUpdate* d_updates = nullptr;
  uint32_t* d_update_count = nullptr;
  uint32_t* d_frontier = nullptr;
  uint32_t* d_frontier_queue = nullptr;
  uint32_t* d_frontier_tail = nullptr;
  bool* d_finished = nullptr;
  uint32_t* d_arc_flags = nullptr;

  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_rev_offsets), graph_r.offsets.size() * sizeof(uint32_t)), "cudaMalloc offsets");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_rev_to), graph_r.to.size() * sizeof(uint32_t)), "cudaMalloc to");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_rev_length), graph_r.length.size() * sizeof(float)), "cudaMalloc length");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_rev_edge_id), rev_edge_id.size() * sizeof(uint32_t)), "cudaMalloc rev_edge_id");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_to), graph.to.size() * sizeof(uint32_t)), "cudaMalloc to");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_dist), n * sizeof(float)), "cudaMalloc dist");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_updates), m * sizeof(RelaxUpdate)), "cudaMalloc updates");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_update_count), sizeof(uint32_t)), "cudaMalloc update_count");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_frontier), n * sizeof(uint32_t)), "cudaMalloc frontier");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_frontier_queue), n * sizeof(uint32_t)), "cudaMalloc frontier_queue");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_frontier_tail), sizeof(uint32_t)), "cudaMalloc frontier_tail");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_finished), sizeof(bool)), "cudaMalloc finished");
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_arc_flags), arc_flags.size() * sizeof(uint32_t)), "cudaMalloc arc_flags");

  CheckCuda(cudaMemcpy(d_rev_offsets, graph_r.offsets.data(), graph_r.offsets.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
            "cudaMemcpy offsets");
  CheckCuda(cudaMemcpy(d_rev_to, graph_r.to.data(), graph_r.to.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
            "cudaMemcpy to");
  CheckCuda(cudaMemcpy(d_rev_length, graph_r.length.data(), graph_r.length.size() * sizeof(float), cudaMemcpyHostToDevice),
            "cudaMemcpy length");
  CheckCuda(cudaMemcpy(d_rev_edge_id, rev_edge_id.data(), rev_edge_id.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
            "cudaMemcpy rev_edge_id");
  CheckCuda(cudaMemcpy(d_to, graph.to.data(), graph.to.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
            "cudaMemcpy to");
  CheckCuda(cudaMemcpy(d_arc_flags, arc_flags.data(), arc_flags.size() * sizeof(uint32_t), cudaMemcpyHostToDevice),
              "cudaMemcpy arc_flags");

  std::vector<uint32_t> frontier_queue(n);

  for (uint32_t source : boundary_vertices) {
    const uint32_t region = partition.region[source];

    const uint32_t init_blocks = (n + 255) / 256;
    initSingleSourceKernel<<<init_blocks, 256>>>(d_dist, n, source);
    CheckCuda(cudaGetLastError(), "initSingleSourceKernel launch");
    CheckCuda(cudaDeviceSynchronize(), "initSingleSourceKernel sync");

    frontier_queue[0] = source;
    CheckCuda(cudaMemcpy(d_frontier_queue, frontier_queue.data(), sizeof(uint32_t), cudaMemcpyHostToDevice),
              "cudaMemcpy initial frontier");
    CheckCuda(cudaMemset(d_frontier_tail, 1, sizeof(uint32_t)), "cudaMemset frontier_tail to 1");
    CheckCuda(cudaMemset(d_finished, 0, sizeof(bool)), "cudaMemset finished to false");

    deltaSteppingPersistentKernel<<<1, 256>>>(d_rev_offsets,
                                              d_rev_to,
                                              d_rev_length,
                                              n,
                                              source,
                                              delta,
                                              d_dist,
                                              d_frontier_queue,
                                              d_frontier_tail,
                                              n,
                                              d_finished);
    CheckCuda(cudaGetLastError(), "deltaSteppingPersistentKernel launch");
    CheckCuda(cudaDeviceSynchronize(), "deltaSteppingPersistentKernel sync");

    markFlagsKernel<<<(m + 255) / 256, 256>>>(d_rev_edge_id, d_to, d_rev_to, d_rev_length, d_dist, m, region, regions_count, d_arc_flags);
    CheckCuda(cudaGetLastError(), "markFlagsKernel launch");
    CheckCuda(cudaDeviceSynchronize(), "markFlagsKernel sync");
  }

  CheckCuda(cudaMemcpy(arc_flags.data(), d_arc_flags, arc_flags.size() * sizeof(uint32_t), cudaMemcpyDeviceToHost),
            "cudaMemcpy arc_flags back");

  cudaFree(d_rev_offsets);
  cudaFree(d_rev_to);
  cudaFree(d_rev_length);
  cudaFree(d_rev_edge_id);
  cudaFree(d_to);
  cudaFree(d_dist);
  cudaFree(d_updates);
  cudaFree(d_update_count);
  cudaFree(d_frontier);
  cudaFree(d_frontier_queue);
  cudaFree(d_frontier_tail);
  cudaFree(d_finished);
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
