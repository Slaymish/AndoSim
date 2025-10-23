#include "matrix_assembly.h"

#include <algorithm>
#include <cmath>

namespace ando_barrier {

MatrixAssembly& MatrixAssembly::instance() {
    static MatrixAssembly cache;
    return cache;
}

void MatrixAssembly::configure(Index dof_count) {
    if (dof_count_ == dof_count && !mass_cache_.rows.empty()) {
        return;
    }

    dof_count_ = dof_count;
    mass_cache_.rows.resize(dof_count_);
    mass_cache_.cols.resize(dof_count_);
    for (Index i = 0; i < dof_count_; ++i) {
        mass_cache_.rows[i] = i;
        mass_cache_.cols[i] = i;
    }
}

void MatrixAssembly::append_mass(const State& state, Real dt, std::vector<Triplet>& triplets) const {
    if (dt <= static_cast<Real>(0.0) || mass_cache_.rows.empty()) {
        return;
    }

    Real dt_inv_sq = static_cast<Real>(1.0) / (dt * dt);
    for (Index idx = 0; idx < static_cast<Index>(mass_cache_.rows.size()); ++idx) {
        Index row = mass_cache_.rows[idx];
        Index vertex = row / 3;
        if (vertex < 0 || vertex >= static_cast<Index>(state.masses.size())) {
            continue;
        }
        Real value = state.masses[vertex] * dt_inv_sq;
        if (value == static_cast<Real>(0.0)) {
            continue;
        }
        triplets.emplace_back(row, row, value);
    }
}

void MatrixAssembly::append_elastic(const std::vector<Triplet>& elastic_triplets,
                                    std::vector<Triplet>& triplets) {
    if (elastic_pattern_.rows.size() != elastic_triplets.size()) {
        elastic_pattern_.rows.clear();
        elastic_pattern_.cols.clear();
        elastic_pattern_.rows.reserve(elastic_triplets.size());
        elastic_pattern_.cols.reserve(elastic_triplets.size());
        for (const auto& entry : elastic_triplets) {
            elastic_pattern_.rows.push_back(entry.row());
            elastic_pattern_.cols.push_back(entry.col());
        }
    }

    triplets.insert(triplets.end(), elastic_triplets.begin(), elastic_triplets.end());
}

size_t MatrixAssembly::contact_key(const ContactPair& contact) const {
    size_t hash = static_cast<size_t>(contact.type);
    hash = hash * 1315423911u + static_cast<size_t>(std::max(contact.vertex_count, 1));
    const std::array<Index, 4> indices = {contact.idx0, contact.idx1, contact.idx2, contact.idx3};
    for (Index idx : indices) {
        size_t value = static_cast<size_t>(idx + 1);
        hash ^= value + 0x9e3779b97f4a7c15ull + (hash << 6) + (hash >> 2);
    }
    return hash;
}

int MatrixAssembly::block_entry_index(int vertex_count, int i, int j) {
    return i * vertex_count + j;
}

void MatrixAssembly::ensure_contact_pattern(const ContactPair& contact) {
    size_t key = contact_key(contact);
    if (contact_cache_.find(key) != contact_cache_.end()) {
        return;
    }

    ContactPattern pattern;
    pattern.key = {contact.idx0, contact.idx1, contact.idx2, contact.idx3};
    pattern.vertex_count = std::max(contact.vertex_count, 1);
    int total_blocks = pattern.vertex_count * pattern.vertex_count;
    pattern.block_offsets.resize(total_blocks + 1, 0);

    const std::array<Index, 4> indices = {contact.idx0, contact.idx1, contact.idx2, contact.idx3};

    for (int i = 0; i < pattern.vertex_count; ++i) {
        for (int j = 0; j < pattern.vertex_count; ++j) {
            pattern.block_offsets[block_entry_index(pattern.vertex_count, i, j)] =
                static_cast<int>(pattern.rows.size());
            for (int r = 0; r < 3; ++r) {
                for (int c = 0; c < 3; ++c) {
                    Index row = indices[i] >= 0 ? indices[i] * 3 + r : -1;
                    Index col = indices[j] >= 0 ? indices[j] * 3 + c : -1;
                    pattern.rows.push_back(row);
                    pattern.cols.push_back(col);
                }
            }
        }
    }
    pattern.block_offsets[total_blocks] = static_cast<int>(pattern.rows.size());

    contact_cache_.emplace(key, std::move(pattern));
}

void MatrixAssembly::append_contact_block(const ContactPair& contact,
                                          int local_i,
                                          int local_j,
                                          const Mat3& block,
                                          Real tolerance,
                                          std::vector<Triplet>& triplets) const {
    size_t key = contact_key(contact);
    auto it = contact_cache_.find(key);
    if (it == contact_cache_.end()) {
        return;
    }

    const ContactPattern& pattern = it->second;
    if (local_i >= pattern.vertex_count || local_j >= pattern.vertex_count) {
        return;
    }

    int block_index = block_entry_index(pattern.vertex_count, local_i, local_j);
    int offset = pattern.block_offsets[block_index];

    for (int k = 0; k < 9; ++k) {
        Index row = pattern.rows[offset + k];
        Index col = pattern.cols[offset + k];
        if (row < 0 || col < 0) {
            continue;
        }
        int r = k / 3;
        int c = k % 3;
        Real value = block(r, c);
        if (std::abs(value) < tolerance) {
            continue;
        }
        triplets.emplace_back(row, col, value);
    }
}

} // namespace ando_barrier
