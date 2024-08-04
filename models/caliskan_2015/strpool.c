#include "strpool.h"

#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SCP_VERSION "0.0.2"

#define SCP_DEFAULT_INITIAL_CAPACITY (1 << 4)
#define SCP_DEFAULT_LOAD_FACTOR 0.86F
#define SCP_DEFAULT_CELLAR_RATIO 0.14F

#define SCP_FIND_CREATED_INPLACE 0b0001
#define SCP_FIND_CREATED_CHAINED 0b0010

/* TODO: Build prime-based resizing table */
/* TODO: Finish initial doxygen documentation */
/* TODO: Build test-suite for testing */
/* TODO: Implement max capacity and/or thread safety */

#define scp_foreach_internal(pool, b)                                         \
  for (scp_bucket_t *b = pool->table; b < pool->table + pool->capacity; ++b)  \
    if (!scp_bucket_is_empty (b))

static scp_bucket_t *scp_find (strpool_t *pool, const char *key,
                               const size_t n, const bool create, int *rflags);
static strpool_t *scp_resize (strpool_t *pool);

static inline bool scp_bucket_is_empty (const scp_bucket_t *b);
static uint32_t scp_strnhash (const char *str, size_t n);

static void
_scp_die (const char *format, ...)
{
  va_list args;

  va_start (args, format);
  vfprintf (stderr, format, args);
  va_end (args);

  /* Make the final preperations before gracefully exiting the process. The
  newline is printed primarily for terminal-based programs to shift the prompt
  to a new line -- Quality of Life... */
  fprintf (stderr, "\n");
  exit (EXIT_FAILURE);
}

void
scp_init (strpool_t *pool, strpool_config_t *config)
{
  assert (pool != NULL);

  if (config)
    {
      assert (pool->capacity != -1U); /* -1U represent EoC in the set */
      assert (0.0F < config->load_factor && config->load_factor < 1.0F);
      assert (0.0F < config->cellar_ratio && config->cellar_ratio < 1.0F);

      pool->capacity = config->initial_capacity;
      pool->load_factor = config->load_factor;
      pool->cellar_ratio = config->cellar_ratio;
    }
  else
    {
      pool->capacity = SCP_DEFAULT_INITIAL_CAPACITY;
      pool->load_factor = SCP_DEFAULT_LOAD_FACTOR;
      pool->cellar_ratio = SCP_DEFAULT_CELLAR_RATIO;
    }

  pool->table = calloc (pool->capacity, sizeof (*pool->table));
  if (!pool->table)
    _scp_die ("scp_init(): unable to allocate pool's table");
  for (uint32_t i = 0; i < pool->capacity; ++i)
    pool->table[i].next = -1U;

  pool->size = pool->cellar_size = 0U;
  pool->cellar_capacity = pool->capacity * pool->cellar_ratio;
  pool->table_capacity = pool->capacity - pool->cellar_capacity;
}

void
scp_fini (strpool_t *pool)
{
  assert (pool != NULL && pool->table != NULL);

  /* This might not be the best practice, but what can I do... */
  scp_foreach_internal (pool, b) free ((void *)b->key);
  free (pool->table);

  /* The pool is cleared to prevent subsequent usage after `scp_fini(...)`.
  Future work might make this only execute when NDEBUG is only disabled for
  optimization in deployment settings. */
  memset (pool, '\0', sizeof (*pool));
}

const char *
scp_intern (strpool_t *pool, const char *s, const size_t n)
{
  assert (pool != NULL && s != NULL);

  int rflags = 0;
  scp_bucket_t *b = scp_find (pool, s, n, true, &rflags);

  /* If the key is already present, don't allocate a new heap chuck */
  if (!rflags)
    return b->key;

  /* Since this is written for C99, we cannot use `strnlen(...)`, because it
  was only *recently* defined in the 2008 POSIX Standard (IEEE 1003.1). As a
  result, we can use `memchr(...)` as a suitable alternative. */
  const char *found = (const char *)memchr (s, '\0', n);
  size_t true_length = found ? found - s : n;

  char *interned = malloc (true_length + 1); /* '\0' (null-terminator) */
  memcpy (interned, s, true_length);
  interned[true_length] = '\0';

  /* Update the map with the interned string (char * -> const char *) */
  b->key = (const char *)interned;
  pool->heap_usage += true_length + 1;

  return interned;
}

bool
scp_is_interned (strpool_t *pool, const char *s, const size_t n)
{
  return scp_find (pool, s, n, false, NULL);
}

size_t
scp_size (strpool_t *pool)
{
  assert (pool != NULL);

  return pool->size;
}

size_t
scp_memory_usage (strpool_t *pool)
{
  assert (pool != NULL);

  uint64_t table_usage = pool->capacity * sizeof (*pool->table);
  return sizeof (*pool) + table_usage + pool->heap_usage;
}

void
scp_foreach (strpool_t *pool, void (*callback) (const char *))
{
  assert (pool != NULL && callback != NULL);

  scp_foreach_internal (pool, b) callback (b->key);
}

static scp_bucket_t *
scp_find (strpool_t *pool, const char *key, const size_t n, const bool create,
          int *rflags)
{
  assert (pool != NULL && pool->table != NULL && key != NULL);

  uint32_t hash = scp_strnhash (key, n);
  scp_bucket_t *chain = pool->table + (hash % pool->table_capacity);

  if (!scp_bucket_is_empty (chain))
    {
      /* The reason we rehash here is to delay rehashing as long as possible.
      Specifically, if there is never any collisions, there is no reason to
      ever rehash, be it it might degrade performance through 2 vectors: (1)
      the initial investment in rehashing and (2) the average chain length
      might increase if the hash function isn't strong on the new table
      capacity. */
      if (create && pool->size > (pool->capacity * pool->load_factor))
        return scp_find (scp_resize (pool), key, n, create, rflags);

      while (true)
        {
          if (chain->hash == hash && strncmp (chain->key, key, n) == 0)
            return chain;

          if (chain->next == -1U)
            break;

          /* Iterate through the remainder of the chain until (1) we find the
          key or (2) reach end of chain (chain->next == -1U). */
          assert (chain->next < pool->capacity);
          chain = pool->table + chain->next;
        }
    }

  if (!create)
    return NULL;

  /* There was no initial colision, which means we don't have to chain. */
  if (scp_bucket_is_empty (chain))
    {
      chain->key = key, chain->hash = hash, pool->size++;

      if (rflags)
        *rflags |= SCP_FIND_CREATED_INPLACE;
      return chain;
    }

  scp_bucket_t *next = NULL;
  if (pool->cellar_size < pool->cellar_capacity)
    {
      next = pool->table + (pool->capacity - ++pool->cellar_size);
      goto bucket_init;
    }
  else if ((chain - pool->table) < pool->table_capacity)
    {
      /* Since the chain is within the table, we can utilize pointer arithmatic
      to calculate the index of the bucket -- bucket == base + offset */
      size_t from = chain - pool->table;

      /* It's better to search the map using indexing instead of strictly
      pointers, becuase pointers force you to work with modulo w/ offsets :/ */
      for (size_t to = from; (to = (to + 1) % pool->table_capacity) != from;)
        if (scp_bucket_is_empty (next = pool->table + to))
          goto bucket_init;
    }
  else /* Chain is located in cellar, which should be handled specially */
    {
      /* Since the `chain` bucket is located within the cellar, we can start
      at the table's base, and linearly search through the table. */
      scp_bucket_t *cellar = pool->table + pool->table_capacity;
      for (next = pool->table; next < cellar; ++next)
        if (scp_bucket_is_empty (next))
          goto bucket_init;
    }

  /* The entire table has been searched, and not avalible buckets have been
  found. This means that the memory has gotton corrupted, and we should alert
  the user by dying. */
  _scp_die ("scp_find(): pool's table got corrupted.");

bucket_init:
  assert (scp_bucket_is_empty (next));
  chain->next = next - pool->table; /* Build the chain */
  next->key = key, next->hash = hash, pool->size++;

  if (rflags)
    *rflags |= SCP_FIND_CREATED_CHAINED;
  return next;
}

static strpool_t *
scp_resize (strpool_t *pool)
{
  scp_bucket_t *old_table = pool->table;
  uint32_t old_capacity = pool->capacity;
  strpool_config_t config = { .initial_capacity = old_capacity << 1,
                              .load_factor = pool->load_factor,
                              .cellar_ratio = pool->cellar_ratio };

  /* It is most efficent to re-intalize the pool with a increased capacity */
  scp_init (pool, &config);
  for (uint32_t i = 0; i < old_capacity; ++i)
    if (!scp_bucket_is_empty (old_table + i))
      {
        int rflags = 0;
        scp_find (pool, old_table[i].key, SIZE_MAX, true, &rflags);
        //printf ("Shifted \"%s\" with response: %d\n", old_table[i].key,
        //        rflags);
      }

  free (old_table);
  return pool;
}

static inline bool
scp_bucket_is_empty (const scp_bucket_t *b)
{
  return b->key == NULL && b->next == -1U;
}

static uint32_t
scp_strnhash (const char *str, size_t n)
{
  char c;
  uint32_t hash = 5381U;
  for (size_t i = 0; (c = *str++) && i < n; ++i)
    hash = ((hash << 5) + hash) + c; /* hash * 33 + c */
  return hash;
}
