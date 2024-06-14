#include "features/lexical.h"

#include <stdio.h>
#include <sys/stat.h>

#include "log_lite.h"
#include "tokenizer.h"

map_t* hri_lexical_features(const char* fname) {
  ctok_t* ctok = ctok_init(fname);
  map_t* map = map_init();

  if (!ctok || !map) {
    ll_log_critical("unable to initalize C++ tokenizer or map");
    goto error;
  }

  /* Tokenize the source file */
  ctok_tokenize(ctok);
  for (size_t i = 0; i < ctok->tokens->size; ++i) {
    int prev = map_get(map, ctok->tokens->data[i]);
    map_put(map, ctok->tokens->data[i], prev + 1);
  }

  return map;

error:
  if (ctok) free(ctok);
  if (map) free(map);
}