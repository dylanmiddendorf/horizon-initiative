#ifndef DATASET_H
#define DATASET_H 1

#include <glob.h>
#include <stdbool.h>
#include <stddef.h>

typedef struct _data_loader
{
  glob_t index;
  char **data;
  size_t next_entry;
} data_loader_t;

typedef struct _data_loader_config
{
  bool sort;
} data_loader_config_t;

int hdl_init (data_loader_t *loader, const char *pattern,
              data_loader_config_t *config);
void hdl_fini (data_loader_t *loader);
char *hdl_next (data_loader_t *loader);
bool hdl_has_next (data_loader_t *loader);
size_t hdl_size (data_loader_t *loader);

#endif