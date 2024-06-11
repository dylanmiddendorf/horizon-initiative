# Define the compiler
CC = gcc

# Define compiler flags
CFLAGS = -Wall -Wextra -Werror -Iinclude -Ilib/log.c/src

# Define the directories
SRC_PATH := src
INC_PATH := include
LIB_PATH := lib
BIN_PATH := bin
OBJ_PATH := obj

# Define the output executable
TARGET = $(BIN_PATH)/caliskan_2015

# Find all the source files
SRCFILES = $(shell find $(SRC_PATH) -name '*.c')
OBJFILES = $(patsubst $(SRC_PATH)/%.c, $(OBJ_PATH)/%.o, $(SRCFILES))

# Libraries (optional, can add more libraries if needed)
LIBS = -lm

# Default goal
all: $(TARGET)

# Build the target executable
$(TARGET): $(OBJFILES) | $(BIN_PATH)
	$(CC) $(OBJFILES) -o $@ $(LIBS)

# Compile source files to object files
$(OBJ_PATH)/%.o: $(SRC_PATH)/%.c | $(OBJ_PATH)
	$(CC) $(CFLAGS) -c $< -o $@

# Create build and bin directories if they don't exist
$(OBJ_PATH):
	mkdir -p $(OBJ_PATH)

$(BIN_PATH):
	mkdir -p $(BIN_PATH)

# Clean build files
clean:
	rm -rf $(OBJ_PATH) $(BIN_PATH)

# Include dependencies (optional)
-include $(OBJFILES:.o=.d)

# Generate dependencies (optional)
$(OBJ_PATH)/%.d: $(SRCDIR)/%.c
	$(CC) $(CFLAGS) -MM -MT $(patsubst %.c, $(OBJ_PATH)/%.o, $<) $< > $@

# Phony targets
.PHONY: all clean
