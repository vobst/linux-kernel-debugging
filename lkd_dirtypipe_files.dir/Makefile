.PHONY: format clean

all: poc

poc: poc.c
	gcc -g -O0 -o poc poc.c

format:
	astyle --options="astyle-code-format.cfg" "poc.c*"

clean:
	rm -f poc
