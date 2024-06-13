#include "data_loader.h"

#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "log.h"

dataset_t *hri_dataset_init(const char *path) {
  DIR *directory = NULL;
  struct dirent *directory_entry = NULL;
  dataset_t *head = NULL, *builder = NULL;
  size_t path_length = strlen(path);

  if (!path || !strlen(path)) {
    log_error(
        "Invalid directory path. The path provided is either NULL or "
        "empty. Please ensure a valid path is specified.\n");
    return NULL;
  }

  if (!(directory = opendir(path))) {
    log_error(
        "Invalid directory path. Unable to open the provided "
        "directory. Please ensure a valid path is specified.\n");
    return NULL;
  }

  while (directory_entry = readdir(directory)) {
    /* Verify that directory entry is a traditional file */
    if (directory_entry->d_type != 8) /* d_type != DT_REG */
      continue;

    /* Allocate first, or next, entry in the chain */
    if (!builder)
      head = builder = malloc(sizeof(*builder));
    else
      builder = builder->next = malloc(sizeof(*builder));

    if (!builder) {
      log_fatal("Unable to allocate next node in dataset_t.\n");
      exit(EXIT_FAILURE);
    }

    builder->entry = malloc(strlen(directory_entry->d_name) + path_length + 2);
    if (!builder->entry) {
      log_fatal("Unable to allocate the node's data (d_name).\n");
      exit(EXIT_FAILURE);
    }

    sprintf(builder->entry, "%s/%s", path, directory_entry->d_name); 
    builder->entry[strlen(directory_entry->d_name) + path_length + 1] = '\0';
  }

  return head;
}
