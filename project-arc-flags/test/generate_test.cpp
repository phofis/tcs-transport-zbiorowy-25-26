#include "utils.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>

int main(int argc, char** argv) {
    try {
        arcflags::CliOptions options = arcflags::ParseCliArgs(argc, argv);

        arcflags::GraphData graph = arcflags::ReadGraph(options);

        if (graph.n == 0) {
            throw std::runtime_error("Graph contains no vertices.");
        }

        const std::filesystem::path out_path(options.output_path);
        if (out_path.has_parent_path()) {
            std::filesystem::create_directories(out_path.parent_path());
        }
        std::ofstream output(out_path);
        if (!output) {
            throw std::runtime_error("Cannot open output file: " + options.output_path);
        }

        const uint32_t count = options.test_count;
        output << count << "\n";

        std::random_device rd;
        std::mt19937_64 gen(rd());
        std::uniform_int_distribution<uint32_t> dist(0, graph.n - 1);

        for (uint32_t i = 0; i < count; ++i) {
            uint32_t s = dist(gen);
            uint32_t t = dist(gen);
            if (graph.n > 1) {
                while (t == s) {
                    t = dist(gen);
                }
            }
            output << s << " " << t << "\n";
        }

        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "generate_test: " << ex.what() << '\n';
        return 1;
    }
}
