CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -pedantic
LDFLAGS ?=

METIS_PREFIX ?= /usr/local
METIS_INC ?= $(METIS_PREFIX)/include
METIS_LIB ?= $(METIS_PREFIX)/lib

REGION_COUNT ?= 64
PARTITION_SEED ?= 42

SRC_DIR := src
BUILD_DIR := build
BIN_DIR := bin
TEST_DIR := tests

PARTITION_SRCS := $(SRC_DIR)/partition_main.cpp $(SRC_DIR)/utils.cpp
PARTITION_BIN := $(BIN_DIR)/partition

PARTITION_CXXFLAGS := $(CXXFLAGS) -I$(METIS_INC) -DPARTITION_REGIONS=$(REGION_COUNT) -DPARTITION_SEED=$(PARTITION_SEED)
PARTITION_LDFLAGS := $(LDFLAGS) -L$(METIS_LIB) -Wl,-rpath,$(METIS_LIB) -lmetis

GRAPH_IN ?=
QUERIES_IN ?=
PARTITION_DIR ?= partition
FLAGS_DIR ?= flags
OUT_DIR ?= out
FORMAT ?= bin
GRAPH_BASE := $(notdir $(basename $(GRAPH_IN)))
PARTITION_BIN_OUT := $(PARTITION_DIR)/partition.$(GRAPH_BASE).bin
PARTITION_TXT_OUT := $(PARTITION_DIR)/partition.$(GRAPH_BASE).txt
FLAGS_BIN_OUT := $(FLAGS_DIR)/preprocess.$(GRAPH_BASE).bin
FLAGS_TXT_OUT := $(FLAGS_DIR)/preprocess.$(GRAPH_BASE).txt
QUERY_BIN_OUT := $(OUT_DIR)/query.$(GRAPH_BASE).bin
QUERY_TXT_OUT := $(OUT_DIR)/query.$(GRAPH_BASE).txt

.PHONY: all clean partition preprocess preprocess_cuda query partition-bin partition-txt pipeline-bin pipeline-txt run run-bin run-txt

all: partition

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

partition: $(PARTITION_BIN)

$(PARTITION_BIN): $(PARTITION_SRCS) $(SRC_DIR)/utils.hpp Makefile | $(BIN_DIR)
	$(CXX) $(PARTITION_CXXFLAGS) $(PARTITION_SRCS) -o $@ $(PARTITION_LDFLAGS)

preprocess:
	@echo "preprocess target placeholder (expected: --graph $(GRAPH_IN) --partition <partition file> --out <flags file>)"

preprocess_cuda:
	@echo "preprocess_cuda target placeholder (expected: --graph $(GRAPH_IN) --partition <partition file> --out <flags file>)"

query:
	@echo "query target placeholder (expected: --graph $(GRAPH_IN) --partition <partition file> --flags <flags file> --queries $(QUERIES_IN) --out <query result file>)"

partition-bin: partition
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required, e.g. make partition-bin GRAPH_IN=graph.bin" && exit 1)
	mkdir -p "$(PARTITION_DIR)"
	$(PARTITION_BIN) --in "$(GRAPH_IN)" --out "$(PARTITION_BIN_OUT)" --format bin

partition-txt: partition
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required, e.g. make partition-txt GRAPH_IN=graph.txt" && exit 1)
	mkdir -p "$(PARTITION_DIR)"
	$(PARTITION_BIN) --in "$(GRAPH_IN)" --out "$(PARTITION_TXT_OUT)" --format txt

pipeline-bin: partition-bin preprocess query

pipeline-txt: partition-txt preprocess query

run: run-bin

run-bin: partition-bin
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required, e.g. make run-bin GRAPH_IN=graph.bin QUERIES_IN=queries.txt" && exit 1)
	@test -n "$(QUERIES_IN)" || (echo "QUERIES_IN is required, e.g. make run-bin GRAPH_IN=graph.bin QUERIES_IN=queries.txt" && exit 1)
	mkdir -p "$(FLAGS_DIR)" "$(OUT_DIR)"
	@echo "run-bin: partition output -> $(PARTITION_BIN_OUT)"
	@echo "run-bin: expected flags output -> $(FLAGS_BIN_OUT)"
	@echo "run-bin: expected query output -> $(QUERY_BIN_OUT)"
	@echo "run-bin: preprocess/query targets are placeholders until implemented"

run-txt: partition-txt
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required, e.g. make run-txt GRAPH_IN=graph.txt QUERIES_IN=queries.txt" && exit 1)
	@test -n "$(QUERIES_IN)" || (echo "QUERIES_IN is required, e.g. make run-txt GRAPH_IN=graph.txt QUERIES_IN=queries.txt" && exit 1)
	mkdir -p "$(FLAGS_DIR)" "$(OUT_DIR)"
	@echo "run-txt: partition output -> $(PARTITION_TXT_OUT)"
	@echo "run-txt: expected flags output -> $(FLAGS_TXT_OUT)"
	@echo "run-txt: expected query output -> $(QUERY_TXT_OUT)"
	@echo "run-txt: preprocess/query targets are placeholders until implemented"

clean:
	rm -rf "$(BUILD_DIR)" "$(BIN_DIR)" "$(PARTITION_DIR)" "$(FLAGS_DIR)" "$(OUT_DIR)"
