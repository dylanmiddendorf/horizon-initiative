# Copright (C) 2024 Dylan Middendorf
# SPDX-License-Identifier: BSD-2-Clause

"""Classes for reading and writing Joern flatgraph databases."""

from __future__ import annotations

import json
import os
import re
import struct

from os import PathLike
from typing import Any, BinaryIO, Literal, Optional, Union, cast

import zstandard as zstd

MAGIC_BYTES = b"FLT GRPH"
HEADER_FORMAT = f"<{len(MAGIC_BYTES)}sQ"

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
assert HEADER_SIZE == 0x10  # Verify header format is right size

UINT32_MAX = 0xFFFF_FFFF
"""A constant holding the maximum value of an unsigned 32-bit integer."""

Property = Union[bool, int, str, list[bool], list[int], list[str]]

# TODO: provide support for graph deletions
# TODO: de-couple the file open from the constructor, becuase future releases
#       might support several non-compatible versions of Flat Graph Databases


class DeserializationError(ValueError):
    """
    Exception raised for errors encountered during the deserialization process.
    """


class Edge:
    INCOMING = 0
    OUTGOING = 1

    def __init__(
        self,
        name: str,
        src: Node,
        dst: Node,
        direction: Literal[1, 2],
        prop: Optional[str] = None,
    ) -> None:
        self.name = name
        self.source = src
        self.destination = dst
        self.direction = direction
        self.property = prop


class Node:
    """A low-level implementation of a Flat Graph's node."""

    def __init__(
        self,
        name: str,
        edges: Optional[set[Edge]] = None,
        properties: Optional[dict[str, Property]] = None,
    ) -> None:
        self.name = name
        self.edges = edges if edges else set()

        self._properties = properties if properties else {}

    def add_property(self, name: str, value: Union[bool, int, str]) -> None:
        """Adds a property to the node.

        This method offers a flexible approach to property addition,
        accommodating variable property cardinalities. It can dynamically
        adjust a property's cardinality from zero to one or one to many, making
        it suitable for constructing nodes from serialized flatgraph databases.

        Args:
            name (str): The name of the property to add.
            value (Union[bool, int, str]): The value associated with the property.
        """
        if name not in self._properties:
            self._properties[name] = value
            return  # Assume the cardinality is one

        if not isinstance(self._properties[name], list):
            self._properties[name] = [self._properties[name]]
        self._properties[name].append(value)

    def __getitem__(self, name: str) -> Property:
        return self._properties[name]

    def __setitem__(self, name: str, value: str) -> None:
        self._properties[name] = value


class Schema:
    def __init__(
        self,
        nodes: list[list[Node]],
        index: dict[str, int],
    ) -> None:
        self.nodes = nodes
        self.index = index

    @classmethod
    def from_graph(cls, graph: Graph) -> Schema:
        manifest = graph.manifest  # Load manifest

        nodes: list[list[Node]] = []
        node_index: dict[str, int] = {}
        for idx, node in enumerate(manifest["nodes"]):
            node_index[node_label := node["nodeLabel"]] = idx
            nodes.append([Node(node_label) for _ in range(node["nnodes"])])

        cls._deserialize_edges(graph, nodes, node_index)
        cls._deserialize_properties(graph, nodes, node_index)

        return Schema(nodes, node_index)

    @staticmethod
    def _deserialize_edges(
        graph: Graph,
        nodes: list[list[Node]],
        node_index: dict[str, int],
    ) -> None:
        for edge in graph.manifest["edges"]:
            node_edge_counts = graph._zstd_decompress(**edge["qty"])
            neighbors = graph._zstd_decompress(**edge["neighbors"])

            name, src_node_type = edge["edgeLabel"], node_index[edge["nodeLabel"]]

            properties = ()
            if edge["property"] is not None:
                properties = graph._zstd_decompress(**edge["property"])

            if edge["edgeLabel"] == "AST" and edge["nodeLabel"] == "BLOCK":
                pass

            idx = 0  # Iteratively access the neighbors
            for src_node_idx, edge_count in enumerate(node_edge_counts[:-1]):
                src = cast(Node, nodes[src_node_type][src_node_idx])
                if edge_count:
                    for idx in range(idx, idx + edge_count):
                        dst_node_idx, dst_node_type = neighbors[idx]
                        dst = nodes[dst_node_type][dst_node_idx]
                        prop = properties[idx] if len(properties) else None
                        src.edges.add(Edge(name, src, dst, edge["inout"], prop))
                    idx += 1

    @staticmethod
    def _deserialize_properties(
        graph: Graph,
        nodes: list[list[Node]],
        node_index: dict[str, int],
    ) -> None:
        for prop in graph.manifest["properties"]:
            node_property_counts = graph._zstd_decompress(**prop["qty"])
            properties = graph._zstd_decompress(**prop["property"])
            name, node_type = prop["propertyLabel"], node_index[prop["nodeLabel"]]

            idx = 0
            for node_idx, property_count in enumerate(node_property_counts[:-1]):
                node = cast(Node, nodes[node_type][node_idx])
                if property_count:
                    for idx in range(idx, idx + property_count):
                        node.add_property(name, properties[idx])
                    idx += 1


class Graph:
    def __init__(
        self,
        name: Optional[Union[str, bytes, PathLike]] = None,
        mode: Literal["r", "w", "a", "x"] = "r",
        fileobj: Optional[BinaryIO] = None,
    ) -> None:
        if not name and not fileobj:
            raise ValueError("nothing to open")

        modes = {"r": "rb", "a": "r+b", "w": "wb", "x": "xb"}
        if mode not in modes:
            raise ValueError("unsupported file mode")

        if mode in {"w", "a", "x"}:
            # TODO: add write and read/write capabilities
            raise NotImplementedError()
        self.mode, self._mode = mode, modes[mode]

        if fileobj is None:
            # If append mode fails due to the absence of the file, switch to
            # write mode. Users may verify the mode to determine if a fallback
            # to write occurred.
            if self.mode == "a" and not os.path.exists(name):
                self.mode, self._mode = "w", "wb"

            # Binary I/O, so pylint: disable-next=unspecified-encoding
            fileobj = open(name, modes[mode])
            self._external_fileobj = False
        else:
            # Attempt to retrieve the name from the stream. If not provided,
            # execution can continue, as it is primarily used for object
            # serialization in `__str__` and `__repr__` methods.
            if (
                name is None
                and hasattr(fileobj, "name")
                and isinstance(fileobj.name, (str, bytes))
            ):
                name = fileobj.name

            # Infer the file mode from the stream if available to avoid obscure
            # errors during execution; otherwise the parameter is used.
            if hasattr(fileobj, "mode"):
                # Verify that the file mode is recognizable
                assert re.fullmatch(r"(?:a|x|r\+?|w\+?)b", fileobj.mode)
                self._mode = fileobj.mode

            self._external_fileobj = True

        self.name, self.fileobj = name, fileobj

        # Delcare internal structures (initalization happens upon first usage)
        self._schema = None
        self._manifest = None
        self._string_pool = None

    def close(self) -> None:
        """Close the database's underlying file descriptor/stream."""
        self.fileobj.close()

    @property
    def manifest(self) -> dict[str, Any]:
        """Get the graph's manifest."""

        if self._manifest is not None:
            return self._manifest

        self.fileobj.seek(0, os.SEEK_SET)
        header = self.fileobj.read(HEADER_SIZE)
        if len(header) < HEADER_SIZE:
            raise DeserializationError(
                f"corrupted file, expected at least {HEADER_SIZE} bytes, but "
                f"only found {len(header)}"
            )

        # Split and deserialize the magic bytes and manifest offset
        header: tuple[bytes, int] = struct.unpack_from(HEADER_FORMAT, header)
        if header[0] != MAGIC_BYTES:
            raise DeserializationError(
                f"corrupted file, expected header {MAGIC_BYTES} ({MAGIC_BYTES.hex(' ')}),"
                f"but found {header[0]} ({header[0].hex(' ')}) instead"
            )

        # Deserialize the manifest (JSON object)
        self.fileobj.seek(header[1], os.SEEK_SET)
        self._manifest = json.load(self.fileobj)
        return self._manifest

    @property
    def pool(self):
        """Get the graph's string pool."""

        if self._string_pool is not None:
            return self._string_pool
        self._string_pool = []  # Only try to deserialize once
        manifest = self.manifest  # Load graph's manifest

        # Parse the pool's index (`stringPoolLength`)
        index = self._zstd_decompress(**manifest["stringPoolLength"])

        # Parse the pool's strings (`stringPoolBytes`)
        pool = self._zstd_decompress(**manifest["stringPoolBytes"])

        # Ensure that the stream has been correctly decompressed
        assert len(pool) == manifest["stringPoolBytes"]["decompressedLength"]
        assert sum(index) == manifest["stringPoolBytes"]["decompressedLength"]

        offset = 0  # Running offset for `stringPoolBytes` substrings
        for length in index:
            self._string_pool.append(pool[offset : offset + length].decode())
            offset += length  # Prepare the offset for the next string
        return self._string_pool

    @property
    def schema(self):
        """Get the graph's schema."""
        if self._schema is None:
            self._schema = Schema.from_graph(self)
        return self._schema

    # The variable names in this method are intentionally aligned with the keys
    # found in the databases manifest/schema. This design choice enables
    # callers to invoke `self._zstd_decompress(**foo)` directly, without the
    # need to extract each argument individually. Additionally, one of the four
    # keys is "type", which redefines the builtin `type`. Therefore,
    # pylint: disable=invalid-name,redefined-builtin
    def _zstd_decompress(
        self,
        type: Literal["bool", "int", "string", "ref", "byte"],
        startOffset: int,
        compressedLength: int,
        decompressedLength: Optional[int] = None,
    ) -> Union[tuple[bool], tuple[int], tuple[str], tuple[tuple[int, int]], bytes]:
        """Decompress a ZStandard stream within the database.

        This method provides a standardized interface for decompressing
        ZStandard streams of various data types. It is primarily used during
        the deserialization of the database's manifest, enabling efficient
        extraction of quantities, neighbors, and properties from JSON objects.

        To decompress a stream at a specific offset, specify the `startOffset`
        and `compressedLength`. The `type` parameter determines the format of
        the decompressed data. For raw bytes, use "byte". For other types, the
        stream is parsed into a tuple of bools, integers, strings, or
        references (node index and type pairs).

        Args:
            type (Literal["bool", "int", "string", "ref", "byte"]): The data
                type of the compressed stream.
            startOffset (int): The absolute offset of the ZStandard stream
                within the file.
            compressedLength (int): The length of the compressed ZStandard
                stream.
            decompressedLength (Optional[int]): The expected length of the
                decompressed data.

        Raises:
            DeserializationError: If the decompressed stream's length does not
                match the expected length, or if the stream's decompressed
                length is not aligned to the specified type's width.
            ValueError: If the specified type is not one of the supported
                options.

        Returns:
            A tuple of the specified type, or the raw, decompressed ZStandard
                stream if the type is "byte".
        """

        self.fileobj.seek(startOffset)  # Align stream's cursor to the offset

        compressed = self.fileobj.read(compressedLength)
        if len(compressed) < compressedLength:
            raise DeserializationError(
                "An unexpected end-of-file (EOF) was reached while "
                f"decompressing the ZStandard stream. Expected {compressedLength} "
                f"bytes, but only {len(compressed)} bytes were read."
            )

        # Decompress the ZStandard stream to get the raw bytes
        decompressed = zstd.decompress(compressed)
        if decompressedLength is None:  # Ensure that
            decompressedLength = len(decompressedLength)
        assert len(decompressed) == decompressedLength

        if type == "bool":
            return struct.unpack(f"{decompressedLength}?", decompressed)
        if type == "int":
            if decompressedLength % 4:
                raise DeserializationError()
            return struct.unpack(f"<{decompressedLength // 4}I", decompressed)
        if type == "string":
            if decompressedLength % 4:
                raise DeserializationError()

            pool = self.pool  # Cache the string pool to remove function overhead
            handles = struct.unpack(f"<{decompressedLength // 4}I", decompressed)

            # TODO: add logging for invalid handles (outside of UINT32_MAX)
            # Remove invalid handles, before querying the string pool. This is
            # done, because deleted strings are denoted with `UINT32_MAX`.
            handles = filter(lambda i: i < len(pool), handles)
            return tuple(map(lambda i: pool[i], handles))
        if type == "ref":
            if decompressedLength % 8:
                raise DeserializationError()

            refs = struct.unpack(f"<{decompressedLength // 4}I", decompressed)
            return tuple((refs[r], refs[r + 1]) for r in range(0, len(refs), 2))
        if type == "byte":
            return decompressed
        raise ValueError()

    # pylint: enable=invalid-name,redefined-builtin

    def __enter__(self) -> Graph:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
