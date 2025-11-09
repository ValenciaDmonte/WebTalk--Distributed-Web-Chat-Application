#!/usr/bin/env python3
import sys
for line in sys.stdin:
    page = line.strip().split()[0]
    print(f"{page}\t1")
