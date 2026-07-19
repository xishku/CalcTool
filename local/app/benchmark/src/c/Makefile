CC = gcc
CFLAGS = -O2 -Wall
LDFLAGS = -lm

# 获取参数
ARRAY_SIZE  := $(firstword $(filter --array-size=%,$(MAKEFLAGS) $(MAKEOVERRIDES)),--array-size=100000)
MATRIX_DIM  := $(firstword $(filter --matrix-dim=%,$(MAKEFLAGS) $(MAKEOVERRIDES)),--matrix-dim=500)

SRC = $(wildcard *.c)
BINS = $(patsubst %.c,../bin/c/%,$(filter-out bench_util.c,$(SRC)))

all: $(BINS)

../bin/c/%: %.c bench_util.c bench_util.h
	@mkdir -p ../bin/c
	$(CC) $(CFLAGS) $< bench_util.c -o $@ $(LDFLAGS)

clean:
	rm -rf ../bin/c

.PHONY: all clean
