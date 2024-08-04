#include "strpool.h"

#include <stdio.h>
#include <stdlib.h>

static const size_t alphabet_length = 26;
static const char *phonetic_alphabet[26]
    = { "Alpha",  "Bravo",    "Charlie", "Delta",   "Echo",    "Foxtrot",
        "Golf",   "Hotel",    "India",   "Juliett", "Kilo",    "Lima",
        "Mike",   "November", "Oscar",   "Papa",    "Quebec",  "Romeo",
        "Sierra", "Tango",    "Uniform", "Victor",  "Whiskey", "X-ray",
        "Yankee", "Zulu" };

void print_entry(const char *s) {
    printf("Found %s...\n", s);
}

int
main (int argc, char *argv[])
{
  strpool_t pool;
  scp_init (&pool, NULL);
  for (size_t i = 0; i < alphabet_length; ++i)
    scp_intern (&pool, phonetic_alphabet[i], SIZE_MAX);
  //scp_foreach(&pool, print_entry);

  for (size_t i = 0; i < alphabet_length; ++i)
    printf ("Test %lu: %s (expected %s)\n", i,
            scp_intern (&pool, phonetic_alphabet[i], SIZE_MAX), phonetic_alphabet[i]);
  scp_fini (&pool);
  return EXIT_SUCCESS;
}