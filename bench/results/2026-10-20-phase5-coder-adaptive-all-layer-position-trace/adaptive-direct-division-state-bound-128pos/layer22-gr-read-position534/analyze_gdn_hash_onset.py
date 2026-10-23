#!/usr/bin/env python3
"""Find the first initial/recovery accepted-prefix GDN/QSA hash divergence."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

GDN_MODEL_LAYERS = [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18,
                    20, 21, 22, 24, 25, 26, 28, 29, 30, 32, 33, 34, 36, 37,
                    38, 40, 41, 42, 44, 45, 46]
ACCEPTED = re.compile(r"ACCEPTED_PREFIX position=(\d+)")
QSA = re.compile(r"layer=(\d+) hash=([0-9a-f]+)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gdn_rows = defaultdict(list)
    qsa_rows = defaultdict(list)
    pending_gdn = pending_qsa = None
    for line in args.service_log.read_text().splitlines():
        if "STATE_HASH_GDN " in line:
            pending_gdn = line.split("STATE_HASH_GDN ", 1)[1].split()
            continue
        if "STATE_HASH_QSA_LAYERS " in line:
            pending_qsa = {int(layer): value for layer, value in QSA.findall(line)}
            continue
        match = ACCEPTED.search(line)
        if match:
            if pending_gdn is None or pending_qsa is None:
                raise ValueError("accepted-prefix row missing per-layer state hashes")
            position = int(match.group(1))
            gdn_rows[position].append(pending_gdn)
            qsa_rows[position].append(pending_qsa)
            pending_gdn = pending_qsa = None
    first = None
    for position in sorted(gdn_rows):
        gdn = gdn_rows[position]
        qsa = qsa_rows[position]
        if len(gdn) < 2 or len(qsa) < 2:
            continue
        if len(gdn[0]) != len(GDN_MODEL_LAYERS):
            raise ValueError(f"position {position}: unexpected GDN hash count {len(gdn[0])}")
        changed_gdn = [GDN_MODEL_LAYERS[i] for i, (a, b) in enumerate(zip(gdn[0], gdn[-1])) if a != b]
        changed_qsa = sorted(layer for layer in qsa[0] if qsa[0][layer] != qsa[-1][layer])
        if changed_gdn or changed_qsa:
            first = {"position": position, "record_count": len(gdn),
                     "first_changed_gdn_model_layer": changed_gdn[0] if changed_gdn else None,
                     "changed_gdn_model_layers": changed_gdn,
                     "changed_qsa_model_layers": changed_qsa}
            break
    result = {"scope": "initial/recovery per-layer accepted-prefix state-hash comparison",
              "accepted_positions": len(gdn_rows), "first_divergence": first,
              "limit": "hash localization; raw persistent-state capture is required to report numerical state deltas"}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
