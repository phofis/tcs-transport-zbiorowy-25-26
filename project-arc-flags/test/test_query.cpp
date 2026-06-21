#include "utils.hpp"
#include "preprocess_utils.hpp"
#include <limits>
#include <queue>
#include <iostream>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <cstdint>
#include <vector>
#include <utility>
#include <cmath>

float query(uint32_t source, uint32_t target, const arcflags::GraphData& graph) {
    const float INF = std::numeric_limits<float>::infinity();
    std::vector<float> dist(graph.n, INF);

    std::priority_queue<
        arcflags::State,
        std::vector<arcflags::State>,
        arcflags::StateComp
    > pq;

    dist[source] = 0.0;
    pq.push({source, 0.0});
    const float EPS = 1e-6;
    while (!pq.empty()) {

        arcflags::State cur = pq.top();
        pq.pop();

        if (cur.dist > dist[cur.v] + EPS)
            continue;

        if (cur.v == target)
            return cur.dist;

        for (uint32_t e = graph.offsets[cur.v];
             e < graph.offsets[cur.v + 1];
             ++e)
        {
            uint32_t to = graph.to[e];
            float nd = cur.dist + graph.length[e];
            if (nd < dist[to] - EPS) {
                dist[to] = nd;
                pq.push({to, nd});
            }
        }
    }

    return INF;
}

int main(int argc, char** argv) {
    try {
        arcflags::CliOptions options = arcflags::ParseCliArgs(argc, argv);
        if (options.query_path.empty()) {
            throw std::runtime_error("Missing required --queries");
        }

        arcflags::GraphData graph = arcflags::ReadGraph(options);

        const std::filesystem::path input_path(options.query_path);
        std::ifstream input(input_path);
        if (!input) {
            throw std::runtime_error("Cannot open input file: " + options.query_path);
        }

        const std::filesystem::path out_path(options.output_path);
        if (out_path.has_parent_path()) {
            std::filesystem::create_directories(out_path.parent_path());
        }
        std::ofstream output(out_path);
        if (!output) {
            throw std::runtime_error("Cannot open output file: " + options.output_path);
        }

        uint32_t query_count;
        if (!(input >> query_count)) {
            throw std::runtime_error("Could not read query count from input.");
        }

        while (query_count--) {
            uint32_t source, target;
            if (!(input >> source >> target)) {
                throw std::runtime_error("Could not read query pair from input.");
            }
            float dist = query(source, target, graph);
            output << dist << "\n";
        }

        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "test_query: " << ex.what() << '\n';
        return 1;git
    }
}
