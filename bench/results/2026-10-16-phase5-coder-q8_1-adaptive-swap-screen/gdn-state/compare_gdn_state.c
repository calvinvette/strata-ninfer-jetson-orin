#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float *load(const char *path, uint64_t *cells, uint64_t *layers,
                   uint64_t *per_layer) {
  FILE *f = fopen(path, "rb");
  char magic[8];
  if (!f || fread(magic, 1, 8, f) != 8 ||
      fread(cells, 8, 1, f) != 1 || fread(layers, 8, 1, f) != 1 ||
      fread(per_layer, 8, 1, f) != 1 || memcmp(magic, "STGDN01\0", 8)) {
    fprintf(stderr, "invalid GDN dump: %s\n", path);
    exit(2);
  }
  uint64_t count = *layers * *per_layer;
  float *data = malloc(count * sizeof(float));
  if (!data || fread(data, sizeof(float), count, f) != count || fgetc(f) != EOF) {
    fprintf(stderr, "invalid GDN payload: %s\n", path);
    exit(2);
  }
  fclose(f);
  return data;
}

int main(int argc, char **argv) {
  if (argc != 3) return 2;
  uint64_t c0, l0, n0, c1, l1, n1;
  float *a = load(argv[1], &c0, &l0, &n0);
  float *b = load(argv[2], &c1, &l1, &n1);
  if (c0 != c1 || l0 != l1 || n0 != n1) return 3;
  double diff2 = 0, ref2 = 0, abs1 = 0, max_abs = 0;
  uint64_t changed = 0, count = l0 * n0;
  for (uint64_t i = 0; i < l0; ++i) {
    double layer_diff2 = 0, layer_ref2 = 0, layer_max = 0;
    uint64_t layer_changed = 0;
    for (uint64_t j = 0; j < n0; ++j) {
      uint64_t k = i * n0 + j;
      double delta = (double)b[k] - a[k], ref = a[k], ad = fabs(delta);
      if (ad) ++layer_changed, ++changed;
      if (ad > layer_max) layer_max = ad;
      if (ad > max_abs) max_abs = ad;
      layer_diff2 += delta * delta;
      layer_ref2 += ref * ref;
      diff2 += delta * delta;
      ref2 += ref * ref;
      abs1 += ad;
    }
    printf("layer %llu changed %llu relative_l2 %.12g max_abs %.12g\n",
           (unsigned long long)i, (unsigned long long)layer_changed,
           sqrt(layer_diff2) / sqrt(layer_ref2), layer_max);
  }
  printf("overall count %llu changed %llu fraction %.12g relative_l2 %.12g "
         "max_abs %.12g mean_abs %.12g\n",
         (unsigned long long)count, (unsigned long long)changed,
         (double)changed / count, sqrt(diff2) / sqrt(ref2), max_abs,
         abs1 / count);
  free(a);
  free(b);
  return 0;
}
