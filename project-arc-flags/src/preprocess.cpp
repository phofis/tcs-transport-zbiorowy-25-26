#include <fstream>
#include <vector>
#include <queue>
#include <utility>
#include <cstdint>
#include "utils.hpp"
#include <iostream>
#include <filesystem>
#include <cmath>
namespace arcflags {

struct State {
    uint32_t v;
    float dist;

};
struct StateComp {
    bool operator()(const State& a, const State& b) const {
        return a.dist > b.dist;
    }
};

std::vector<uint32_t> findBoundaryVertices(
    const GraphData& graph,
    const PartitionData& partition,
    std::vector<uint32_t>& boundaryOffsets)
{
    const uint32_t R = partition.regions_count;

    boundaryOffsets.assign(R + 1, 0);

    // temporary storage: boundary candidates
    std::vector<uint32_t> boundary_vertices_tmp;
    boundary_vertices_tmp.reserve(graph.n / 10); // heuristic

    std::vector<uint32_t> boundary_region_tmp;
    boundary_region_tmp.reserve(graph.n / 10);

    // ===== PASS 1: scan graph once =====
    for (uint32_t v = 0; v < graph.n; ++v) {

        const uint32_t rv = partition.region[v];
        bool is_boundary = false;

        for (uint32_t i = graph.offsets[v];
             i < graph.offsets[v + 1];
             ++i)
        {
            if (partition.region[graph.to[i]] != rv) {
                is_boundary = true;
                break;
            }
        }

        if (is_boundary) {
            boundary_vertices_tmp.push_back(v);
            boundary_region_tmp.push_back(rv);
            boundaryOffsets[rv + 1]++;
        }
    }

    // ===== PREFIX SUM =====
    for (uint32_t r = 1; r <= R; ++r) {
        boundaryOffsets[r] += boundaryOffsets[r - 1];
    }

    // ===== PACK =====
    std::vector<uint32_t> boundaryVertices(boundaryOffsets[R]);
    std::vector<uint32_t> cursor = boundaryOffsets;

    for (size_t i = 0; i < boundary_vertices_tmp.size(); ++i) {
        uint32_t v = boundary_vertices_tmp[i];
        uint32_t rv = boundary_region_tmp[i];

        boundaryVertices[cursor[rv]++] = v;
    }

    return boundaryVertices;
}
//rev_edge_id:  reverse graph edge id -> original graph edge id
GraphData reverseGraph(const GraphData& graph, std::vector<uint32_t>& rev_edge_id) {
    GraphData reversed;
    reversed.n = graph.n;
    reversed.m = graph.m;
    reversed.offsets.resize(graph.n + 1, 0);
    reversed.to.resize(graph.m);
    reversed.length.resize(graph.m);
    rev_edge_id.resize(graph.m);

    for (uint32_t v = 0; v < graph.n; ++v) {
        for (uint32_t i = graph.offsets[v]; i < graph.offsets[v+1]; ++i) {
            const uint32_t to = graph.to[i];
            reversed.offsets[to + 1]++;
        }
    }

    for (uint32_t v = 1; v <= graph.n; ++v) {
        reversed.offsets[v] += reversed.offsets[v - 1];
    }

    std::vector<uint32_t> current_offset(reversed.offsets.begin(), reversed.offsets.end());

    for (uint32_t v = 0; v < graph.n; ++v) {
        for (uint32_t i = graph.offsets[v]; i < graph.offsets[v+1]; ++i) {
            const uint32_t to = graph.to[i];
            const float length = graph.length[i];
            const uint32_t offset = current_offset[to]++;
            reversed.to[offset] = v;
            reversed.length[offset] = length;
            rev_edge_id[offset] = i;
        }
    }

    return reversed;
}
void set_flag(std::vector<uint32_t>& arc_flags, uint32_t edge_id, uint32_t region, uint32_t region_count) {
    const uint32_t W = (region_count + 31)/32;
    uint32_t word = region >> 5;
    
    uint32_t bit = region & 31;
    arc_flags[edge_id * W + word] |= (1u<< (31-bit));
}
bool read_flag(const std::vector<uint32_t>& arc_flags, uint32_t edge_id, uint32_t region, uint32_t region_count) {
    const uint32_t W = (region_count + 31)/32;
    uint32_t word = region >> 5;
    
    uint32_t bit = region & 31;

    return (arc_flags[edge_id * W + word] >> (31 - bit)) & 1u;
} 
// dwie wersje: 1 - dijkstra z kazdej krawędzi 2- multi source dijkstra z kazdego 
std::vector<uint32_t> arcFlagsPreprocessing(const GraphData& graph, const PartitionData& partition) {
    const uint32_t N = graph.n;
    const uint32_t M = graph.m;
    const uint32_t R = partition.regions_count;

    const uint32_t W = (R + 31) / 32;

    std::vector<uint32_t> arc_flags(M * W, 0);

    // boundary vertices grouped by region
    std::vector<uint32_t> boundary_offsets;
    std::vector<uint32_t> boundary_vertices =
        findBoundaryVertices(graph, partition, boundary_offsets);

    // reverse graph
    std::vector<uint32_t> rev_edge_id;
    GraphData graph_r = reverseGraph(graph, rev_edge_id);

    constexpr float INF = std::numeric_limits<float>::infinity();
    constexpr float EPS = 1e-6;

    std::vector<float> dist(N);

    for (uint32_t r = 0; r < R; ++r) {
        
        std::fill(dist.begin(), dist.end(), INF);
        
        std::priority_queue<
            State,
            std::vector<State>,
            StateComp
        > pq;
        for (uint32_t i = boundary_offsets[r] ; i < boundary_offsets[r + 1]; ++i) {
            uint32_t s = boundary_vertices[i];

            dist[s] = 0.0f;
            pq.push({s, 0.0f});
        

            // reverse Dijkstra
            while (!pq.empty()) {

                const State cur = pq.top();
                pq.pop();

                if (cur.dist > dist[cur.v])
                    continue;

                for (uint32_t e = graph_r.offsets[cur.v] ; e < graph_r.offsets[cur.v + 1] ; ++e) {
                    uint32_t to = graph_r.to[e];
                    float nd = cur.dist + graph_r.length[e];
                    if (nd < dist[to] - EPS) {
                        dist[to] = nd;
                        pq.push({to, nd});
                    }
                }
            }
            //check if edge is on shortest path
            for(uint32_t v = 0 ; v < N; ++v) {
                for(uint32_t e = graph_r.offsets[v]; e < graph_r.offsets[v + 1]; ++e) {
                    uint32_t to = graph_r.to[e];
                    if(std::abs(dist[v] + graph_r.length[e] - dist[to]) <= EPS) {
                        set_flag(arc_flags, rev_edge_id[e], r, R);
                    }
                }
            }
        }
    }

    return arc_flags;
}

}// namespace arcflags

int main(int argc, char* argv[]) {
    try{
        const arcflags::CliOptions options = arcflags::ParseCliArgs(argc, argv);

        if(options.partition_path.empty()) {
            throw std::runtime_error("Missing required --partition");
        }
        const arcflags::GraphData graph = arcflags::ReadGraph(options);
        const arcflags::PartitionData partition = arcflags::ReadPartition(options, graph.n);
        const std::vector<uint32_t> arcFlags = arcflags::arcFlagsPreprocessing(graph, partition);


        const std::filesystem::path out_path(options.output_path);
        if (out_path.has_parent_path()) {
            std::filesystem::create_directories(out_path.parent_path());
        }
        
        std::ofstream output(out_path);

        if(options.format == arcflags::Encoding::kTxt) 
            arcflags::WriteTextVector(output, arcFlags);
        else 
            arcflags::WriteBinaryVector(output, arcFlags);
        
        return 0;
    }
    catch(const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

}

