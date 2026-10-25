#pragma once

#include "strata/kernels/iq_kernels.hpp"

#include <cstddef>
#include <cstdint>

namespace strata::kernels {

/// Workspace bytes for one Flash-Next Q2_0 routed expert (640 FP32 hidden values).
size_t ninfer_q2_0_expert_workspace_bytes() noexcept;
void ninfer_q2_0_expert_backend_set(bool enabled, bool strict) noexcept;
bool ninfer_q2_0_expert_backend_enabled() noexcept;
bool ninfer_q2_0_expert_backend_strict() noexcept;
uint64_t ninfer_q2_0_expert_dispatch_count() noexcept;

/// NInfer-derived single-token D3/D4 expert computation for the exact
/// Flash-Next Q2_0 geometry. Weight pointers refer to one expert's raw GGUF
/// tensors: gate/up rows are [640,2560], down rows [2560,640]. `x`, `workspace`
/// and `output` are caller-owned device allocations. The call enqueues on the
/// supplied stream, allocates nothing, synchronizes nothing, and emits an
/// unweighted output row without shared-expert or residual work.
void ninfer_q2_0_expert(const void* gate_q2_0, const void* up_q2_0, const void* down_q2_0,
                        const float* x, float* workspace, float* output, void* stream);

/// Grouped resident-cache form matching Strata's selected expert rows. The
/// workspace size follows native_expert_scratch_bytes(cap_entries,L.n_ff).
/// Q8_1 activation rows and all descriptor arrays are caller owned and remain
/// live until stream completion. Only Q2_0/Q2_0 at 2560/640 is accepted.
void ninfer_q2_0_expert_grouped(const NativeExpertLayout& L, const unsigned long long* grp_ptr,
                               const int32_t* grp_start, const int32_t* n_groups,
                               const int32_t* ent_dst, const int32_t* ent_tok,
                               int64_t cap_groups, int64_t cap_entries, const void* x_q8_1,
                               void* workspace, float* output, void* stream, int64_t grid_groups = 0);

} // namespace strata::kernels
