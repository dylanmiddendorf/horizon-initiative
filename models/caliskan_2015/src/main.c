#include <stdio.h>
#include <string.h>

#include "data_loader.h"
#include "features/layout.h"

int main(int argc, char *argv[]) {
  (void)argc, (void)argv;
  FILE *csv = fopen("layout_features.csv", "wt");
  fprintf(csv, "id,f0,f1,f2,f3,f4,f5\n");

  char dir_path[] = "/home/ubuntu/research/horizon-initiative/dataset";
  dataset_t *d = hri_dataset_init(dir_path);
  hri_dataset_enumerate(d, s) {
    printf("e=%s, i=%ld\n", s.e, s.i);
    double *f = hri_layout_features(s.e);
    fprintf(csv, "%s,%lf,%lf,%lf,%lf,%d,%d\n", s.e, f[0], f[1], f[2], f[3],
            (int)f[4], (int)f[5]);
  }

  fclose(csv);
  return 0;
}