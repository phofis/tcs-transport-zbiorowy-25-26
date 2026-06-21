#include "utils.hpp"

namespace arcflags {

struct State {
    uint32_t v;
    double dist;
};

struct StateComp {
    bool operator()(const State& a, const State& b) const {
        return a.dist > b.dist;
    }
};

bool read_flag(const std::vector<uint32_t>& arc_flags, uint32_t edge_id, uint32_t region, uint32_t region_count);

std::vector<uint32_t> findBoundaryVertices(
        const GraphData &graph,
        const GraphData &graph_r,
        const PartitionData &partition,
        std::vector<uint32_t> &boundaryOffsets);

GraphData reverseGraph(const GraphData &graph, std::vector<uint32_t> &rev_edge_id);

void set_flag(std::vector<uint32_t> &arc_flags, uint32_t edge_id, uint32_t region, uint32_t region_count);

} // namespace arcflags