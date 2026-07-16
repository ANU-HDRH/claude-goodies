#!/usr/bin/env python3
"""Unit tests for check-presentation.py's token decoder (Phase 1 edge fix).

Covers the classification the golden SVG tests can't easily reach:
  - all three real d2 edge shapes normalise to the right key
  - a container prefix applies to BOTH endpoints
  - `<->` endpoints are sorted (tag direction irrelevant)
  - `~Z0`-style internals are ignored, NOT counted as nodes
  - an edge-SHAPED token that fails EDGE_RE is WARNED, never silently dropped
"""
import base64
import importlib.util
import os
import re
from collections import Counter

HERE = os.path.dirname(__file__)
CHK = os.path.join(HERE, "..", "references", "check-presentation.py")
spec = importlib.util.spec_from_file_location("chk", CHK)
chk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chk)


def classify(decoded_tokens):
    """Run the decoder's per-token logic over already-decoded strings."""
    nodes, edges, warns, seen = set(), Counter(), [], set()
    for dec in decoded_tokens:
        m = chk.EDGE_RE.match(dec)
        if m:
            edges[chk.norm_edge(m["prefix"], m["a"].strip(), m["b"].strip(), m["op"])] += 1
        elif chk.EDGE_HINT_RE.search(dec):
            if dec not in seen:
                warns.append(dec)
        elif chk.NODE_RE.match(dec):
            nodes.add(dec)
        seen.add(dec)
    return nodes, edges, warns


def test_edge_shapes_normalise():
    n, e, w = classify([
        "(author -> build.content)[0]",   # cross-container, unprefixed
        "build.(content -> gen)[0]",       # container-internal, prefixed
        "request.(user <-> host)[0]",      # bidirectional, prefixed
    ])
    assert e[("author", "build.content", True)] == 1
    assert e[("build.content", "build.gen", True)] == 1
    # <-> endpoints sorted: host < user
    assert e[("request.host", "request.user", False)] == 1
    assert not w


def test_parallel_edges_counted_as_multiset():
    _, e, _ = classify(["build.(content -> gen)[0]", "build.(content -> gen)[1]"])
    assert e[("build.content", "build.gen", True)] == 2


def test_bidir_key_is_order_independent():
    _, e1, _ = classify(["(a <-> b)[0]"])
    _, e2, _ = classify(["(b <-> a)[0]"])
    assert e1 == e2


def test_z_internals_ignored_not_nodes():
    n, e, w = classify(["~Z0", "~Z1"])
    assert n == set() and not e and not w


def test_edge_shaped_but_unparseable_warns():
    n, e, w = classify(["(orphan -> thing) no-index"])
    assert w == ["(orphan -> thing) no-index"]
    assert not e


def test_dotted_node_still_a_node():
    n, _, _ = classify(["build.content"])
    assert n == {"build.content"}


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok   {name}")
            except AssertionError as ex:
                print(f"  FAIL {name}: {ex}")
                fails += 1
    raise SystemExit(1 if fails else 0)
