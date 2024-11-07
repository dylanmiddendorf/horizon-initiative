#include "../data.h"
#include "../layout.h"

#include <stdlib.h>

int
main (int argc, char *argv[])
{
  data_loader_t loader = { 0 };
  hdl_init (&loader, "dataset/*.cpp", NULL);
  hri_layout_export (&loader);
  hdl_fini(&loader);
  return 0;
}