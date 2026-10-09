#pragma once
// Original independent test arithmetic. Never included by production code.
#include <cmath>
#include <cstdint>
#include <stdexcept>
namespace codec_oracle {
// IEEE binary16 value from integer significand and binary exponent, in FP64.
inline double half_value(uint16_t h) {
    const unsigned exp = (h >> 10) & 31, fraction = h & 1023;
    if (exp == 31) throw std::runtime_error("nonfinite scale outside this contract");
    double v = exp ? std::ldexp(double(1024+fraction), int(exp)-25)
                   : std::ldexp(double(fraction), -24);
    return std::copysign(v, (h & 32768) ? -1.0 : 1.0);
}
inline double positive_bf16(unsigned h) {
    const unsigned exp = h >> 7, fraction = h & 127;
    return exp ? std::ldexp(double(128+fraction), int(exp)-134)
               : std::ldexp(double(fraction), -133);
}
// Search adjacent represented numbers, compare FP64 distances, ties to even.
// This deliberately avoids the implementation's F32 bit-rounding addition.
inline uint16_t nearest_bf16(double x) {
    const unsigned sign = std::signbit(x) ? 32768 : 0;
    x = std::fabs(x);
    unsigned low = 0, high = 0x7f7f;
    while(low < high) {
        const unsigned mid = (low+high+1)/2;
        if(positive_bf16(mid) <= x) low = mid; else high = mid-1;
    }
    if(positive_bf16(low) == x) return uint16_t(sign | low);
    if (low >= 0x7f7f) throw std::runtime_error("oracle range exceeded");
    const double a = x-positive_bf16(low), b = positive_bf16(low+1)-x;
    const unsigned code = a < b ? low : b < a ? low+1 : (low & 1) ? low+1 : low;
    return uint16_t(sign | code);
}

inline uint16_t nearest_half(double x) {
    const unsigned sign = std::signbit(x) ? 32768 : 0;
    x = std::fabs(x);
    // IEEE nearest-even overflow threshold: halfway above finite max65504.
    if (x >= 65520.0) return uint16_t(sign | 0x7c00);
    unsigned low = 0, high = 0x7bff;
    while (low < high) {
        const unsigned mid = (low+high+1)/2;
        if (half_value(uint16_t(mid)) <= x) low=mid; else high=mid-1;
    }
    if (half_value(uint16_t(low)) == x || low == 0x7bff) return uint16_t(sign | low);
    const double a=x-half_value(uint16_t(low)), b=half_value(uint16_t(low+1))-x;
    const unsigned code=a<b ? low : b<a ? low+1 : (low&1) ? low+1 : low;
    return uint16_t(sign | code);
}
} // namespace codec_oracle
