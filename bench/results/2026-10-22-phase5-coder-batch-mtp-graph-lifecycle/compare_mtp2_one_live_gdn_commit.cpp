// Compare exact position/token GDN commit records, retaining repeated captures.
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
using Key = std::tuple<int64_t, int32_t, int32_t>;
using Group = std::vector<const R*>;
using Groups = std::map<Key, std::vector<Group>>;
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
        f.read(reinterpret_cast<char*>(row.values.data()),
               static_cast<std::streamsize>(row.values.size() * sizeof(float)));
        if (!f) throw std::runtime_error("truncated STGCMT1 payload in " + path);
        rows.push_back(std::move(row));
    }
    return rows;
}
Groups group_records(const std::vector<R>& rows) {
    Groups result;
    Key key{};
    Group group;
    int last_layer = -1;
    auto flush = [&] { if (!group.empty()) result[key].push_back(group); group.clear(); };
    for (const auto& row : rows) {
        const Key next{row.h.position, row.h.token, row.h.slot};
        if (group.empty() || next != key || row.h.layer <= last_layer) {
            flush(); key = next; last_layer = -1;
        }
        group.push_back(&row);
        last_layer = row.h.layer;
    }
    flush();
    return result;
}
int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("usage: comparator SERIAL.stgcmt BATCH.stgcmt");
        const auto serial_rows = read(argv[1]);
        const auto batch_rows = read(argv[2]);
        const auto serial = group_records(serial_rows);
        const auto batch = group_records(batch_rows);
        int incomplete = 0;
        for (const auto& entry : batch) {
            const auto& key = entry.first;
            const auto refs = serial.find(key);
            for (size_t occurrence = 0; occurrence < entry.second.size(); ++occurrence) {
                if (refs == serial.end() || occurrence >= refs->second.size()) {
                    std::cout << "position=" << std::get<0>(key) << " token=" << std::get<1>(key)
                              << " capture=" << occurrence << " no-serial-pair\n";
                    incomplete = 1;
                    continue;
                }
                uint64_t changed = 0, total = 0;
                double error = 0.0, reference_norm = 0.0, max_abs = 0.0;
                int first_layer = -1, layers = 0;
                for (const auto* row : entry.second[occurrence]) {
                    const auto& refs_in_capture = refs->second[occurrence];
                    const auto it = std::find_if(refs_in_capture.begin(), refs_in_capture.end(),
                        [&](const R* ref) { return ref->h.layer == row->h.layer; });
                    if (it == refs_in_capture.end()) continue;
                    const auto* ref = *it;
                    if (row->values.size() != ref->values.size())
                        throw std::runtime_error("state geometry mismatch");
                    ++layers;
                    for (size_t i = 0; i < row->values.size(); ++i) {
                        const double a = ref->values[i];
                        const double d = static_cast<double>(row->values[i]) - a;
                        if (d != 0.0) { ++changed; if (first_layer < 0) first_layer = row->h.layer; }
                        ++total; error += d * d; reference_norm += a * a;
                        max_abs = std::max(max_abs, std::abs(d));
                    }
                }
                std::cout << "position=" << std::get<0>(key) << " token=" << std::get<1>(key)
                          << " capture=" << occurrence << " layers=" << layers
                          << " changed=" << changed << "/" << total
                          << " relative_l2=" << (reference_norm ? std::sqrt(error / reference_norm) : 0.0)
                          << " max_abs=" << max_abs << " first_changed_layer=" << first_layer << "\n";
                if (layers != 36) incomplete = 1;
            }
        }
        return incomplete ? 2 : 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
        return 1;
    }
}
