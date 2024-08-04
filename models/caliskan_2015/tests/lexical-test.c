#include "data.h"
#include "features/lexical.h"

#include <stdlib.h>

int
main (int argc, char *argv[])
{
  data_loader_t loader = { 0 };
  hdl_init (&loader, "dataset/*.cpp", NULL);
  hri_extract_lexical_features (&loader);
  hdl_fini(&loader);
  return 0;
}