#include "utils.hpp"

#include <fstream>
#include <istream>
#include <ostream>
#include <stdexcept>
#include <string>

namespace arcflags {
namespace {


const char kUsageText[] = "Usage: partition --in <path> --out <path> [--format bin|txt]";

[[noreturn]] void ThrowUsageError(const std::string& message) {
  throw std::runtime_error(message + "\n" + kUsageText);
}

template <typename T>
std::vector<T> ReadTextVector(std::istream& input, const std::size_t count, const std::string& label) {
  std::vector<T> values;
  values.reserve(count);
  for (std::size_t i = 0; i < count; ++i) {
    T value{};
    if (!(input >> value)) {
      throw std::runtime_error("Could not read " + label + " from text input.");
    }
    values.push_back(value);
  }
  return values;
}

template <typename T>
std::vector<T> ReadBinaryVector(std::istream& input, const std::size_t count, const std::string& label) {
  std::vector<T> values(count);
  if (count == 0) {
    return values;
  }
  input.read(reinterpret_cast<char*>(values.data()), static_cast<std::streamsize>(count * sizeof(T)));
  if (!input) {
    throw std::runtime_error("Could not read " + label + " from binary input.");
  }
  return values;
}

template <typename T>
void WriteTextVectorImpl(std::ostream& output, const std::vector<T>& values) {
  for (std::size_t i = 0; i < values.size(); ++i) {
    if (i > 0) {
      output << ' ';
    }
    output << values[i];
  }
  output << '\n';
}

template <typename T>
void WriteBinaryVectorImpl(std::ostream& output, const std::vector<T>& values) {
  if (values.empty()) {
    return;
  }
  output.write(reinterpret_cast<const char*>(values.data()),
               static_cast<std::streamsize>(values.size() * sizeof(T)));
  if (!output) {
    throw std::runtime_error("Failed while writing output.");
  }
}

}  // namespace

const char* EncodingName(const Encoding encoding) {
  return encoding == Encoding::kBin ? "bin" : "txt";
}

std::string UsageText() { return kUsageText; }

CliOptions ParseCliArgs(int argc, char** argv) {
  CliOptions options;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--out") {
      if (i + 1 >= argc) {
        ThrowUsageError("Missing value for --out");
      }
      options.output_path = argv[++i];
      continue;
    }
    if(arg == "--graph") {
      if (i + 1 >= argc) {
        ThrowUsageError("Missing value for --graph");
      }
      options.graph_path = argv[++i];
      continue;
    }
    if(arg == "--partition") {
      if (i + 1 >= argc) {
        ThrowUsageError("Missing value for --partition");
      }
      options.partition_path = argv[++i];
      continue;
    }
    if(arg == "--flags") {
      if (i + 1 >= argc) {
        ThrowUsageError("Missing value for --flags");
      }
      options.flags_path = argv[++i];
      continue;
    }
    if(arg == "--queries") {
      if (i + 1 >= argc) {
        ThrowUsageError("Missing value for --queries");
      }
      options.query_path = argv[++i];
      continue;
    }
    if (arg == "--format") {
      if (i + 1 >= argc) {
        ThrowUsageError("Missing value for --format");
      }
      const std::string value = argv[++i];
      if (value == "bin") {
        options.format = Encoding::kBin;
      } else if (value == "txt") {
        options.format = Encoding::kTxt;
      } else {
        ThrowUsageError("Invalid --format value: " + value);
      }
      continue;
    }
    if (arg == "--count") {
      if (i + 1 >= argc) {
        ThrowUsageError("Missing value for --count");
      }
      const std::string value = argv[++i];
      try {
        options.test_count = static_cast<uint32_t>(std::stoul(value));
      } catch (...) {
        ThrowUsageError("Invalid --count value: " + value);
      }
      continue;
    }
    ThrowUsageError("Unknown argument: " + arg);
  }

  if (options.graph_path.empty()) {
    ThrowUsageError("Missing required --graph");
  }
  if (options.output_path.empty()) {
    ThrowUsageError("Missing required --out");
  }

  return options;
}

void ValidateCsr(const GraphData& graph) {
  if (graph.offsets.size() != graph.n + 1) {
    throw std::runtime_error("Invalid graph: offsets size does not match N.");
  }
  if (graph.to.size() != graph.m || graph.length.size() != graph.m) {
    throw std::runtime_error("Invalid graph: to/length size does not match M.");
  }

  uint32_t previous = 0;
  for (uint32_t i = 0; i <= graph.n; ++i) {
    const uint32_t current = graph.offsets[i];
    if (current < previous || current > graph.m) {
      throw std::runtime_error("Invalid graph: offsets must be non-decreasing in [0,M].");
    }
    previous = current;
  }
  if (graph.offsets[0] != 0) {
    throw std::runtime_error("Invalid graph: offsets[0] must be 0.");
  }
  if(graph.offsets[graph.n] != graph.m) {
    throw std::runtime_error("Invalid graph: offsets[N] must be M.");
  }

  for (uint32_t edge_id = 0; edge_id < graph.m; ++edge_id) {
    if (graph.to[edge_id] >= graph.n) {
      throw std::runtime_error("Invalid graph: to[] contains vertex id out of range.");
    }
  }
}

std::vector<uint32_t> ReadTextVectorU32(std::istream& input, const std::size_t count, const std::string& label) {
  return ReadTextVector<uint32_t>(input, count, label);
}

std::vector<float> ReadTextVectorFloat(std::istream& input, const std::size_t count, const std::string& label) {
  return ReadTextVector<float>(input, count, label);
}

std::vector<uint32_t> ReadBinaryVectorU32(std::istream& input, const std::size_t count, const std::string& label) {
  return ReadBinaryVector<uint32_t>(input, count, label);
}

std::vector<float> ReadBinaryVectorFloat(std::istream& input, const std::size_t count, const std::string& label) {
  return ReadBinaryVector<float>(input, count, label);
}

GraphData ReadGraphText(const std::string& path) {
  std::ifstream input(path);
  if (!input) {
    throw std::runtime_error("Cannot open input file: " + path);
  }

  GraphData graph;
  if (!(input >> graph.n >> graph.m)) {
    throw std::runtime_error("Could not read N and M from text input.");
  }

  graph.offsets = ReadTextVectorU32(input, graph.n + 1, "offsets");
  graph.to = ReadTextVectorU32(input, graph.m, "to");
  graph.length = ReadTextVectorFloat(input, graph.m, "length");
  ValidateCsr(graph);
  return graph;
}

GraphData ReadGraphBinary(const std::string& path) {
  static_assert(sizeof(uint32_t) == 4, "uint32_t must be 4 bytes.");
  static_assert(sizeof(float) == 4, "float must be 4 bytes.");

  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("Cannot open input file: " + path);
  }

  GraphData graph;
  input.read(reinterpret_cast<char*>(&graph.n), sizeof(uint32_t));
  input.read(reinterpret_cast<char*>(&graph.m), sizeof(uint32_t));
  if (!input) {
    throw std::runtime_error("Could not read N and M from binary input.");
  }

  graph.offsets = ReadBinaryVectorU32(input, graph.n + 1, "offsets");
  graph.to = ReadBinaryVectorU32(input, graph.m, "to");
  graph.length = ReadBinaryVectorFloat(input, graph.m, "length");
  ValidateCsr(graph);
  return graph;
}

GraphData ReadGraph(const CliOptions& options) {
  if (options.format == Encoding::kTxt) {
    return ReadGraphText(options.graph_path);
  }
  return ReadGraphBinary(options.graph_path);
}

void WriteTextVector(std::ostream& output, const std::vector<uint32_t>& values) {
  WriteTextVectorImpl(output, values);
}

void WriteTextVector(std::ostream& output, const std::vector<float>& values) {
  WriteTextVectorImpl(output, values);
}

void WriteBinaryVector(std::ostream& output, const std::vector<uint32_t>& values) {
  WriteBinaryVectorImpl(output, values);
}

void WriteBinaryVector(std::ostream& output, const std::vector<float>& values) {
  WriteBinaryVectorImpl(output, values);
}


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

void ValidatePartition(const PartitionData& partition, const uint32_t n) {
    if (partition.region.size() != n) {
        throw std::runtime_error("Partition size does not match graph vertex count.");
    }
    for (const uint32_t r : partition.region) {
        if (r >= partition.regions_count) {
            throw std::runtime_error("Partition contains out-of-range region id.");
        }
    }
}
bool read_flag(const std::vector<uint32_t>& arc_flags, uint32_t edge_id, uint32_t region, uint32_t region_count) {
    const uint32_t W = (region_count + 31)/32;
    uint32_t word = region >> 5;
    
    uint32_t bit = region & 31;

    return (arc_flags[edge_id * W + word] >> (31 - bit)) & 1u;
} 


}  // namespace arcflags
