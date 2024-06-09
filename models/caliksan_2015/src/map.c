#include "map.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAP_DEFAULT_INITIAL_CAPACITY 0x08
#define MAP_DEFAULT_LOAD_FACTOR 0.68
#define MAP_DEFAULT_CELLAR_RATIO 0.14

static map_t *_map_init(uint32_t initial_capacity);
static map_t *_map_rehash(map_t *map);
static bucket_t *_bucket_find(map_t *map, char *key, bool create);
static inline bool _bucket_is_empty(bucket_t *b);
static inline uint32_t _bucket_set_value(bucket_t *b, uint32_t value);
static inline uint32_t _bucket_get_value(bucket_t *b);

struct _bucket {
  char *key;
  uint32_t value;

  uint32_t hash;
  bucket_t *next;
};

map_t *map_init() {
  map_t *map = _map_init(MAP_DEFAULT_INITIAL_CAPACITY);

  /* Assign all constants after initalization */
  map->cellar_ratio = MAP_DEFAULT_CELLAR_RATIO;
  map->load_factor = MAP_DEFAULT_LOAD_FACTOR;
  map->threshold = map->table_capacity * map->load_factor;

  map->cellar_capacity = map->capacity * map->cellar_ratio;
  map->table_capacity = map->capacity - map->cellar_capacity;
  return map;
}

static map_t *_map_init(uint32_t initial_capacity) {
  map_t *map = malloc(sizeof(*map));
  if (!map) return NULL;

  /* Assign required constant(s) after initalization */
  map->capacity = initial_capacity;
  map->size = 0, map->cellar_size = 0;

  map->table = calloc(map->capacity, sizeof(*map->table));
  if (!map->table) {
    free(map); /* Prevent all memory leaks */
    return NULL;
  }

  map_clear(map);
  return map;
}

uint32_t map_get(map_t *map, char *key) {
  return _bucket_get_value(_bucket_find(map, key, false));
}

uint32_t map_put(map_t *map, char *key, uint32_t value) {
  return _bucket_set_value(_bucket_find(map, key, false), value);
}

map_t *map_clear(map_t *map) {
  /* Populate all the buckets will null pointers */
  for (uint32_t i = 0; i < map->capacity; ++i) map->table[i].next = NULL;
  return map;
}

static map_t *_map_rehash(map_t *map) {
  map_t *new_map = _map_init(map->capacity << 1);

  new_map->cellar_ratio = map->cellar_ratio;
  new_map->load_factor = map->load_factor;

  new_map->cellar_capacity = map->capacity * new_map->cellar_ratio;
  new_map->table_capacity = new_map->capacity - new_map->cellar_capacity;
  new_map->threshold = new_map->capacity * new_map->load_factor;
  new_map->vacuum = map->vacuum;

  for (uint32_t i = 0; i < map->capacity; ++i) {
    bucket_t *b = &map->table[i]; /* Reduce array accesses */
    if (!_bucket_is_empty(b)) map_put(new_map, b->key, b->value);
  }

  return memcpy(map, new_map, sizeof(*map));
}

static bucket_t *_bucket_find(map_t *map, char *key, bool create) {
  if (!map || !key) return NULL;

  if (map->size > map->threshold)
    return _bucket_find(_map_rehash(map), key, create);

  uint32_t hash = djb2_hash(key);
  bucket_t *chain = &map->table[hash % map->table_capacity], *prev = NULL;

  for (; chain; prev = chain, chain = chain->next)
    if (hash == chain->hash && strcmp(key, chain->key) == 0) return chain;

  if (create) return NULL; /* Bucket does not exist... */

    if (_bucket_is_empty(prev)) {
    chain = prev, prev = NULL;
    goto bucket_init;
  }

  if (map->cellar_size < map->cellar_capacity) {
    chain = &map->table[map->capacity - ++map->cellar_size];
    goto bucket_init; /* DRY principles */
  }

  do {
    /* bucket_index = (bucket - base_bucket) / sizeof(bucket_t) */
    chain = &map->table[(chain - map->table + 1) % map->table_capacity];
  } while (!_bucket_is_empty(chain) && chain != prev);

  if (chain == prev) {
    if (map->size < map->capacity) {
      fprintf(stderr, "memory curruption detected...\n");
      exit(EXIT_FAILURE); /* The map has been currupted... */
    }

    fprintf(stderr, "invalid load factor detected...");
    map->load_factor = MAP_DEFAULT_LOAD_FACTOR;
    return _bucket_find(_map_rehash(map), key, create);
  }

bucket_init:
  map->size++; /* Increase size for rehashing... */
  chain->key = key, chain->hash = hash;
  if (prev) prev->next = chain;
  return chain;
}

static inline bool _bucket_is_empty(bucket_t *b) {
  return b->key == NULL && b->next == NULL;
}

static inline uint32_t _bucket_set_value(bucket_t *b, uint32_t value) {
  if (!b) return 0; /* Prevent null pointer exceptions (segfaults) */
  uint32_t prev_value = _bucket_is_empty(b) ? 0 : b->value;
  b->value = value;
  return prev_value;
}

static inline uint32_t _bucket_get_value(bucket_t *b) {
  if (!b) return 0; /* Prevent null pointer exceptions (segfaults) */
  return b->value;
}

uint32_t djb2_hash(const char *s) {
  uint32_t hash = 5381;
  if (!s) return hash;

  char c; /* Used to store the current character */
  while ((c = *s++) != '\0') hash = (hash << 5) + hash + c;
  return hash;
}
