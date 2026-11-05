#pragma once

#include "strata/kernels/iq_kernels.hpp"

#include <cstddef>
#include <cstdint>

namespace strata::kernels {

/// Scratch for grouped NInfer-derived IQ2_S/IQ4_NL expert execution.
size_t ninfer_iq2s_iq4nl_workspace_bytes(int64_t cap_entries, int64_t n_ff) noexcept;
void ninfer_iq2s_iq4nl_backend_set(bool enabled) noexcept;
bool ninfer_iq2s_iq4nl_backend_enabled() noexcept;
uint64_t ninfer_iq2s_iq4nl_dispatch_count() noexcept;
void ninfer_iq3xxs_iq4nl_backend_set(bool enabled) noexcept;
bool ninfer_iq3xxs_iq4nl_backend_enabled() noexcept;
uint64_t ninfer_iq3xxs_iq4nl_dispatch_count() noexcept;
void ninfer_iq3s_iq4nl_backend_set(bool enabled) noexcept;
bool ninfer_iq3s_iq4nl_backend_enabled() noexcept;
uint64_t ninfer_iq3s_iq4nl_dispatch_count() noexcept;

/// Grouped resident expert path for IQ2_S gate/up + IQ4_NL down at 2560/640.
/// Descriptors and all buffers are caller-owned and remain live until the
/// supplied CUDA stream completes. Routing weights, shared experts and residual
/// addition remain owned by Strata.
void ninfer_iq2s_iq4nl_expert_grouped(const NativeExpertLayout& layout,
                                     const unsigned long long* grp_ptr,
                                     const int32_t* grp_start,
                                     const int32_t* n_groups,
                                     const int32_t* ent_dst,
                                     const int32_t* ent_tok,
                                     int64_t cap_groups,
                                     int64_t cap_entries,
                                     const void* x_q8_1,
                                     void* workspace,
                                     float* output,
                                     void* stream,
                                     int64_t grid_groups = 0);

/// Grouped resident expert path for IQ3_XXS gate/up + IQ4_NL down at 2560/640.
void ninfer_iq3xxs_iq4nl_expert_grouped(const NativeExpertLayout& layout,
                                        const unsigned long long* grp_ptr,
                                        const int32_t* grp_start,
                                        const int32_t* n_groups,
                                        const int32_t* ent_dst,
                                        const int32_t* ent_tok,
                                        int64_t cap_groups,
                                        int64_t cap_entries,
                                        const void* x_q8_1,
                                        void* workspace,
                                        float* output,
                                        void* stream,
                                        int64_t grid_groups = 0);

/// Grouped resident expert path for IQ3_S gate/up + IQ4_NL down at 2560/640.
void ninfer_iq3s_iq4nl_expert_grouped(const NativeExpertLayout& layout,
                                      const unsigned long long* grp_ptr,
                                      const int32_t* grp_start,
                                      const int32_t* n_groups,
                                      const int32_t* ent_dst,
                                      const int32_t* ent_tok,
                                      int64_t cap_groups,
                                      int64_t cap_entries,
                                      const void* x_q8_1,
                                      void* workspace,
                                      float* output,
                                      void* stream,
                                      int64_t grid_groups = 0);

} // namespace strata::kernels
