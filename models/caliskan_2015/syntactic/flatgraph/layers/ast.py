from __future__ import annotations

import subprocess
import tempfile

from os import PathLike
from typing import Union

from flatgraph import Edge, Graph, Node, Property


class AST:
    def __init__(self, node: Node) -> None:
        self._node = node
        self._children: list[AST] = None

    @property
    def name(self) -> str:
        return self._node.name

    @property
    def properties(self) -> dict[str, Property]:
        return self._node._properties

    @property
    def children(self) -> list[AST]:
        if self._children is None:
            self._children = [
                AST(e.destination)
                for e in self._node.edges
                if e.direction == Edge.OUTGOING and e.name in ("AST",)
            ]

        return self._children

    @classmethod
    def from_source(cls, source: str | bytes | PathLike) -> AST:
        # joern-parse dumps the output of the CPG to either `cpg.bin`, or a
        # specified file (-o flag). Since the user doesn't manually generate
        # the CPG, we will create a temporary file for Joern to use.
        with tempfile.NamedTemporaryFile("wb", delete_on_close=False) as cpg:
            pass

        # Utilize Joern to generate the flat graph for AST traversal
        subprocess.run(["joern-parse", "-o", cpg.name, source], check=True)
        return cls.from_cpg(cpg.name, source)

    @classmethod
    def from_cpg(cls, cpg: str | bytes | PathLike) -> AST:
        graph = Graph(cpg, "r")  # Parse the database's manifest
        file_node_type = graph.schema.index["FILE"]
        for file_node in graph.schema.nodes[file_node_type]:
            if file_node._properties["NAME"] == "main.cpp":
                return cls(file_node)
        raise ValueError()

# TODO: parse & dump
