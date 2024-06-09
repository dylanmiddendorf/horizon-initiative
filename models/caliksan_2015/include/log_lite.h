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

#ifndef LOG_LITE_H
#define LOG_LITE_H 1

#include <stdarg.h>
#include <stdio.h>


#define _LL_STR(s) #s
#define _LL_XSTR(s) _LL_STR(s)
#define LL_PRETTY_PRINT(format) _LL_XSTR(__func__) ":" _LL_XSTR(__LINE__) " -- "

typedef enum _ll_level {
  LL_LEVEL_DEBUG,
  LL_LEVEL_INFO,
  LL_LEVEL_WARN,
  LL_LEVEL_ERROR,
  LL_LEVEL_CRITICAL
} ll_level_t;

void ll_log_debug(const char *format, ...);
void ll_log_info(const char *format, ...);
void ll_log_warn(const char *format, ...);
void ll_log_error(const char *format, ...);
void ll_log_critical(const char *format, ...);
void ll_set_level(ll_level_t level);

#endif