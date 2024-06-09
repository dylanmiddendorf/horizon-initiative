#include "log_lite.h"

#include "stdarg.h"
#include "stdio.h"

static ll_level_t _ll_active_level = LL_LEVEL_ERROR;

#define LL_LOG(level, prefix, format)                                \
  va_list args;                                                      \
  if (level < _ll_active_level) return;                              \
  va_start(args, format);                                            \
  fprintf(level < LL_LEVEL_ERROR ? stdout : stderr, "%s: ", prefix); \
  vfprintf(level < LL_LEVEL_ERROR ? stdout : stderr, format, args);  \
  fprintf(level < LL_LEVEL_ERROR ? stdout : stderr, "\n")

void ll_log_debug(const char *format, ...) {
  LL_LOG(LL_LEVEL_DEBUG, "[DEBUG ]", format);
}

void ll_log_info(const char *format, ...) {
  LL_LOG(LL_LEVEL_INFO, "[INFO ]", format);
}

void ll_log_warn(const char *format, ...) {
  LL_LOG(LL_LEVEL_WARN, "[WARN ]", format);
}

void ll_log_error(const char *format, ...) {
  LL_LOG(LL_LEVEL_ERROR, "[ERROR ]", format);
}

void ll_log_critical(const char *format, ...) {
  LL_LOG(LL_LEVEL_ERROR, "[CRITICAL]", format);
}

void ll_set_level(ll_level_t level) { _ll_active_level = level; }
