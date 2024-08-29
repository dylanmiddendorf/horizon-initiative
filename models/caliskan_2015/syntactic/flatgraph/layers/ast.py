# Copright (C) 2024 Dylan Middendorf
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

import subprocess
import tempfile

from os import PathLike
from typing import Optional

from flatgraph import Edge, Graph, Node, Property


class AST:
    def __init__(self, graph: Graph, node: Node) -> None:
        self._graph = graph
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
                AST(self._graph, e.destination)
                for e in self._node.edges
                if e.direction == Edge.OUTGOING and e.name in ("AST",)
            ]

        return self._children

    @property
    def code(self) -> str:
        return self.properties["CODE"]

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
    def from_cpg(
        cls,
        cpg: str | bytes | PathLike,
        source: Optional[str | bytes | PathLike] = None,
    ) -> AST:
        def is_source(node: Node) -> bool:
            if node._properties["NAME"] in ("<includes>", "<unknown>"):
                return False
            return source is None or node._properties["NAME"] == source

        graph = Graph(cpg, "r")  # Parse the database's manifest
        file_nodes = graph.schema.nodes[graph.schema.index["FILE"]]
        file_nodes: list[Node] = list(filter(is_source, file_nodes))

        if len(file_nodes) == 1:
            return cls(graph, file_nodes[0])  # Unpack the target file in the CPG
        raise ValueError("ambigous source file")

    @classmethod
    def open(cls, filename: str | bytes | PathLike) -> AST:
        try:
            return cls.from_cpg(filename)
        except Exception as e:
            return cls.from_source(filename)
    
    def close(self) -> None:
        return self._graph.close()
        
    def __enter__(self) -> AST:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

# TODO: parse & dump
