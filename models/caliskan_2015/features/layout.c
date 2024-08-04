#include "layout.h"

#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "../data.h"

double *
hri_layout_features (const char *fbuffer)
{
  size_t n = strlen (fbuffer);
  bool empty_line = true; /* used for FSM state managment */
  int tab_count = 0, space_count = 0, whitespace_count = 0;
  int curly_brace_lines = 0, empty_line_count = 0;
  int tab_start_lines = 0, space_start_lines = 0;
  for (size_t i = 0; i < n; ++i)
    {
      if (isspace (fbuffer[i]))
        {
          if (fbuffer[i] == '\t')
            tab_count++;
          if (fbuffer[i] == ' ')
            space_count++;
          if (fbuffer[i] == '\n')
            empty_line = true;

          whitespace_count++;
        }
      else
        {
          if (fbuffer[i] == '{')
            {
              if (empty_line)
                curly_brace_lines++;
              else
                curly_brace_lines--;
            }

          empty_line = false;
        }

      if (i > 0 && fbuffer[i - 1] == '\n')
        {
          /* File aganostic solution for line-endings (CRLF & LF) */
          if (fbuffer[i] == '\n')
            empty_line_count++;
          else if (fbuffer[i] == '\r')
            empty_line_count++;
          else if (fbuffer[i] == '\t')
            tab_start_lines++;
          else if (fbuffer[i] == ' ')
            space_start_lines++;
        }
    }

  double *features = calloc (sizeof (*features), 6);

  features[0] = (double)tab_count / n;
  features[1] = (double)space_count / n;
  features[2] = (double)empty_line_count / n;
  features[3] = (double)whitespace_count / (n - whitespace_count);
  features[4] = curly_brace_lines > 0; /* Not sure about edge case... */
  features[5] = tab_start_lines > space_start_lines;
  return features;
}

void
hri_layout_export (data_loader_t *loader)
{
  FILE *csv = fopen ("layout.csv", "wt");
  while (hdl_has_next (loader))
    {
      double *f = hri_layout_features (hdl_next (loader));
      fprintf (csv, "%s,%lf,%lf,%lf,%lf,%d,%d\n",
               loader->index.gl_pathv[loader->next_entry - 1], f[0], f[1],
               f[2], f[3], (int)f[4], (int)f[5]);
      free (f);
    }
  fclose (csv);
}
