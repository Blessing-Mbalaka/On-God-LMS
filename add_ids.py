#!/usr/bin/env python3
"""
add_ids.py  – injects a unique "id" into every dict node of a JSON exam spec

Usage
-----
$ python add_ids.py exam.json             # prints JSON-with-ids to stdout
$ python add_ids.py exam.json -o new.json # writes to new.json in-place
"""

import json, uuid, argparse, sys, pathlib

import uuid

def ensure_ids(node, depth=0, seen=None):
    """
    Recursively adds a unique 'id' to every dictionary in a nested structure,
    safely avoiding circular references and recursion overflow.
    """
    MAX_DEPTH = 100
    if seen is None:
        seen = set()

    if depth > MAX_DEPTH:
        print(f"⚠️ [ensure_ids] Max recursion depth exceeded.")
        return

    if isinstance(node, dict):
        node_id = id(node)
        if node_id in seen:
            print(f"🛑 [ensure_ids] Circular reference detected. Skipping node.")
            return
        seen.add(node_id)

        node.setdefault("id", uuid.uuid4().hex)

        for v in node.values():
            ensure_ids(v, depth + 1, seen)

    elif isinstance(node, list):
        for v in node:
            ensure_ids(v, depth + 1, seen)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src", help="input JSON file")
    p.add_argument("-o", "--out", help="write result here (defaults to stdout)")
    args = p.parse_args()

    data = json.loads(pathlib.Path(args.src).read_text(encoding="utf-8"))
    ensure_ids(data)
    dumped = json.dumps(data, indent=2, ensure_ascii=False)

    if args.out:
        pathlib.Path(args.out).write_text(dumped, encoding="utf-8")
    else:
        sys.stdout.write(dumped)

if __name__ == "__main__":
    main()
