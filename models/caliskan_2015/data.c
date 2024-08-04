/* data.c -- Facilities for managing data loading.
 *
 * Copright (C) 2024 Dylan Middendorf
 * SPDX-License-Identifier: BSD-2-Clause
 */

#include "data.h"

#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

/* TODO: optimization (1) keep file (2) chunk file (8kb) */

#define _DATA_ERROR(fmt, ...)                                                 \
  do                                                                          \
    {                                                                         \
      fprintf (stderr, "\x1b[31m[ERROR  ]\x1b[0m %s: ", __func__);        \
      fprintf (stderr, fmt __VA_OPT__ (, ) __VA_ARGS__);                      \
      fprintf (stderr, "\n");                                                 \
    }                                                                         \
  while (0)

static int
_hdl_glob_error_handle (const char *filename, int error_code)
{
  _DATA_ERROR ("unable to read \"%s\" (error=%d)", filename, error_code);
  return 1; /* Don't attempt the resolve the issue (fail out) */
}

int
hdl_init (data_loader_t *loader, const char *pattern,
          data_loader_config_t *config)
{
  int status = glob (pattern, 0, _hdl_glob_error_handle, &loader->index);
  if (status)
    {
      _DATA_ERROR ("error while globbing (error=%d)", status);
      return status; /* Alert the user of any `glob` wrongdoings... */
    }

  loader->next_entry = 0; /* Ensure that next_entry is 0 */
  loader->data = calloc (loader->index.gl_pathc, sizeof (*loader->data));
  if (!loader->data)
    {
      _DATA_ERROR ("unable to allocated loader->data (errno=%d)", errno);
      return -1; /* Utilize negative(s) to differentiate from `glob` */
    }

  return status;
}

void
hdl_fini (data_loader_t *loader)
{
  for (size_t i = 0; i < loader->index.gl_pathc; ++i)
    {
      if (loader->data[i] == NULL)
        break; /* The `data` array is null terminated (if partially full) */
      free (loader->data[i]);
    }

  free (loader->data);
  globfree (&loader->index);
}

char *
hdl_next (data_loader_t *loader)
{
  struct stat st; /* stat(...) will populate all the fields */

  int status = stat (loader->index.gl_pathv[loader->next_entry], &st);
  assert (status == 0); /* File is assumed to exist before call */

  loader->data[loader->next_entry] = malloc (st.st_size + 1);
  if (!loader->data[loader->next_entry])
    {
      _DATA_ERROR ("unable to allocate buffer for loader->data[loader->"
                   "next_entry] (errno=%d)",
                   errno);
      return NULL;
    }

  FILE *stream = fopen (loader->index.gl_pathv[loader->next_entry], "rt");
  if (!stream)
    {
      _DATA_ERROR ("unable to open \"%s\"",
                   loader->index.gl_pathv[loader->next_entry]);
      return NULL;
    }

  int n = fread (loader->data[loader->next_entry], 1, st.st_size, stream);
  fclose (stream);          /* Limit resource usage times */
  assert (n == st.st_size); /* Make sure the entire file was read */
  loader->data[loader->next_entry][st.st_size] = '\0';

  return loader->data[loader->next_entry++];
}

inline bool
hdl_has_next (data_loader_t *loader)
{
  return loader->next_entry < loader->index.gl_pathc;
}

size_t
hdl_size (data_loader_t *loader)
{
  return loader->index.gl_pathc;
}
