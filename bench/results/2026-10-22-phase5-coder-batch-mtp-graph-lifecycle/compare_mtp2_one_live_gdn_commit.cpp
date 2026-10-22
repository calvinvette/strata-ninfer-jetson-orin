// Compare one serial and one batch STGCMT1 commit at the same position/token.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
struct H { char magic[8]; uint32_t version; int32_t layer; int64_t position; uint64_t recurrent, count; int32_t token, slot; };
struct R { H h{}; std::vector<float> values; };
std::vector<R> read(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open " + path);
    std::vector<R> rows;
    for (;;) {
        R row;
        f.read(reinterpret_cast<char*>(&row.h), sizeof(row.h));
        if (f.eof()) break;
        if (!f || std::memcmp(row.h.magic, "STGCMT1", 7) || row.h.version != 1)
            throw std::runtime_error("invalid STGCMT1 header in " + path);
        row.values.resize(static_cast<size_t>(row.h.count));
        f.read(reinterpret_cast<char*>(row.values.data()), static_cast<std::streamsize>(row.values.size() * sizeof(float)));
        if (!f) throw std::runtime_error("truncated STGCMT1 payload in " + path);
        rows.push_back(std::move(row));
    }
    return rows;
}
int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("usage: comparator SERIAL.stgcmt BATCH.stgcmt");
        const auto serial = read(argv[1]);
        const auto batch = read(argv[2]);
        using Key = std::tuple<int, int64_t, int>;
        std::map<Key, const R*> reference;
        for (const auto& row : serial) reference[{row.h.layer, row.h.position, row.h.token}] = &row;
        uint64_t changed = 0, total = 0;
        double error = 0.0, reference_norm = 0.0;
        double max_abs = 0.0;
        int first_layer = -1, layers = 0;
        int64_t position = -1;
        int32_t token = -1;
        for (const auto& row : batch) {
            auto it = reference.find({row.h.layer, row.h.position, row.h.token});
            if (it == reference.end()) continue;
            const auto& ref = *it->second;
            if (row.values.size() != ref.values.size()) throw std::runtime_error("state geometry mismatch");
            position = row.h.position;
            token = row.h.token;
            ++layers;
            bool layer_changed = false;
            for (size_t i = 0; i < row.values.size(); ++i) {
                const double a = ref.values[i];
                const double d = static_cast<double>(row.values[i]) - a;
                if (d != 0.0) { ++changed; layer_changed = true; }
                ++total;
                error += d * d;
                reference_norm += a * a;
                max_abs = std::max(max_abs, std::abs(d));
            }
            if (layer_changed && first_layer < 0) first_layer = row.h.layer;
        }
        if (!layers) throw std::runtime_error("no exact position/token state pair");
        std::cout << "position=" << position << " token=" << token << " layers=" << layers
                  << " changed=" << changed << "/" << total
                  << " relative_l2=" << std::sqrt(error / reference_norm)
                  << " max_abs=" << max_abs << " first_changed_layer=" << first_layer << "\n";
        return layers == 36 ? 0 : 2;
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
        return 1;
    }
}
