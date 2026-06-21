#include <fstream>
#include <vector>
#include <queue>
#include <utility>
#include <cstdint>
#include "utils.hpp"
#include "preprocess_utils.hpp"
#include <iostream>
#include <omp.h>
#include <filesystem>
#include <cmath>
namespace arcflags
{

    // dwie wersje: 1 - dijkstra z kazdej krawędzi 2- multi source dijkstra z kazdego
    std::vector<uint32_t> arcFlagsPreprocessing(const GraphData &graph, const arcflags::PartitionData &partition)
    {
        const uint32_t N = graph.n;
        const uint32_t M = graph.m;
        const uint32_t R = partition.regions_count;

        const uint32_t W = (R + 31) / 32;

        std::vector<uint32_t> arc_flags(M * W, 0);

        // boundary vertices grouped by region
        // reverse graph
        std::vector<uint32_t> rev_edge_id;
        arcflags::GraphData graph_r = reverseGraph(graph, rev_edge_id);

        std::vector<uint32_t> boundary_offsets;
        std::vector<uint32_t> boundary_vertices =
            findBoundaryVertices(graph, graph_r, partition, boundary_offsets);

        constexpr float INF = std::numeric_limits<float>::infinity();
        constexpr float EPS = 1e-6;

        
        for (uint32_t e = 0; e < M; ++e)
        {
            uint32_t to = graph.to[e];
            set_flag(arc_flags, e, partition.region[to], R);
        }

        int threads = omp_get_max_threads();
        std::vector<std::vector<float>> dist_buffers(threads, std::vector<float>(N, INF));
        std::vector<std::vector<int>> visited_buffers(threads, std::vector<int>(N, 0));
        std::vector<int> stamps(threads, 0);
    #pragma omp parallel
    {  
        #pragma omp for schedule(dynamic)
        for (uint32_t i = 0; i < boundary_offsets[R]; ++i)
        {
            int tid = omp_get_thread_num();
            int curr_stamp = stamps[tid]++;
            std::vector<int> &visited = visited_buffers[tid];
            std::vector<float> &dist = dist_buffers[tid];
            uint32_t s = boundary_vertices[i];
            uint32_t r = partition.region[s];

            std::priority_queue<
                State,
                std::vector<State>,
                StateComp>
                pq;

            dist[s] = 0.0;
            visited[s] = curr_stamp;

            pq.push({s, 0.0});

            // reverse Dijkstra
            while (!pq.empty())
            {

                const State cur = pq.top();
                pq.pop();

                if (cur.dist > dist[cur.v] + EPS)
                    continue;

                for (uint32_t e = graph_r.offsets[cur.v]; e < graph_r.offsets[cur.v + 1]; ++e)
                {
                    uint32_t to = graph_r.to[e];
                    float to_dist = visited[to] == curr_stamp ? dist[to] : INF;
                    float  nd = cur.dist + graph_r.length[e];
                    if (nd < to_dist - EPS)
                    {
                        dist[to] = nd;
                        visited[to] = curr_stamp;
                        pq.push({to, nd});
                    }
                }
            }
            // check if edge is on shortest path
            for (uint32_t v = 0; v < N; ++v)
            {
                for (uint32_t e = graph_r.offsets[v]; e < graph_r.offsets[v + 1]; ++e)
                {
                    uint32_t to = graph_r.to[e];
                    if (std::isinf(dist[v]) || std::isinf(dist[to]))
                        continue;

                    if (std::abs(dist[to] -
                                    (dist[v] + graph_r.length[e])) <= EPS)
                    {
                        set_flag(arc_flags, rev_edge_id[e], r, R);
                    }
                }
            }
        }
    }

        return arc_flags;
    }

} // namespace arcflags
int main(int argc, char *argv[])
{
    try
    {
        const arcflags::CliOptions options = arcflags::ParseCliArgs(argc, argv);

        if (options.partition_path.empty())
        {
            throw std::runtime_error("Missing required --partition");
        }
        const arcflags::GraphData graph = arcflags::ReadGraph(options);
        const arcflags::PartitionData partition = arcflags::ReadPartition(options, graph.n);
        const std::vector<uint32_t> arcFlags = arcflags::arcFlagsPreprocessing(graph, partition);
        const std::filesystem::path out_path(options.output_path);
        if (out_path.has_parent_path())
        {
            std::filesystem::create_directories(out_path.parent_path());
        }

        std::ofstream output(out_path);

        if (options.format == arcflags::Encoding::kTxt)
            arcflags::WriteTextVector(output, arcFlags);
        else
            arcflags::WriteBinaryVector(output, arcFlags);

        return 0;
    }
    catch (const std::exception &e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
