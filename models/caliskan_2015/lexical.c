#include "lexical.h"

#include <assert.h>
#include <glob.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

#include "ctok.h"
#include "data.h"
#include "map.h"
#include "strpool.h"

void
hri_extract_lexical_features (data_loader_t *loader)
{
  strpool_t pool = { 0 };
  tokenizer_config_t ctok_config = { .pool = &pool };

  scp_init (&pool, NULL);
  while (hdl_has_next (loader))
    {
      cpp_tokenizer_t tok = { 0 };
      const char *source = hdl_next (loader);
      cxt_init (&tok, source, &ctok_config);
      while (cxt_has_more_tokens (&tok))
        cxt_next_token (&tok);
    }

  FILE *csv_stream = fopen ("lexical.csv", "w+t");
  fputs("author,", csv_stream);
  for (size_t i = 0; i < pool.capacity; ++i)
    if (pool.table[i].key != NULL)
      fprintf (csv_stream, "%08x,", pool.table[i].hash);
  fprintf (csv_stream, "\n");

  for (size_t i = 0; i < loader->index.gl_pathc; ++i)
    {
      size_t count = 0;
      map_t *map = map_init ();
      cpp_tokenizer_t tok = { 0 };
      cxt_init (&tok, loader->data[i], &ctok_config);
      for (; cxt_has_more_tokens (&tok); ++count)
        {
          const char *token = cxt_next_token (&tok);
          uint32_t prev_value = map_get (map, token);
          map_put (map, token, prev_value + 1);
        }

      fprintf(csv_stream, "%s,", loader->index.gl_pathv[i]);
      for (size_t i = 0; i < pool.capacity; ++i)
        if (pool.table[i].key != NULL)
          {
            float freq = (float)map_get (map, pool.table[i].key);
            fprintf (csv_stream, "%.5f,", freq / count);
          }
      fseek(csv_stream, SEEK_CUR, -1);
      fprintf (csv_stream, "\n");
    }
  fclose (csv_stream);

  printf ("N tokens: %d\n", pool.size);
  scp_fini (&pool);
}