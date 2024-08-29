#!/usr/bin/env python
# Copright (C) 2024 Dylan Middendorf
# SPDX-License-Identifier: BSD-2-Clause

from argparse import ArgumentParser, Namespace
import glob
import zlib

from os import PathLike
from typing import Literal, Optional, Sequence

import pandas as pd

from flatgraph.layers.ast import AST


# fmt: off
AST_NODE_TYPES = [
    "ANNOTATION", "ANNOTATION_LITERAL", "ANNOTATION_PARAMETER",
    "ANNOTATION_PARAMETER_ASSIGN", "ARRAY_INITIALIZER", "BLOCK", "CALL",
    "CALL_REPR", "COMMENT", "CONTROL_STRUCTURE", "FIELD_IDENTIFIER", "FILE",
    "IDENTIFIER", "JUMP_LABEL", "JUMP_TARGET", "LITERAL", "LOCAL", "MEMBER",
    "METHOD", "METHOD_PARAMETER_IN", "METHOD_PARAMETER_OUT", "METHOD_REF",
    "METHOD_RETURN", "MODIFIER", "NAMESPACE", "NAMESPACE_BLOCK", "RETURN",
    "TYPE_ARGUMENT", "TYPE_DECL", "TYPE_PARAMETER", "TYPE_REF", "UNKNOWN"
]
# fmt: on


def export_static(
    sources: str | Sequence[str],
    output: str | bytes | PathLike,
    format: Literal["csv"] = "csv",
) -> None:
    """
    Exports static features from the specified source code files or code
    property graphs (CPGs) to the designated output file in the given format.

    The method extracts the following static features, as defined in
    Caliskan-Islam et al.:

    - `MaxDepthASTNode`: The maximum depth of an AST node.
    - `ASTNodeTypesTF`: Term frequency of AST node types, excluding leaf nodes.
    - `ASTNodeTypesTFIDF`: TF-IDF of AST node types, excluding leaf nodes.
    - `ASTNodeTypeAvgDep`: Average depth of AST node types, excluding leaf nodes.
    - `cppKeywords` The term frequency of C++ keywords.

    Args:
        sources: A string or sequence of strings representing the source code
            files or CPGs to be processed.
        output: A string, bytes object, or Path-like object specifying the
            output file path.
        format: The desired output format. Currently, only "csv" is supported.
    """

    if format != "csv":
        raise NotImplementedError()

    # TODO: Implement `ASTNodeTypesTFIDF`
    # TODO: Implement `cppKeywords` (lexical)

    def max_node_depth(node: AST, depth: int = 0) -> int:
        """Find the maximum depth of an AST node."""
        max_depth = depth + 1  # Include current node (+1)
        for child in node.children:
            # TODO: find clever way to handle max recusion errors
            max_depth = max(max_depth, max_node_depth(child, depth + 1))
        return max_depth

    def node_freqency(node: AST) -> None:
        """Find the term frequency (TF) of all AST node types, excluding leaves."""
        if len(children := node.children) == 0:
            return  # Exclude leaves from term frequency

        node_frequencies[AST_NODE_TYPES.index(node.name)] += 1
        for child in children:
            node_freqency(child)

    def average_node_depth(node: AST, depth: int = 0) -> None:
        """Find the average depth of all AST node types, excluding leaves."""
        if len(children := node.children) == 0:
            return  # Exclude leaves from average depth

        node_type = AST_NODE_TYPES.index(node.name)  # Micro-optimzation
        summation, count = node_depths[node_type]  # Unpack previous average
        node_depths[node_type] = (summation + depth + 1, count + 1)
        for child in children:  # Recursivley update the depths
            average_node_depth(child, depth + 1)

    with open(output, "wt", encoding="utf-8") as output_file:
        depth_features = map(lambda f: f"{f}-AD", AST_NODE_TYPES)
        frequency_features = map(lambda f: f"{f}-TF", AST_NODE_TYPES)
        output_file.write(
            ",".join(("source", "max-depth", *depth_features, *frequency_features))
            + "\n" # Terminate CSV field names
        )

        for source in sources:
            root = AST.open(source)

            node_frequencies = [0] * len(AST_NODE_TYPES)
            node_depths = [(0, 0)] * len(AST_NODE_TYPES)

            node_freqency(root)  # Populates `node_frequencies`
            average_node_depth(root)  # Populates `node_depths`

            node_count = sum(node_frequencies)
            node_frequencies = [f / node_count for f in node_frequencies]
            node_depths = [s / max(n, 1) for (s, n) in node_depths]

            output_file.write(f"{root.properties['NAME']},{max_node_depth(root)},")
            output_file.write(''.join(map(lambda f: f"{f:.4},", node_frequencies)))
            output_file.write(",".join(map(lambda f: f"{f:.4}", node_depths)))
            output_file.write("\n")  # Terminate the record with a line break


def export_leaves(root: AST, author: str, dataset: pd.DataFrame) -> None:
    pass


def export_bigrams(root: AST, author: str, dataset: pd.DataFrame) -> None:
    def unique_bigrams(root: AST) -> set[int]:
        bigrams: set[int] = set()

        def extract(node: AST) -> None:
            for child in node.children:
                bigrams.add(zlib.crc32(f"{node.code} -> {child.code}".encode()))
                extract(child)  # Recursivley extract bigrams from the tree

        extract(root)
        return bigrams


def _parse_arguments(args: Optional[Sequence[str]] = None) -> Namespace:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    syntactic_parser = subparsers.add_parser("syntactic")
    syntactic_parser.add_argument(
        "--bigram-output",
        default="syntactic_bigrams.csv",
        required=False,
        dest="bigram_path",
        metavar="<file>",
    )
    syntactic_parser.add_argument(
        "--leaf-output",
        default="syntactic_leaves.csv",
        dest="leaf_path",
        required=False,
        metavar="<file>",
    )
    syntactic_parser.add_argument(
        "--output",
        default="syntactic.csv",
        dest="static_path",
        required=False,
        metavar="<file>",
    )

    syntactic_parser.add_argument("files", nargs="+", metavar="FILE")
    return parser.parse_args(args)  # If none are supplied, fall back to CLI


def main():
    args = _parse_arguments()
    export_static(args.files, args.static_path)


if __name__ == "__main__":
    main()
