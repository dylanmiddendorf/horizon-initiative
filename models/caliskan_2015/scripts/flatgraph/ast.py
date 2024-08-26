from __future__ import annotations

import subprocess
import tempfile

from os import PathLike
from typing import Union

from flatgraph import Edge, Graph, Node, Property


class Cursor:
    def __init__(self, node: Node) -> None:
        self._node = node
        self._children: list[Cursor] = None

    @property
    def name(self) -> str:
        return self._node.name
    
    @property
    def properties(self) -> dict[str, Property]:
        return self._node._properties

    @property
    def children(self) -> list[Cursor]:
        if self._children is None:
            self._children = [
                Cursor(e.destination)
                for e in self._node.edges
                if e.direction == Edge.OUTGOING and e.name in ("AST",)
            ]

        return self._children


class TranslationUnit:
    def __init__(self, graph: Graph, name) -> None:
        self._graph = graph
        self._name = name
        self._cursor: Cursor = None

    @classmethod
    def from_source(cls, filename: Union[str, bytes, PathLike]) -> TranslationUnit:
        # joern-parse dumps the output of the CPG to either `cpg.bin`, or a
        # specified file (-o flag). Since the user doesn't manually generate
        # the CPG, we will create a temporary file for Joern to use.
        with tempfile.NamedTemporaryFile("wb", delete_on_close=False) as cpg:
            pass
        
        # Utilize Joern to generate the flat graph for traversal
        subprocess.run(["joern-parse", "-o", cpg.name, filename], check=True)
        return cls.from_cpg(cpg.name, filename)

    @classmethod
    def from_cpg(cls, cpg_name, filename) -> TranslationUnit:
        return cls(Graph(cpg_name, "r"), filename)
    
    @property
    def cursor(self) -> Cursor:
        if self._cursor is not None:
            return self._cursor
        
        file_node_type = self._graph.schema.index['FILE']
        for file in self._graph.schema.nodes[file_node_type]:
            if file._properties['NAME'] == 'main.cpp':
                self._cursor = Cursor(file)
                return self._cursor
        raise ValueError()
