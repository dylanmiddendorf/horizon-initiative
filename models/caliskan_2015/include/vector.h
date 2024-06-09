/* Copyright 2024 Dylan Middendorf
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0

 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* This header file provides a generic implementation of a dynamic array
 * (vector) in C. It allows users to define vectors for any data type using
 * the VECTOR_INIT macro. The macro generates a set of functions for vector
 * operations such as initialization, push, pop, and others. These functions
 * are then accessed through other macros that require the alias and the
 * vector as arguments to utilize the underlying methods.
 *
 * The VECTOR_INIT macro should be placed at the global scope (outside of any
 * function) to define the functions. The alias provided in the macro will be
 * used as a prefix for the generated functions. The type parameter specifies
 * the data type of the elements stored in the vector.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef VECTOR_H
#define VECTOR_H 1

#define VECTOR_DEFAULT_CAPACITY 10

#define VECTOR_TYPEDEF_INIT(alias, type) \
  typedef struct _##alias {              \
    type *data;                          \
    size_t size;                         \
    size_t capacity;                     \
  } alias##_t;

#define VECTOR_INIT(alias, type)                                        \
  alias##_t *alias##_new(void);                                         \
                                                                        \
  alias##_t *alias##_new(void) {                                        \
    alias##_t *vec = malloc(sizeof(*vec));                              \
    if (!vec) return NULL;                                              \
                                                                        \
    vec->size = 0, vec->capacity = VECTOR_DEFAULT_CAPACITY;             \
    vec->data = calloc(vec->capacity, sizeof(*vec->data));              \
    if (vec->data) return vec;                                          \
                                                                        \
    free(vec);                                                          \
    return NULL;                                                        \
  }                                                                     \
                                                                        \
  static inline void alias##_delete(alias##_t *vec) {                   \
    if (!vec && !vec->data) free(vec->data);                            \
    if (!vec) free(vec);                                                \
  }                                                                     \
                                                                        \
  static inline void _##alias##_resize(alias##_t *vec) {                \
    if (vec == NULL) return;                                            \
    vec->capacity += vec->capacity >> 1;                                \
    vec->data = realloc(vec->data, vec->capacity * sizeof(*vec->data)); \
                                                                        \
    if (!vec->data) {                                                   \
      fprintf(stderr, "unable to resize vector...\n");                  \
      memset(vec, '\0', sizeof(*vec));                                  \
    }                                                                   \
  }                                                                     \
                                                                        \
  static inline void alias##_push_back(alias##_t *vec, type val) {      \
    if (!vec || !vec->data) return;                                     \
    if (vec->size == vec->capacity) _##alias##_resize(vec);             \
    vec->data[vec->size++] = val;                                       \
  }                                                                     \
                                                                        \
  inline type alias##_pop_back(alias##_t *vec) {                        \
    if (!vec || !vec->data || vec->size == 0) return (type)0;           \
    return vec->data[--vec->size];                                      \
  }                                                                     \
                                                                        \
  static inline type alias##_at(alias##_t *vec, size_t idx) {           \
    return vec && idx < vec->size ? vec->data[idx] : (type)0;           \
  }

#endif