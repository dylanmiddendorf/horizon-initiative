#ifndef CTOK_H
#define CTOK_H

#include <stdbool.h>
#include <stddef.h>

#include "strpool.h"

typedef struct _cpp_tokenizer
{
  const char *str;
  int max_position;

  int current_position;
  int next_position;

  /* This */
  strpool_t *pool;
  bool external_pool;

  /* This field isn't necessary for typical operations, but was included to
  extract features for the model described Caliskan et al 2015. */
  int n_comments;
} cpp_tokenizer_t;

typedef struct _tokenizer_config
{
  strpool_t *pool;
} tokenizer_config_t;

void cxt_init (cpp_tokenizer_t *tok, const char *source,
               tokenizer_config_t *config);
void cxt_fini (cpp_tokenizer_t *tok);

int cxt_count_tokens (cpp_tokenizer_t *tok);
bool cxt_has_more_tokens (cpp_tokenizer_t *tok);
const char *cxt_next_token (cpp_tokenizer_t *tok);

#endif