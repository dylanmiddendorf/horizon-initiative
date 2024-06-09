#ifndef MAP_H
#define MAP_H 1

#include <stdbool.h>
#include <stdint.h>

typedef struct _bucket bucket_t;

typedef struct _map {
  bucket_t *table;

  uint32_t capacity;
  uint32_t table_capacity;
  uint32_t cellar_capacity;
  float cellar_ratio;

  uint32_t size; /* Number of active entries in whole map (table & cellar) */
  uint32_t cellar_size; /* Number of active entries in strictly in cellar */

  float load_factor;
  uint32_t threshold;

  /* If true, refactor the map on deletion, else use lazy deletion. */
  bool vacuum; /* Defaults to false, because it reduces deletion overhead */
} map_t;

map_t *map_init();
uint32_t map_get(map_t *map, char *key);
uint32_t map_put(map_t *map, char *key, uint32_t value);
map_t *map_clear(map_t *map);
uint32_t djb2_hash(const char *s);

#endif