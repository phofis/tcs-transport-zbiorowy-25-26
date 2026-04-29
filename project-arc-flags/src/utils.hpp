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
  Encoding format = Encoding::kBin;
};

struct GraphData {
  uint32_t n = 0;
  uint32_t m = 0;
  std::vector<uint32_t> offsets;
  std::vector<uint32_t> to;
  std::vector<float> length;
};

CliOptions ParseCliArgs(int argc, char** argv);
const char* EncodingName(Encoding encoding);
std::string UsageText();
void ValidateCsr(const GraphData& graph);
GraphData ReadGraphText(const std::string& path);
GraphData ReadGraphBinary(const std::string& path);
GraphData ReadGraph(const CliOptions& options);

std::vector<uint32_t> ReadTextVectorU32(std::istream& input, std::size_t count, const std::string& label);
std::vector<float> ReadTextVectorFloat(std::istream& input, std::size_t count, const std::string& label);
std::vector<uint32_t> ReadBinaryVectorU32(std::istream& input, std::size_t count, const std::string& label);
std::vector<float> ReadBinaryVectorFloat(std::istream& input, std::size_t count, const std::string& label);
void WriteTextVector(std::ostream& output, const std::vector<uint32_t>& values);
void WriteTextVector(std::ostream& output, const std::vector<float>& values);
void WriteBinaryVector(std::ostream& output, const std::vector<uint32_t>& values);
void WriteBinaryVector(std::ostream& output, const std::vector<float>& values);

}  // namespace arcflags
