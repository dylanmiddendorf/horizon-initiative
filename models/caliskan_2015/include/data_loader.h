#ifndef LOADER_H
#define LOADER_H 1

typedef struct _dataset dataset_t;

#define hri_dataset_enumerate(d, i, e) \
  for (struct {size_t i, char *e} s = {0}; d && (s.e = d->entry); ++d, ++s.i)

struct _dataset {
  dataset_t *next;
  char *entry;
};

#endif