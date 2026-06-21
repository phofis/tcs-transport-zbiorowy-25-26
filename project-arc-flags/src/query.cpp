#include <fstream>
#include "utils.hpp"
#include "preprocess_utils.hpp"
#include <iostream>
#include <filesystem>
#include <queue>

std::vector<uint32_t> readArcFlags(arcflags::CliOptions options, uint32_t len) {

    std::filesystem::path flags_path(options.flags_path);
    std::vector<uint32_t> flags;
    
    
    if(options.format == arcflags::Encoding::kTxt) {
        std::ifstream input(flags_path);
        flags = arcflags::ReadTextVectorU32(input, len, "flags");
    }
    else {
        std::ifstream input(flags_path, std::ios::binary);
        flags = arcflags::ReadBinaryVectorU32(input, len, "flags");
    }
    return flags;
}
float query(uint32_t source, uint32_t target, arcflags::PartitionData& partition, std::vector<uint32_t>& flags, arcflags::GraphData& graph) {
    const float INF = std::numeric_limits<float>::infinity();
    const uint32_t target_region = partition.region[target];
    const float EPS = 1e-6;
    std::vector<float> dist(graph.n, INF);

    std::priority_queue<
        arcflags::State,
        std::vector<arcflags::State>,
        arcflags::StateComp
    > pq;

    dist[source] = 0.0;
    pq.push({source, 0.0});

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
            if (!arcflags::read_flag(
                    flags,
                    e,
                    target_region,
                    partition.regions_count))
            {
                    continue;
            }

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
    if(options.partition_path.empty()) {
        throw std::runtime_error("Missing required --partition");
    }
    if(options.flags_path.empty()) {
        throw std::runtime_error("Missing required --flags");
    }
    if(options.query_path.empty()) {
        throw std::runtime_error("Missing required --queries");
    }
    arcflags::GraphData graph = arcflags::ReadGraph(options);
    const uint32_t N = graph.n;
    const uint32_t M = graph.m;

    arcflags::PartitionData partition = arcflags::ReadPartition(options, N);
    const uint32_t R = partition.regions_count;
    const uint32_t flags_len = M * ((R + 31)/32);

    std::vector<uint32_t> arcFlags = readArcFlags(options, flags_len);

    std::filesystem::path queryPath(options.query_path);
    std::ifstream input(queryPath);

    const std::filesystem::path out_path(options.output_path);
        if (out_path.has_parent_path()) {
            std::filesystem::create_directories(out_path.parent_path());
        }
        
    std::ofstream output(out_path);

    uint32_t query_count;
    input>>query_count;
    while(query_count--) {
        uint32_t source, target;
        input>>source>>target;
        float dist = query(source, target, partition ,arcFlags, graph);
        output<<dist<<"\n";
    }

    }catch (const std::exception& ex) {
    std::cerr << "partition: " << ex.what() << '\n';
    return 1;
    }
    
}