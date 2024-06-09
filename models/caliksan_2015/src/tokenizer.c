#include "tokenizer.h"

#include <assert.h>
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

#include "log_lite.h"

// TODO: tokenize <..> same as ""
// TODO: tokenize #include as 1 token
// TODO: tokenize #define as 1 token

#define _CTOK_BUFSIZ 0x100UL

#define _CTOK_MAX(a, b)     \
  ({                        \
    __typeof__(a) _a = (a); \
    __typeof__(b) _b = (b); \
    _a > _b ? _a : _b;      \
  })

const char *ctok_operators[] = {
    "{",  "}",  "[",  "]",    "#",   "##",  "(",   ")",   "<:", ":>",
    "<%", "%>", "%:", "%:%:", ";",   ":",   "...", "?",   "::", ".",
    ".*", "+",  "-",  "*",    "/",   "%",   "^",   "&",   "|",  "~",
    "!",  "=",  "<",  ">",    "+=",  "-=",  "*=",  "/=",  "%=", "^=",
    "&=", "|=", "<<", ">>",   ">>=", "<<=", "==",  "!=",  "<=", ">=",
    "&&", "||", "++", "--",   ",",   "->*", "->",  "%:%", ".."};

VECTOR_INIT(ctok_vector, char *)

static void _ctok_process_token(ctok_t *ctok, size_t from, size_t to);

ctok_t *ctok_init(char *fname) {
  ctok_t *ctok;

  FILE *file;
  struct stat statbuf;

  /* Verify that the file exists and can be read */
  if (!fname || stat(fname, &statbuf) == -1) {
    ll_log_error("fname == NULL || stat(fname, &statbuf) == -1");
    goto error;
  }

  /* Allocate the tokenizer onto the heap */
  if (!(ctok = calloc(1, sizeof(*ctok)))) {
    ll_log_error("ctok == NULL");
    goto error;
  }

  /* Open the file to get size / content */
  if (!(file = fopen(fname, "rt"))) {
    ll_log_error("file == NULL");
    goto error;
  }

  ctok->file_size = statbuf.st_size;
  if (!(ctok->file_buffer = malloc(ctok->file_size + 1))) {
    ll_log_error("ctok->file_buffer == NULL");
    goto error;
  }

  ctok->file_buffer[ctok->file_size - 1] = '\0';
  if (fread(ctok->file_buffer, 1, ctok->file_size, file) < ctok->file_size) {
    ll_log_error("Unable to read to entire source file...");
    goto error;
  }

  fclose(file);
  return ctok;

error:
  if (file) fclose(file);
  if (ctok && ctok->file_buffer) free(ctok->file_buffer);
  if (ctok) free(ctok);
  return NULL;
}

void ctok_tokenize(ctok_t *ctok) {
  if (!ctok || !ctok->file_buffer || !ctok->file_size) {
    ll_log_warn("ctok_tokenize(...) -- ctok isn't initalized");
    return;
  }

  ctok->buffer_capacity = _CTOK_BUFSIZ;
  if (!(ctok->token_buffer = calloc(ctok->buffer_capacity, 1))) {
    ll_log_error("ctok_tokenize(...) -- unable to initalize token buffer");
    return;
  }

  if (!(ctok->tokens = ctok_vector_new())) {
    ll_log_error("ctok_tokenize(...) -- unable to initalize token vector");
    return;
  }

  size_t token_from = 0;
  char prev = '\0', curr = ctok->file_buffer[0];
  for (size_t i = 0; i < ctok->file_size; curr = ctok->file_buffer[++i]) {
    /* Case #1: character literal */
    if (curr == '\'') {
      if (ctok->mode == CTOK_NORMAL_MODE || ctok->mode == CTOK_OPERATOR_MODE) {
        if (!isspace(curr)) _ctok_process_token(ctok, token_from, i);
        ctok->mode = CTOK_CHARACTER_LITERAL_MODE;
        token_from = i; /* Begin procesing next token... */
      } else if (prev != '\\' && ctok->mode == CTOK_CHARACTER_LITERAL_MODE) {
        ctok->mode = CTOK_NORMAL_MODE; /* Possible ERROR? */
      }
    }

    /* Case 2: string literal */
    else if (curr == '"') {
      if (ctok->mode == CTOK_NORMAL_MODE || ctok->mode == CTOK_OPERATOR_MODE) {
        if (!isspace(curr)) _ctok_process_token(ctok, token_from, i);
        ctok->mode = CTOK_STRING_LITERAL_MODE;
        token_from = i; /* Begin procesing next token... */
      } else if (prev != '\\' && ctok->mode == CTOK_STRING_LITERAL_MODE) {
        ctok->mode = CTOK_NORMAL_MODE;
      }
    }

    /* Case 3: multi-line comments */
    else if (prev == '/' && curr == '*')
      ctok->mode = CTOK_MULTI_LINE_COMMENT_MODE;
    else if (prev == '*' && curr == '/' &&
             ctok->mode == CTOK_MULTI_LINE_COMMENT_MODE)
      ctok->mode = CTOK_NORMAL_MODE, ctok->_n_comments++;
    else if (ctok->mode == CTOK_MULTI_LINE_COMMENT_MODE)
      continue;

    /* Case 4: single-line comments */
    else if (prev == '/' && curr == '/')
      ctok->mode = CTOK_SINGLE_LINE_COMMENT_MODE;
    else if (prev == '\\' && curr != '\n' &&
             ctok->mode == CTOK_SINGLE_LINE_COMMENT_MODE)
      ctok->mode = CTOK_NORMAL_MODE, ctok->_n_comments++;
    else if (ctok->mode == CTOK_SINGLE_LINE_COMMENT_MODE)
      ;

    /* Case 5: identifiers and keywords */
    else if (isalnum(curr) || curr == '_') {
      if (ctok->mode == CTOK_NORMAL_MODE && isspace(prev)) {
        token_from = i;
      } else if (ctok->mode == CTOK_OPERATOR_MODE) {
        _ctok_process_token(ctok, token_from, i);
        ctok->mode = CTOK_NORMAL_MODE;
        token_from = i;
      }
    }

    /* Case 6: operators and punctuators */
    else if (!isspace(curr) && ctok->mode == CTOK_NORMAL_MODE) {
      if (!isspace(prev)) _ctok_process_token(ctok, token_from, i);
      ctok->mode = CTOK_OPERATOR_MODE;
      token_from = i;
    } else if (!isspace(curr) && ctok->mode == CTOK_OPERATOR_MODE) {
      char tmp[i - token_from + 2];
      strncpy(tmp, ctok->file_buffer + token_from, i - token_from + 1);
      tmp[i - token_from + 1] = '\0';
      for (size_t j = 0; j < 59; ++j)
        if (strcmp(ctok_operators[j], tmp) == 0) {
          printf("Token -> %s\n", tmp);
          goto end_of_loop;
        }

      _ctok_process_token(ctok, token_from, i);
      ctok->mode = CTOK_NORMAL_MODE;
      token_from = i;
    }

    else if (isspace(curr) && !(isspace(prev) || prev == '/')) {
      _ctok_process_token(ctok, token_from, i);
      ctok->mode = CTOK_NORMAL_MODE;
    }

  end_of_loop:
    prev = curr; /* keep last character for brevity */
  }

  char *token = ctok->token_buffer;
  for (size_t i = 0; i < ctok->token_count; ++i, token += strlen(token) + 1)
    ctok_vector_push_back(ctok->tokens, token);
}

static void _ctok_process_token(ctok_t *ctok, size_t from, size_t to) {
  assert(ctok && ctok->file_buffer);
  assert(ctok->token_buffer && ctok->tokens);
  assert(from <= to && to < ctok->file_size);

  if (from == to) return;

  // Calculate the length of the token
  size_t token_length = to - from;

  // Check if the token_buffer has enough capacity, if not resize it
  if ((ctok->buffer_size + token_length + 1) > ctok->buffer_capacity) {
    /* Determine a suitable capacity for the next token */
    size_t new_capacity = _CTOK_MAX(_CTOK_BUFSIZ, ctok->buffer_capacity << 1);
    while (new_capacity < ctok->buffer_size + token_length + 1)
      new_capacity <<= 1;

    ctok->token_buffer = realloc(ctok->token_buffer, new_capacity);
    if (!ctok->token_buffer) {
      ll_log_critical("Failed to allocate memory for token buffer\n");
      exit(EXIT_FAILURE);
    }

    ctok->buffer_capacity = new_capacity;
  }

  // Copy the token from file_buffer to token_buffer
  char *dest = ctok->token_buffer + ctok->buffer_size;
  memcpy(dest, ctok->file_buffer + from, token_length);
  ctok->token_buffer[ctok->buffer_size + token_length] = '\0';

  // Store the position of the new token in the tokens vector
  ctok->buffer_size += token_length + 1; /* Update the buffer size */
  ctok->token_count++;
}