CXX = g++
CXXFLAGS = -O2 -std=c++17 -Wall
LDFLAGS = -lm

SRC = $(wildcard *.cpp)
BINS = $(patsubst %.cpp,../bin/cpp/%,$(filter-out bench_util.cpp,$(SRC)))

all: $(BINS)

../bin/cpp/%: %.cpp bench_util.cpp bench_util.hpp
	@mkdir -p ../bin/cpp
	$(CXX) $(CXXFLAGS) $< bench_util.cpp -o $@ $(LDFLAGS)

clean:
	rm -rf ../bin/cpp

.PHONY: all clean
