# Compiler and flags
CC = gcc
CFLAGS = -Wall -Wextra -Iinclude
LIBS = -lm

# Directories
SRC_DIR = src
INCLUDE_DIR = include
OBJ_DIR = obj
BIN_DIR = bin

# Target executable
TARGET = $(BIN_DIR)/caliskan_2015

# Find all source files
SRC_FILES = $(shell find $(SRC_DIR) -name '*.c')
# Generate object files from source files
OBJ_FILES = $(patsubst $(SRC_DIR)/%.c, $(OBJ_DIR)/%.o, $(SRC_FILES))

# Default target
all: $(TARGET)

# Rule to build the target executable
$(TARGET): $(OBJ_FILES)
	@mkdir -p $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $^ $(LIBS)

# Rule to build object files
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

# Rule to clean the build
clean:
	rm -rf $(OBJ_DIR) $(BIN_DIR)

# Rule to print debugging info (optional)
debug:
	@echo "Source files: $(SRC_FILES)"
	@echo "Object files: $(OBJ_FILES)"
	@echo "Target: $(TARGET)"

# Phony targets
.PHONY: all clean debug
