#include "../ctok.h"

#include <stdio.h>
#include <stdlib.h>

int
main (int argc, char *argv[])
{
  printf("Entering main...\n");
  cpp_tokenizer_t tok;
  const char *code
      = "int main(){ios::sync_with_stdio(false);cin.tie(0); "
        "cout.tie(0);int T = 1; cin >> T;while (T--)solve();return 0;}";
  cxt_init (&tok, code, NULL);

  while(cxt_has_more_tokens(&tok))
    printf ("Found \"%p\"\n", cxt_next_token (&tok));

  return EXIT_SUCCESS;
}