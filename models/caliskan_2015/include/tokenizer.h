#ifndef TOKENIZER_H
#define TOKENIZER_H 1

#include <stdint.h>

#include "vector.h"

VECTOR_TYPEDEF_IMPORT(ctok_vector, char *)

typedef enum _ctok_mode {
  CTOK_NORMAL_MODE,
  CTOK_CHARACTER_LITERAL_MODE,
  CTOK_STRING_LITERAL_MODE,
  CTOK_MULTI_LINE_COMMENT_MODE,
  CTOK_SINGLE_LINE_COMMENT_MODE,
  CTOK_OPERATOR_MODE,
} ctok_mode_t;

typedef struct _ctok {
  /* Tempararily used when tokenizing the file */
  char *file_buffer;
  size_t file_size;

  char *token_buffer;
  size_t buffer_size;
  size_t buffer_capacity;

  ctok_vector_t *tokens;
  size_t token_count;

  /* Used for the finite state machine while tokenizing */
  ctok_mode_t mode;

  /* Auxilary features used within the CAA model */
  uint32_t _n_comments;
} ctok_t;

ctok_t *ctok_init(char *fname);
void ctok_tokenize(ctok_t *ctok);

#endif