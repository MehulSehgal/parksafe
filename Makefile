CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra

all: safety_engine

safety_engine: safety_engine.cpp
	$(CXX) $(CXXFLAGS) -o safety_engine safety_engine.cpp

clean:
	rm -f safety_engine

.PHONY: all clean
