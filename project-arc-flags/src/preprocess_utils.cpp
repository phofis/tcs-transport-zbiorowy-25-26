#include "preprocess_utils.hpp"
#include "utils.hpp"
#include <vector>
namespace arcflags
{

    std::vector<uint32_t> findBoundaryVertices(
        const GraphData &graph,
        const GraphData &graph_r,
        const PartitionData &partition,
        std::vector<uint32_t> &boundaryOffsets)
    {
        const uint32_t R = partition.regions_count;

        boundaryOffsets.assign(R + 1, 0);

        // temporary storage: boundary candidates
        std::vector<uint32_t> boundary_vertices_tmp;
        boundary_vertices_tmp.reserve(graph.n / 10); // heuristic

        std::vector<uint32_t> boundary_region_tmp;
        boundary_region_tmp.reserve(graph.n / 10);
        

        // ===== PASS 1: scan graph once =====
        for (uint32_t v = 0; v < graph.n; ++v)
        {

            const uint32_t rv = partition.region[v];
            bool is_boundary = false;

            for (uint32_t i = graph.offsets[v];
                 i < graph.offsets[v + 1];
                 ++i)
            {
                if (partition.region[graph.to[i]] != rv)
                {
                    is_boundary = true;
                    break;
                }
            } 

            if (!is_boundary)
            {
                for (uint32_t i = graph_r.offsets[v];
                     i < graph_r.offsets[v + 1];
                     ++i)
                {
                    if (partition.region[graph_r.to[i]] != rv)
                    {
                        is_boundary = true;
                        break;
                    }
                }
            }

            if (is_boundary)
            {
                boundary_vertices_tmp.push_back(v);
                boundary_region_tmp.push_back(rv);
                boundaryOffsets[rv + 1]++;
            }
        }

        // ===== PREFIX SUM =====
        for (uint32_t r = 1; r <= R; ++r)
        {
            boundaryOffsets[r] += boundaryOffsets[r - 1];
        }

        // ===== PACK =====
        std::vector<uint32_t> boundaryVertices(boundaryOffsets[R]);
        std::vector<uint32_t> cursor = boundaryOffsets;

        for (size_t i = 0; i < boundary_vertices_tmp.size(); ++i)
        {
            uint32_t v = boundary_vertices_tmp[i];
            uint32_t rv = boundary_region_tmp[i];

            boundaryVertices[cursor[rv]++] = v;
        }

        return boundaryVertices;
    }
    // rev_edge_id:  reverse graph edge id -> original graph edge id
    GraphData reverseGraph(const GraphData &graph, std::vector<uint32_t> &rev_edge_id)
    {
        GraphData reversed;
        reversed.n = graph.n;
        reversed.m = graph.m;
        reversed.offsets.resize(graph.n + 1, 0);
        reversed.to.resize(graph.m);
        reversed.length.resize(graph.m);
        rev_edge_id.resize(graph.m);

        for (uint32_t v = 0; v < graph.n; ++v)
        {
            for (uint32_t i = graph.offsets[v]; i < graph.offsets[v + 1]; ++i)
            {
                const uint32_t to = graph.to[i];
                reversed.offsets[to + 1]++;
            }
        }

        for (uint32_t v = 1; v <= graph.n; ++v)
        {
            reversed.offsets[v] += reversed.offsets[v - 1];
        }

        std::vector<uint32_t> current_offset(reversed.offsets.begin(), reversed.offsets.end());

        for (uint32_t v = 0; v < graph.n; ++v)
        {
            for (uint32_t i = graph.offsets[v]; i < graph.offsets[v + 1]; ++i)
            {
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
    void set_flag(std::vector<uint32_t> &arc_flags, uint32_t edge_id, uint32_t region, uint32_t region_count)
    {
        const uint32_t W = (region_count + 31) / 32;
        uint32_t word = region >> 5;

        uint32_t bit = region & 31;
        arc_flags[edge_id * W + word] |= (1u << (31 - bit));
    }
}