#include <stdio.h>

#include "map.h"
#include "vector.h"
#include "tokenizer.h"

void test_map() {
  map_t *m = map_init();
  map_put(m, "alpha", 1);
  map_put(m, "beta", 2);
  map_put(m, "charlie", 3);
  map_put(m, "delta", 4);
  map_put(m, "echo", 5);
  map_put(m, "foxtrot", 6);
  map_put(m, "golf", 7);
  printf("%d\n", map_get(m, "charlie"));
}

VECTOR_TYPEDEF_INIT(vec, char *)
VECTOR_INIT(vec, char *)

void test_vec() {
  vec_t *v = vec_new();
  vec_push_back(v, "alpha");
  vec_push_back(v, "beta");
  vec_push_back(v, "charlie");
  vec_push_back(v, "delta");
  vec_push_back(v, "echo");
  for(size_t i = 0; i < v->size; ++i)
    printf("index %lu -> %s\n", i, vec_at(v, i));
  vec_delete(v);
}

void test_tokenizer() {
  ctok_t *ctok = ctok_init("dataset/10tus_250649710.cpp");
  ctok_tokenize(ctok); /* Tokenize the source file */
  for(size_t i = 0; i < ctok->tokens->size; ++i)
    printf("\"%s\", ", ctok->tokens->data[i]);
}

int main(int argc, char *argv[]) {
  (void) argc, (void) argv;
  test_tokenizer();
  return 0;
}