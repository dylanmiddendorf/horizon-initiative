#include "ctok.h"

#include <assert.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

/* TODO: Support all forms of new-lines when parsing single-line comments */
/* TODO: Shift from isolated methods to a singular macro */

static const char *cxt_tokens[]
    = { "{",  "}",  "[",  "]",    "#",   "##",  "(",   ")",  "<:", ":>",
        "<%", "%>", "%:", "%:%:", ";",   ":",   "...", "?",  "::", ".",
        ".*", "+",  "-",  "*",    "/",   "%",   "^",   "&",  "|",  "~",
        "!",  "=",  "<",  ">",    "+=",  "-=",  "*=",  "/=", "%=", "^=",
        "&=", "|=", "<<", ">>",   ">>=", "<<=", "==",  "!=", "<=", ">=",
        "&&", "||", "++", "--",   ",",   "->*", "->" };

static int cxt_skip_delimiters (cpp_tokenizer_t *tok, const int start);
static int cxt_scan_token (cpp_tokenizer_t *tok, int from);
static int cxt_scan_identifier (cpp_tokenizer_t *tok, int from);
static int cxt_scan_numerical_literal (cpp_tokenizer_t *tok, int from);
static int cxt_scan_character_literal (cpp_tokenizer_t *tok, int from);
static int cxt_scan_string_literal (cpp_tokenizer_t *tok, int from);
static int cxt_scan_operator (cpp_tokenizer_t *tok, int from);
static bool cxt_is_operator (cpp_tokenizer_t *tok, int from, int to);

void
cxt_init (cpp_tokenizer_t *tok, const char *source, tokenizer_config_t *config)
{
  assert (tok != NULL && source != NULL);
  tok->str = source, tok->max_position = strlen (source);
  tok->current_position = 0, tok->next_position = -1;

  if (config)
    {
      assert (config->pool);
      tok->pool = config->pool;
      tok->external_pool = true;
    }
  else
    {
      tok->pool = malloc (sizeof (*tok->pool));
      scp_init (tok->pool, NULL);
      tok->external_pool = false;
    }

  tok->n_comments = 0;
}

void
cxt_fini (cpp_tokenizer_t *tok)
{
  assert (tok && tok->pool);
  if (!tok->external_pool)
    free (tok->pool);
}

int
cxt_count_tokens (cpp_tokenizer_t *tok)
{
  return 0UL;
}

bool
cxt_has_more_tokens (cpp_tokenizer_t *tok)
{
  tok->next_position = cxt_skip_delimiters (tok, tok->current_position);
  return (tok->next_position < tok->max_position);
}

const char *
cxt_next_token (cpp_tokenizer_t *tok)
{
  tok->current_position = cxt_skip_delimiters (tok, tok->current_position);

  int start = tok->current_position;
  tok->current_position = cxt_scan_token (tok, tok->current_position);

  return scp_intern (tok->pool, tok->str + start,
                     tok->current_position - start);
}

static int
cxt_skip_delimiters (cpp_tokenizer_t *tok, const int start)
{
  int p = start;
  for (; p < tok->max_position; ++p)
    {
      if (isspace (tok->str[p]))
        continue;

      if (tok->str[p] == '/')
        {
          /* Check index before increasing the scope (1 -> 2 characters). */
          if (p == tok->max_position - 1)
            break;

          /* If a comment is found, iterate until the end is found. For
          single-line comment, this is denoted with a non-escaped new-line
          character. For multi-line comments this is denoted with an asterisk
          followed by a forward slash. */
          if (tok->str[p + 1] == '/')
            {
              tok->n_comments++; /* Single-line comment found */
              for (p = p + 2; p < tok->max_position; ++p)
                if (tok->str[p] == '\n' && tok->str[p - 1] != '\\')
                  break;
            }
          else if (tok->str[p + 1] == '*')
            {
              tok->n_comments++; /* Multi-line comment found */
              for (p = p + 2; p < tok->max_position; ++p)
                if (tok->str[p - 1] == '*' && tok->str[p] == '/')
                  break;
            }
        }
      else
        break; /* Found non-insignificant token */
    }

  return p < tok->max_position ? p : tok->max_position;
}

static int
cxt_scan_token (cpp_tokenizer_t *tok, int from)
{
  /* The end of stream (EoS) has already been reached */
  if (tok->max_position <= from)
    return from;

  char c = tok->str[from]; /* Increase readability */
  if (isalpha (c) || c == '_')
    return cxt_scan_identifier (tok, from);
  if (isdigit (c))
    return cxt_scan_numerical_literal (tok, from);
  if (c == '\'')
    return cxt_scan_character_literal (tok, from);
  if (c == '"')
    return cxt_scan_string_literal (tok, from);
  return cxt_scan_operator (tok, from);
}

static int
cxt_scan_identifier (cpp_tokenizer_t *tok, int from)
{
  assert (tok != NULL && from < tok->max_position);
  assert (isalpha (tok->str[from]) || tok->str[from] == '_');

  int p = from + 1; /* First character has already been processed */
  for (char c = tok->str[p]; p < tok->max_position; c = tok->str[++p])
    if (!isalnum (c) && c != '_')
      break;
  return p;
}

static int
cxt_scan_numerical_literal (cpp_tokenizer_t *tok, int from)
{
  assert (tok != NULL && from < tok->max_position && isdigit (tok->str[from]));
  for (int p = from + 1; p < tok->max_position; ++p)
    if (!isalnum (tok->str[p]) && tok->str[p] != '.')
      return p;
  return tok->max_position;
}

static int
cxt_scan_character_literal (cpp_tokenizer_t *tok, int from)
{
  assert (tok != NULL && from < tok->max_position && tok->str[from] == '\'');
  for (int p = from + 2; p <= tok->max_position; ++p)
    if (tok->str[p - 1] != '\\' && tok->str[p] == '\'')
      return p + 1;
  return tok->max_position;
}

static int
cxt_scan_string_literal (cpp_tokenizer_t *tok, int from)
{
  assert (tok != NULL && from < tok->max_position && tok->str[from] == '"');
  for (int p = from + 1; p < tok->max_position; ++p)
    if (tok->str[p - 1] != '\\' && tok->str[p] == '"')
      return p + 1;
  return tok->max_position;
}

static int
cxt_scan_operator (cpp_tokenizer_t *tok, int from)
{
  assert (tok != NULL && from < tok->max_position);
  for (int p = from + 1; p < tok->max_position; ++p)
    if (!cxt_is_operator (tok, from, p + 1))
      return p;
  return tok->max_position;
}

static bool
cxt_is_operator (cpp_tokenizer_t *tok, int from, int to)
{
  for (size_t i = 0; i < 57; ++i)
    if (strncmp (tok->str + from, cxt_tokens[i], to - from) == 0)
      return true;
  return false;
}
