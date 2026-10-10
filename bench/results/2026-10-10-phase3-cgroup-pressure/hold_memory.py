import time
# Touch and hold a bounded 4 GiB anonymous allocation for the external sampler.
size = 4 * 1024**3
buf = bytearray(size)
for i in range(0, size, 2 * 1024**2):
    buf[i] = 1
time.sleep(15)
print(f"held_bytes={len(buf)}")
