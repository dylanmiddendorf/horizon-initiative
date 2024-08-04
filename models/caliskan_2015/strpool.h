#ifndef STRPOOL_H
#define STRPOOL_H 1

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct _scp_bucket
{
  const char *key;
  uint32_t hash;

  uint32_t next;
} scp_bucket_t;

typedef struct _strpool
{
  scp_bucket_t *table;

  uint32_t capacity;
  uint32_t table_capacity;
  uint32_t cellar_capacity;

  uint32_t size;
  uint32_t cellar_size;

  float load_factor;
  float cellar_ratio;

  uint64_t heap_usage;
} strpool_t;

typedef struct _strpool_config
{
  uint32_t initial_capacity;
  float load_factor;
  float cellar_ratio;
} strpool_config_t;

void scp_init (strpool_t *pool, strpool_config_t *config);
void scp_fini (strpool_t *pool);

const char *scp_intern (strpool_t *pool, const char *s, const size_t n);
bool scp_is_interned (strpool_t *pool, const char *s, const size_t n);

size_t scp_size (strpool_t *pool);
size_t scp_memory_usage (strpool_t *pool);

void scp_foreach (strpool_t *pool, void (*callback) (const char *));

#endif