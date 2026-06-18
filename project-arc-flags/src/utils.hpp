#pragma once

#include <cstddef>
#include <cstdint>
#include <iosfwd>
#include <string>
#include <vector>

namespace arcflags {


enum class Encoding {
  kBin,
  kTxt,
};

struct CliOptions {
  std::string input_path;
  std::string output_path;
  std::string graph_path;
  std::string partition_path;
  std::string flags_path;
  std::string query_path;
  Encoding format = Encoding::kBin;
  uint32_t test_count = 1000;
};

struct GraphData {
  uint32_t n = 0;
  uint32_t m = 0;
  std::vector<uint32_t> offsets;
  std::vector<uint32_t> to;
  std::vector<float> length;
};

struct PartitionData {
    uint32_t regions_count;
    std::vector<uint32_t> region;
};

struct State {
    uint32_t v;
    double dist;
};

struct StateComp {
    bool operator()(const State& a, const State& b) const {
        return a.dist > b.dist;
    }  
};

CliOptions ParseCliArgs(int argc, char** argv);
const char* EncodingName(Encoding encoding);
std::string UsageText();

void ValidateCsr(const GraphData& graph);
GraphData ReadGraphText(const std::string& path);
GraphData ReadGraphBinary(const std::string& path);
GraphData ReadGraph(const CliOptions& options);

void ValidatePartition(const PartitionData& partition, const uint32_t n);
PartitionData ReadPartitionText(const std::string& path, const uint32_t n);
PartitionData ReadPartitionBinary(const std::string& path, const uint32_t n);
PartitionData ReadPartition(const CliOptions& options, const uint32_t n);


std::vector<uint32_t> ReadTextVectorU32(std::istream& input, std::size_t count, const std::string& label);
std::vector<float> ReadTextVectorFloat(std::istream& input, std::size_t count, const std::string& label);
std::vector<uint32_t> ReadBinaryVectorU32(std::istream& input, std::size_t count, const std::string& label);
std::vector<float> ReadBinaryVectorFloat(std::istream& input, std::size_t count, const std::string& label);
void WriteTextVector(std::ostream& output, const std::vector<uint32_t>& values);
void WriteTextVector(std::ostream& output, const std::vector<float>& values);
void WriteBinaryVector(std::ostream& output, const std::vector<uint32_t>& values);
void WriteBinaryVector(std::ostream& output, const std::vector<float>& values);
bool read_flag(const std::vector<uint32_t>& arc_flags, uint32_t edge_id, uint32_t region, uint32_t region_count);
}  // namespace arcflags
