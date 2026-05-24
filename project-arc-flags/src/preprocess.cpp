#include <fstream>
#include <vector>
#include <cstdint>
#include "utils.hpp"
#include <iostream>
#include <filesystem>

namespace arcflags {

struct PartitionData {
    uint32_t regions_count;
    std::vector<uint32_t> region;
};

PartitionData ReadPartitionText(const std::string& path, const uint32_t n) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("Cannot open input file: " + path);
    }
    PartitionData partition;
    if (!(input >> partition.regions_count)) {
        throw std::runtime_error("Could not read regions count from text input.");
    }
    partition.region = ReadTextVectorU32(input, n, "region");
    return partition;
}

PartitionData ReadPartitionBinary(const std::string& path, const uint32_t n) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("Cannot open input file: " + path);
    }
    PartitionData partition;
    input.read(reinterpret_cast<char*>(&partition.regions_count), sizeof(uint32_t));
    if (!input) {
        throw std::runtime_error("Could not read regions count from binary input.");
    }
    partition.region = ReadBinaryVectorU32(input, n, "region");
    return partition;
}

PartitionData ReadPartition(const CliOptions& options, const uint32_t n) {
    if (options.format == Encoding::kTxt) {
        return ReadPartitionText(options.partition_path, n);
    } else {
        return ReadPartitionBinary(options.partition_path, n);
    }
}

PartitionData ValidatePartition(const PartitionData& partition, const uint32_t n) {
    if (partition.region.size() != n) {
        throw std::runtime_error("Partition size does not match graph vertex count.");
    }
    for (const uint32_t r : partition.region) {
        if (r >= partition.regions_count) {
            throw std::runtime_error("Partition contains out-of-range region id.");
        }
    }
    return partition;
}
// popraw to  zeby offsety liczyly sie poprawnie, aktualnie region_v + 1 moze wyjsc poza zakres - tak samo w reverseGraph
std::vector<uint32_t> findBoundaryVertices(const GraphData& graph, const PartitionData& partition, std::vector<uint32_t>& boundaryOffsets) {
    boundaryOffsets.resize(partition.regions_count, 0);
    for(uint32_t v = 0; v < graph.n; ++v) {
        const uint32_t region_v = partition.region[v];
        const uint32_t left_boundary = graph.offsets[v];
        const uint32_t right_boundary = (v != graph.n - 1 ? graph.offsets[v + 1] : graph.m);
        for (uint32_t i = left_boundary; i < right_boundary; ++i) {
            const uint32_t to = graph.to[i];
            const uint32_t region_to = partition.region[to];
            if (region_to != region_v) {
                boundaryOffsets[region_v + 1]++;
            }
        }
    }
    std::vector<uint32_t> boundaryVertices;
    for (uint32_t v = 0; v < graph.n; ++v) {
        const uint32_t region_v = partition.region[v];
        const uint32_t left_boundary = graph.offsets[v];
        const uint32_t right_boundary = (v != graph.n - 1 ? graph.offsets[v + 1] : graph.m);
        for (uint32_t i = left_boundary; i < right_boundary; ++i) {
            const uint32_t to = graph.to[i];
            const uint32_t region_to = partition.region[to];
            if (region_to != region_v) {
                const uint32_t pos = boundaryOffsets[region_v]++;
                boundaryVertices.push
                break;
            }
        }
    }
    return boundaryVertices;
}
//rev_edge_id:  reverse graph edge id -> original graph edge id
GraphData reverseGraph(const GraphData& graph, std::vector<uint32_t>& rev_edge_id) {
    GraphData reversed;
    reversed.n = graph.n;
    reversed.m = graph.m;
    reversed.offsets.resize(graph.n, 0);
    reversed.to.resize(graph.m);
    reversed.length.resize(graph.m);
    rev_edge_id.resize(graph.m);

    for (uint32_t v = 0; v < graph.n; ++v) {
        const uint32_t left_boundary = graph.offsets[v];
        const uint32_t right_boundary = (v != graph.n - 1 ? graph.offsets[v + 1] : graph.m);
        for (uint32_t i = left_boundary; i < right_boundary; ++i) {
            const uint32_t to = graph.to[i];
            const float length = graph.length[i];
            reversed.offsets[to + 1]++;
        }
    }

    for (uint32_t v = 1; v < graph.n; ++v) {
        reversed.offsets[v] += reversed.offsets[v - 1];
    }

    std::vector<uint32_t> current_offset(reversed.offsets.begin(), reversed.offsets.end());

    for (uint32_t v = 0; v < graph.n; ++v) {
        const uint32_t left_boundary = graph.offsets[v];
        const uint32_t right_boundary = (v != graph.n - 1 ? graph.offsets[v + 1] : graph.m);
        for (uint32_t i = left_boundary; i < right_boundary; ++i) {
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

std::vector<uint32_t> arcFlagsPreprocessing(const GraphData& graph, const PartitionData& partition) {

    return std::vector<uint32_t>();
}

}// namespace arcflags

int main(int argc, char* argv[]) {
    try{
        const arcflags::CliOptions options = arcflags::ParseCliArgs(argc, argv);
        if(options.graph_path.empty()) {
            throw std::runtime_error("Missing required --graph");
        }
        if(options.partition_path.empty()) {
            throw std::runtime_error("Missing required --partition");
        }
        if(options.output_path.empty()) {
            throw std::runtime_error("Missing required --out");
        }
        const arcflags::GraphData graph = arcflags::ReadGraph(options);
        const arcflags::PartitionData partition = arcflags::ReadPartition(options, graph.n);
        std::cout<<partition.regions_count<<std::endl;

        const std::vector<uint32_t> arcFlags = arcflags::arcFlagsPreprocessing(graph, partition);


        const std::filesystem::path out_path(options.output_path);
        if (out_path.has_parent_path()) {
            std::filesystem::create_directories(out_path.parent_path());
        }
        if(options.format == arcflags::Encoding::kTxt) {
            std::ofstream output(options.flags_path);
            arcflags::WriteTextVector(output, arcFlags);
        } else {
            std::ofstream output(options.flags_path, std::ios::binary);
            arcflags::WriteBinaryVector(output, arcFlags);
        }
        
        return 0;
    }
    catch(const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;

    }

}

