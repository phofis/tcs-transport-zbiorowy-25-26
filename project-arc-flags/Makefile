CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -pedantic
LDFLAGS ?=

NVCC ?= nvcc
NVCCFLAGS ?= -O2 -std=c++17 -ccbin g++ -arch sm_61

METIS_PREFIX ?= /usr/local
METIS_INC ?= $(METIS_PREFIX)/include
METIS_LIB ?= $(METIS_PREFIX)/lib

REGION_COUNT ?= 64
PARTITION_SEED ?= 42

SRC_DIR := src
BIN_DIR := bin

PARTITION_SRCS := $(SRC_DIR)/partition_main.cpp $(SRC_DIR)/utils.cpp
PREPROCESS_SRCS := $(SRC_DIR)/preprocess.cpp $(SRC_DIR)/utils.cpp
PREPROCESS_CUDA_SRC := $(SRC_DIR)/preprocess.cu
QUERY_SRCS := $(SRC_DIR)/query.cpp $(SRC_DIR)/utils.cpp

PARTITION_BIN := $(BIN_DIR)/partition
PREPROCESS_BIN := $(BIN_DIR)/preprocess
PREPROCESS_CUDA_BIN := $(BIN_DIR)/preprocess_cuda
QUERY_BIN := $(BIN_DIR)/query

PARTITION_CXXFLAGS := $(CXXFLAGS) \
	-I$(METIS_INC) \
	-DPARTITION_REGIONS=$(REGION_COUNT) \
	-DPARTITION_SEED=$(PARTITION_SEED)

PARTITION_LDFLAGS := $(LDFLAGS) \
	-L$(METIS_LIB) \
	-Wl,-rpath,$(METIS_LIB) \
	-lmetis

PREPROCESS_CXXFLAGS := $(CXXFLAGS)
PREPROCESS_LDFLAGS := $(LDFLAGS)
PREPROCESS_CUFLAGS := $(CUFLAGS) 
QUERY_CXXFLAGS := $(CXXFLAGS)
QUERY_LDFLAGS := $(LDFLAGS)

TEST_SRCS := test/test_query.cpp $(SRC_DIR)/utils.cpp
TEST_BIN := $(BIN_DIR)/test_query
TEST_CXXFLAGS := $(CXXFLAGS)
TEST_LDFLAGS := $(LDFLAGS)

GENERATE_SRCS := test/generate_test.cpp $(SRC_DIR)/utils.cpp
GENERATE_BIN := $(BIN_DIR)/generate_test
GENERATE_CXXFLAGS := $(CXXFLAGS)
GENERATE_LDFLAGS := $(LDFLAGS)

GRAPH_IN ?=
QUERIES_IN ?=

PARTITION_DIR ?= partition
FLAGS_DIR ?= flags
OUT_DIR ?= out
GRAPH_BASE := $(notdir $(basename $(GRAPH_IN)))

PARTITION_BIN_OUT := $(PARTITION_DIR)/partition.$(GRAPH_BASE).bin
PARTITION_TXT_OUT := $(PARTITION_DIR)/partition.$(GRAPH_BASE).txt

FLAGS_BIN_OUT := $(FLAGS_DIR)/preprocess.$(GRAPH_BASE).bin
FLAGS_TXT_OUT := $(FLAGS_DIR)/preprocess.$(GRAPH_BASE).txt

QUERY_TXT_OUT := $(OUT_DIR)/query.$(GRAPH_BASE).txt

.PHONY: \
	all clean \
	partition preprocess query test \
	generate-test \
	partition-bin partition-txt \
	preprocess-bin preprocess-txt \
	query-bin query-txt \
	pipeline-bin pipeline-txt \
	run run-bin run-txt run-test

all: partition preprocess query

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

#
# BUILD
#

partition: $(PARTITION_BIN)

$(PARTITION_BIN): $(PARTITION_SRCS) $(SRC_DIR)/utils.hpp Makefile | $(BIN_DIR)
	$(CXX) $(PARTITION_CXXFLAGS) $(PARTITION_SRCS) -o $@ $(PARTITION_LDFLAGS)

preprocess: $(PREPROCESS_BIN)

$(PREPROCESS_BIN): $(PREPROCESS_SRCS) $(SRC_DIR)/utils.hpp Makefile | $(BIN_DIR)
	$(CXX) $(PREPROCESS_CXXFLAGS) $(PREPROCESS_SRCS) -o $@ $(PREPROCESS_LDFLAGS)

preprocess-cuda: $(PREPROCESS_CUDA_BIN)

$(PREPROCESS_CUDA_BIN): $(PREPROCESS_CUDA_SRC) $(SRC_DIR)/utils.cpp $(SRC_DIR)/utils.hpp Makefile | $(BIN_DIR)
	$(NVCC) $(NVCCFLAGS) \
		$(PREPROCESS_CUDA_SRC) \
		$(SRC_DIR)/utils.cpp \
		-o $@ $(PREPROCESS_LDFLAGS)

query: $(QUERY_BIN)

$(QUERY_BIN): $(QUERY_SRCS) $(SRC_DIR)/utils.hpp Makefile | $(BIN_DIR)
	$(CXX) $(QUERY_CXXFLAGS) $(QUERY_SRCS) -o $@ $(QUERY_LDFLAGS)

test: $(TEST_BIN)

$(TEST_BIN): $(TEST_SRCS) $(SRC_DIR)/utils.hpp Makefile | $(BIN_DIR)
	$(CXX) $(TEST_CXXFLAGS) -I$(SRC_DIR) $(TEST_SRCS) -o $@ $(TEST_LDFLAGS)

generate-test: $(GENERATE_BIN)

$(GENERATE_BIN): $(GENERATE_SRCS) $(SRC_DIR)/utils.hpp Makefile | $(BIN_DIR)
	$(CXX) $(GENERATE_CXXFLAGS) -I$(SRC_DIR) $(GENERATE_SRCS) -o $@ $(GENERATE_LDFLAGS)

run-test: test
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	@test -n "$(QUERIES_IN)" || (echo "QUERIES_IN is required" && exit 1)
	mkdir -p "$(OUT_DIR)"
	./$(TEST_BIN) \
		--graph "$(GRAPH_IN)" \
		--queries "$(QUERIES_IN)" \
		--out "$(OUT_DIR)/test_query.$(GRAPH_BASE).txt" \
		$(if $(FORMAT),--format $(FORMAT),)

#
# PARTITION
#

partition-bin: partition
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	mkdir -p "$(PARTITION_DIR)"
	$(PARTITION_BIN) \
		--graph "$(GRAPH_IN)" \
		--out "$(PARTITION_BIN_OUT)" \
		--format bin

partition-txt: partition
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	mkdir -p "$(PARTITION_DIR)"
	$(PARTITION_BIN) \
		--graph "$(GRAPH_IN)" \
		--out "$(PARTITION_TXT_OUT)" \
		--format txt

#
# PREPROCESS
#

preprocess-bin: partition-bin preprocess
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	mkdir -p "$(FLAGS_DIR)"
	$(PREPROCESS_BIN) \
		--graph "$(GRAPH_IN)" \
		--partition "$(PARTITION_BIN_OUT)" \
		--out "$(FLAGS_BIN_OUT)" \
		--format bin

preprocess-txt: partition-txt preprocess
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	mkdir -p "$(FLAGS_DIR)"
	$(PREPROCESS_BIN) \
		--graph "$(GRAPH_IN)" \
		--partition "$(PARTITION_TXT_OUT)" \
		--out "$(FLAGS_TXT_OUT)" \
		--format txt
preprocess-cuda-bin: partition-bin preprocess-cuda
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	mkdir -p "$(FLAGS_DIR)"
	$(PREPROCESS_CUDA_BIN) \
		--graph "$(GRAPH_IN)" \
		--partition "$(PARTITION_BIN_OUT)" \
		--out "$(FLAGS_BIN_OUT)" \
		--format bin
preprocess-cuda-txt: partition-txt preprocess-cuda
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	mkdir -p "$(FLAGS_DIR)"
	$(PREPROCESS_CUDA_BIN) \
		--graph "$(GRAPH_IN)" \
		--partition "$(PARTITION_TXT_OUT)" \
		--out "$(FLAGS_BIN_OUT)" \
		--format txt

#
# QUERY EXECUTION
#

query-bin: 
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	@test -n "$(QUERIES_IN)" || (echo "QUERIES_IN is required" && exit 1)
	mkdir -p "$(OUT_DIR)"
	$(QUERY_BIN) \
		--graph "$(GRAPH_IN)" \
		--partition "$(PARTITION_BIN_OUT)" \
		--flags "$(FLAGS_BIN_OUT)" \
		--queries "$(QUERIES_IN)" \
		--out "$(QUERY_TXT_OUT)"

query-txt: 
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	@test -n "$(QUERIES_IN)" || (echo "QUERIES_IN is required" && exit 1)
	mkdir -p "$(OUT_DIR)"
	$(QUERY_BIN) \
		--graph "$(GRAPH_IN)" \
		--partition "$(PARTITION_TXT_OUT)" \
		--flags "$(FLAGS_TXT_OUT)" \
		--queries "$(QUERIES_IN)" \
		--out "$(QUERY_TXT_OUT)"

#
# FULL PREPROCESSING PIPELINE
#

pipeline-bin: preprocess-bin query

pipeline-txt: preprocess-txt query

pipeline-cuda-bin: preprocess-cuda-bin query

pipeline-cuda-txt: preprocess-cuda-txt query

#
# RUN ONLY
#

run: run-bin

run-bin: query-bin

run-txt: query-txt


run-compare: generate-test test
	@test -n "$(GRAPH_IN)" || (echo "GRAPH_IN is required" && exit 1)
	mkdir -p "$(OUT_DIR)"
	# generate queries (text format)
	./$(GENERATE_BIN) --graph "$(GRAPH_IN)" --out "$(OUT_DIR)/queries.txt" --format bin $(if $(COUNT),--count $(COUNT),--count 1000)

	# run baseline dijkstra test
	./$(TEST_BIN) --graph "$(GRAPH_IN)" --queries "$(OUT_DIR)/queries.txt" --out "$(OUT_DIR)/baseline.$(GRAPH_BASE).txt"
	# run arcflags query
	./$(QUERY_BIN) --graph "$(GRAPH_IN)" --partition "$(PARTITION_BIN_OUT)" --flags "$(FLAGS_BIN_OUT)" --queries "$(OUT_DIR)/queries.txt" --out "$(OUT_DIR)/arcflags.$(GRAPH_BASE).txt"
	# compare
	diff -u "$(OUT_DIR)/baseline.$(GRAPH_BASE).txt" "$(OUT_DIR)/arcflags.$(GRAPH_BASE).txt" || (echo "Outputs differ" && exit 2)
	@echo "Outputs match"

clean:
	rm -rf \
		"$(BIN_DIR)" \
		"$(PARTITION_DIR)" \
		"$(FLAGS_DIR)" \
		"$(OUT_DIR)" \
		"$(PREPROCESS_DIR)"