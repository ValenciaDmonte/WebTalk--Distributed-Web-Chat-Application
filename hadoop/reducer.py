#!/usr/bin/env python3
import sys
current_key = None
count = 0
for line in sys.stdin:
    key, val = line.strip().split("\t")
    val = int(val)
    if key == current_key:
        count += val
    else:
        if current_key:
            print(f"{current_key}\t{count}")
        current_key = key
        count = val
if current_key:
    print(f"{current_key}\t{count}")
