# Copyright (c) 2024 Dylan Middendorf.
# SPDX-License-Identifier: BSD-2-Clause

layout: data.o layout.o tests/layout-test.o
lexical: ctok.o map.o strpool.o data.o lexical.o tests/lexical-test.o

ctok.o: ctok.h strpool.h
data.o: data.h
layout.o: layout.h data.h
lexical.o: lexical.h ctok.h data.h map.h strpool.h
map.o: map.h
strpool.o: strpool.h

tests/layout-test.o: layout.h data.h
tests/lexical-test.o: lexical.h data.h

.PHONY: clean
clean:
	rm *.o tests/*.o