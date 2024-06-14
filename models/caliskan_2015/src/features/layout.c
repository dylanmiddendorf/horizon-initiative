#include "features/layout.h"

#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/stat.h>

#include "log_lite.h"
#include "tokenizer.h"

double* hri_layout_features(const char* fname) {
  FILE* file = NULL;
  struct stat statbuf = {0};
  char* fbuffer;

  if (!fname || stat(fname, &statbuf) == -1) {
    ll_log_error("unable to get file attributes...");
    return NULL;
  }

  if (!(file = fopen(fname, "rt"))) {
    ll_log_error("file == NULL");
    goto error;
  }

  if (!(fbuffer = malloc(statbuf.st_size + 1))) {
    ll_log_error("fbuffer == NULL");
    goto error;
  }

  fbuffer[statbuf.st_size - 1] = '\0';
  if (fread(fbuffer, 1, statbuf.st_size, file) < statbuf.st_size) {
    ll_log_error("Unable to read to entire source file...");
    goto error;
  }

  bool empty_line = true; /* used for FSM state managment */
  int tab_count = 0, space_count = 0, whitespace_count = 0;
  int curly_brace_lines = 0, empty_line_count = 0;
  int tab_start_lines = 0, space_start_lines = 0;
  for (size_t i = 0; i < statbuf.st_size; ++i) {
    if (isspace(fbuffer[i])) {
      if (fbuffer[i] == '\t') tab_count++;
      if (fbuffer[i] == ' ') space_count++;
      if (fbuffer[i] == '\n') empty_line = true;

      whitespace_count++;
    } else {
      if (fbuffer[i] == '{') {
        if (empty_line)
          curly_brace_lines++;
        else
          curly_brace_lines--;
      }

      empty_line = false;
    }

    if (i > 0 && fbuffer[i - 1] == '\n') {
      /* File aganostic solution for line-endings (CRLF & LF) */
      if (fbuffer[i] == '\n') empty_line_count++;
      if (fbuffer[i] == '\r') empty_line_count++;
      if (fbuffer[i] == '\t') tab_start_lines++;
      if (fbuffer[i] == ' ') space_start_lines++;
    }
  }

  double* features = calloc(sizeof(*features), 6);
  if (!features) {
    ll_log_critical("Unable to allocate feature vector...\n");
  }

  features[0] = (double)tab_count / statbuf.st_size;
  features[1] = (double)space_count / statbuf.st_size;
  features[2] = (double)empty_line_count / statbuf.st_size;
  features[3] = (double)whitespace_count / (statbuf.st_size - whitespace_count);
  features[4] = curly_brace_lines > 0; /* Not sure about edge case... */
  features[5] = tab_start_lines > space_start_lines;
  return features;

error:
  if (fbuffer) free(fbuffer);
  if (file) fclose(file);
}
