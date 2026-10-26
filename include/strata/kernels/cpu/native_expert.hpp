// include/strata/kernels/cpu/native_expert.hpp - plan v0.3 P6: one routed expert in its GGUF form on the CPU.
//
// The IQ2_XS / IQ3_XXS model files keep their experts in i-quant formats (IQ1_M, IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS,
// IQ3_S gate/up; Q2_0 or IQ4_NL down) whose values cannot be re-expressed in the Q2_0 pack form.  A native expert
// blob is the three GGUF slices back to back, [gate rows | up rows | down rows], and the arithmetic is ggml-cpu's
// own (`ggml_get_type_traits_cpu`): the activation is quantized with the weight type's `vec_dot_type` and each row
// is one `vec_dot`, exactly what llama.cpp's CPU backend computes for the same tensor.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace strata::kernels::cpu {

/// Bytes of the largest quantized activation any native layer uses (2560 values as Q8_K: 10 x 292).
inline constexpr size_t kNativeActBytes = 4096;
/// Bytes of the largest quantized down activation (640 values as Q8_0: 20 x 34, or Q8_K 3 x 292).
inline constexpr size_t kNativeHBytes = 1024;

/// One layer's native expert geometry.
struct NativeFmt {
    int gu_type = -1, d_type = -1;      ///< ggml types of gate/up and of down
    int gu_act = -1, d_act = -1;        ///< their vec_dot_type (the activation formats)
    int gu_act_default = -1, d_act_default = -1; ///< original vec_dot formats before diagnostic overrides
    std::vector<int> q8_1_dot_expert_ids; ///< optional expert filter for the Q8_1 arithmetic mirror
    bool q8_1_reciprocal_silu = false;  ///< opt-in CUDA-order SiLU expression for selected Q8_1 routes
    int q8_1_reciprocal_silu_expert = -1; ///< optional model expert ID filter
    bool q8_1_exp2f_silu = false; ///< opt-in host-exp2f SiLU candidate for selected Q8_1 routes
    int q8_1_exp2f_silu_expert = -1; ///< optional model expert ID filter
    int64_t n_embd = 0, n_ff = 0;
    size_t gu_row = 0, d_row = 0;       ///< bytes per weight row
    size_t up_off = 0, down_off = 0;    ///< inside the blob
    size_t bytes = 0;                   ///< the whole blob
    size_t act_bytes = 0, h_bytes = 0;  ///< quantized activation sizes (n_embd of gu_act, n_ff of d_act)
};

/// Whether this build has the ggml-cpu path.
bool native_experts_available() noexcept;
/// Fills `f` for a layer; false (with a reason) when ggml-cpu has no dot product for a type. The opt-in
/// STRATA_NATIVE_CPU_Q8_1_DOT diagnostic selects CUDA-matching Q8_1 routes for IQ2_S/Q2_0,
/// IQ2_S/IQ4_NL, IQ3_XXS/Q2_0, IQ3_XXS/IQ4_NL, IQ3_S/Q2_0 and IQ3_S/IQ4_NL expert pairs (`1` enables all supported pairs; a
/// pair name selects one). A pair may be suffixed with `@layer=N` to scope it to one zero-based model layer. The
/// optional `STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS` ID filter further limits selected rows. A comma-separated list is
/// global to all selected layers; `layer=ID,ID;layer=ID,ID` clauses scope distinct lists per selected layer.
/// Unlisted experts keep their original activation formats. It is not a default dispatch policy.
bool native_fmt(int gu_type, int d_type, int64_t n_embd, int64_t n_ff, NativeFmt& f, std::string& err, int layer = -1);
/// Resolve a layer format for one expert when the opt-in Q8_1 mirror has an expert filter.
void native_fmt_for_expert(const NativeFmt& f, int expert_id, NativeFmt& out);
bool native_q8_1_dot_expert_selected(const NativeFmt& f, int expert_id) noexcept;

/// x (n_embd floats) -> the gate/up activation (act_bytes).
void native_quant_act(const NativeFmt& f, const float* x, void* dst);
/// h (n_ff floats) -> the down activation (h_bytes).
void native_quant_h(const NativeFmt& f, const float* h, void* dst);

/// From how many tokens native_gu_rows gives this gate/up type to a multi-token kernel (#152; ggml-cpu's per-token dot
/// below that).  1: a token's rows are the same alone and in any group.
int native_gu_mt_min(int gu_type);
/// ff[t][r] = silu(gate_r . a[t]) * (up_r . a[t]) for rows r in [r0, r1), `nt` tokens.
void native_gu_rows(const NativeFmt& f, const uint8_t* blob, const void* const* act, int nt, float* const* ff,
                    int r0, int r1);
/// out[t][r] = down_r . hq[t] for rows r in [r0, r1).
void native_down_rows(const NativeFmt& f, const uint8_t* blob, const void* const* hq, int nt, float* const* out,
                      int r0, int r1);

}  // namespace strata::kernels::cpu
