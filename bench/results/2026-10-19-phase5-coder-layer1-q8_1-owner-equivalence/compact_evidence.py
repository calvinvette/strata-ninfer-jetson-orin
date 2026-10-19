#!/usr/bin/env python3
"""Losslessly deduplicate the identical GDN dumps and gzip JSONL evidence."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PART_BYTES = 64 * 1024 * 1024


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    dumps = sorted(HERE.rglob("prefill-gdn.bin"))
    if dumps:
        hashes = {path: sha256(path) for path in dumps}
        unique = set(hashes.values())
        if len(unique) != 1:
            raise RuntimeError(f"GDN dumps differ; retain all originals: {unique}")
        digest = next(iter(unique))
        size = dumps[0].stat().st_size
        for path, value in hashes.items():
            request_path = path.parent / "requests.json"
            request = json.loads(request_path.read_text())
            request["prefill_gdn_sha256"] = value
            request["prefill_gdn_bytes"] = size
            request_path.write_text(json.dumps(request, indent=2) + "\n")

        source = dumps[0]
        remaining = size
        parts = []
        with source.open("rb") as stream:
            index = 0
            while remaining:
                amount = min(PART_BYTES, remaining)
                target = HERE / f"prefill-gdn-reference.part{index:02d}"
                with target.open("wb") as output:
                    left = amount
                    while left:
                        data = stream.read(min(left, 8 * 1024 * 1024))
                        if not data:
                            raise RuntimeError("unexpected EOF while splitting GDN dump")
                        output.write(data)
                        left -= len(data)
                parts.append(target)
                remaining -= amount
                index += 1
        h = hashlib.sha256()
        for path in parts:
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    h.update(block)
        if h.hexdigest() != digest:
            raise RuntimeError("split GDN reference does not reconstruct the original")
        for path in dumps:
            path.unlink()
    else:
        parts = sorted(HERE.glob("prefill-gdn-reference.part*"))
        if not parts:
            raise RuntimeError("no raw GDN dumps or retained reference parts found")
        h = hashlib.sha256()
        size = 0
        for path in parts:
            size += path.stat().st_size
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    h.update(block)
        digest = h.hexdigest()

    text_files = sorted(HERE.rglob("*.jsonl"))
    for path in text_files:
        target = Path(str(path) + ".gz")
        with path.open("rb") as source_stream, target.open("wb") as raw_target:
            with gzip.GzipFile(filename="", mode="wb", compresslevel=1,
                               fileobj=raw_target, mtime=0) as output:
                for block in iter(lambda: source_stream.read(1024 * 1024), b""):
                    output.write(block)
        with gzip.open(target, "rb") as compressed:
            if hashlib.sha256(compressed.read()).hexdigest() != sha256(path):
                target.unlink()
                raise RuntimeError(f"gzip verification failed for {path}")
        path.unlink()

    def preserve_shared(paths, name):
        paths = [path for path in paths if path.exists()]
        if not paths:
            return 0
        contents = [gzip.open(path, "rb").read() if path.suffix == ".gz" else path.read_bytes()
                    for path in paths]
        hashes = [hashlib.sha256(data).hexdigest() for data in contents]
        same = len(set(hashes)) == 1
        shared = HERE / "shared-captures" / name if same else None
        if shared is not None:
            shared.parent.mkdir(exist_ok=True)
            if not shared.exists():
                shared.write_bytes(paths[0].read_bytes())
        if name.startswith("routes-all-layers-"):
            key = "routes_all_layers"
        elif name.startswith("cpu-outputs-layer1-"):
            key = "cpu_outputs_layer1"
        elif name == "device-moe-routes-layer1.jsonl.gz":
            key = "device_moe_routes_layer1"
        elif name == "combined-moe.bin":
            key = "combined_moe"
        else:
            key = None
        if key is None:
            raise RuntimeError(f"unrecognized capture type: {name}")
        for index, path in enumerate(paths):
            request_path = path.parent / "requests.json"
            if request_path.exists():
                request = json.loads(request_path.read_text())
                captures = request.setdefault("capture_artifacts", {})
                artifact = shared if shared is not None else path
                captures[key] = {"path": str(artifact.relative_to(HERE)),
                                 "sha256": hashes[0] if same else hashes[index],
                                 "bytes": len(contents[0]) if same else len(contents[index])}
                request_path.write_text(json.dumps(request, indent=2) + "\n")
            if shared is not None:
                path.unlink()
        return len(paths)

    shared_count = 0
    for arm in ("cpu_mirror", "gpu_layer1"):
        route_paths = sorted((HERE / "paired-runs").glob(f"block-*/{arm}/run/routes-all-layers.jsonl.gz"))
        route_paths += sorted((HERE / "device-route-pair-retry1").glob(f"{arm}/run/routes-all-layers.jsonl.gz"))
        shared_count += preserve_shared(route_paths, f"routes-all-layers-{arm}.jsonl.gz")
        output_paths = sorted((HERE / "paired-runs").glob(f"block-*/{arm}/run/cpu-outputs-layer1.jsonl.gz"))
        output_paths += sorted((HERE / "device-route-pair-retry1").glob(f"{arm}/run/cpu-outputs-layer1.jsonl.gz"))
        shared_count += preserve_shared(output_paths, f"cpu-outputs-layer1-{arm}.jsonl.gz")
    combined_paths = sorted(HERE.glob("**/run/combined-moe.bin"))
    shared_count += preserve_shared(combined_paths, "combined-moe.bin")
    device_paths = sorted(HERE.glob("device-route-pair-retry1/*/run/device-moe-routes.jsonl.gz"))
    shared_count += preserve_shared(device_paths, "device-moe-routes-layer1.jsonl.gz")

    zstd_dump = HERE / "prefill-gdn-reference.bin.zst"
    if zstd_dump.exists():
        zstd_dump.unlink()
    print(json.dumps({"gdn_sha256": digest, "gdn_bytes": size,
                      "gdn_reference_parts": [str(path.relative_to(HERE)) for path in parts],
                      "gdn_run_copies_removed": len(dumps),
                      "jsonl_files_gzipped": len(text_files),
                      "duplicate_capture_files_removed": shared_count}, indent=2))


if __name__ == "__main__":
    main()
