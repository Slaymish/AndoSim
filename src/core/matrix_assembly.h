#pragma once

#include "types.h"
#include "state.h"
#include "collision.h"

#include <array>
#include <unordered_map>
#include <vector>

namespace ando_barrier {

class MatrixAssembly {
public:
    static MatrixAssembly& instance();

    void configure(Index dof_count);

    void append_mass(const State& state, Real dt, std::vector<Triplet>& triplets) const;
    void append_elastic(const std::vector<Triplet>& elastic_triplets, std::vector<Triplet>& triplets);

    void ensure_contact_pattern(const ContactPair& contact);
    void append_contact_block(const ContactPair& contact,
                              int local_i,
                              int local_j,
                              const Mat3& block,
                              Real tolerance,
                              std::vector<Triplet>& triplets) const;

private:
    struct TierCache {
        std::vector<Index> rows;
        std::vector<Index> cols;
    };

    struct ContactPattern {
        std::array<Index, 4> key;
        int vertex_count = 0;
        std::vector<Index> rows;
        std::vector<Index> cols;
        std::vector<int> block_offsets;
    };

    Index dof_count_ = 0;
    TierCache mass_cache_;
    TierCache elastic_pattern_;
    std::unordered_map<size_t, ContactPattern> contact_cache_;

    size_t contact_key(const ContactPair& contact) const;
    static int block_entry_index(int vertex_count, int i, int j);
};

} // namespace ando_barrier
