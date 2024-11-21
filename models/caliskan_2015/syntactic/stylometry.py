#!/usr/bin/env python
# Copright (C) 2024 Dylan Middendorf
# SPDX-License-Identifier: BSD-2-Clause

from argparse import ArgumentParser, Namespace
import zlib
import os

from os import PathLike
from typing import Literal, Optional, Sequence

import pandas as pd

from flatgraph.layers.ast import AST
from flatgraph import Graph

# TODO: Optimize by "digesting" CPGs, then exporting at once (decrease proccess
#       times, but increases memory usage)? Decouples feature extraction and
#       exportation, which will make the linter happy (too-many-locals) and my
#       heart/soul :)

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


def export_bigrams(
    sources: str | Sequence[str],
    output_filename: str | bytes | PathLike,
    output_format: Literal["csv"] = "csv",
) -> None:

    if output_format != "csv":
        raise NotImplementedError()

    unique_bigrams: set[int] = set()
    feature_set: list[dict[int, int]] = []

    def bigram_term_frequency(node: AST, features: dict[int, int]):
        for child in node.children:
            bigram_hash = zlib.crc32(f"{node.code} -> {child.code}".encode())
            features[bigram_hash] = features.get(bigram_hash, 0) + 1
            bigram_term_frequency(child, features)

    submission_authors: list[str] = []
    for source in sources:
        # TODO: shift from splitext to reading file signature
        if os.path.splitext(source)[1] != "bin":
            with Graph(source, "r") as graph:
                for graph_soure in graph.schema.sources:
                    root = AST(graph, graph_soure)
                    bigrams = {}  # Populated with bigram term frequency
                    source_filename: str = root.properties["NAME"]
                    author = source_filename[: source_filename.rindex("_")]
                    submission_authors.append(author)

                    bigram_term_frequency(root, bigrams)
                    unique_bigrams.update(bigrams.keys())
                    feature_set.append(bigrams)

        else:
            bigrams = {}  # Populated with bigram term frequency

            with AST.open(source) as root:
                # Resolve the author name from the source filename
                source_filename: str = root.properties["NAME"]
                author = source_filename[: source_filename.rindex("_")]
                submission_authors.append(author)

                bigram_term_frequency(root, bigrams)
                unique_bigrams.update(bigrams.keys())
                feature_set.append(bigrams)

    with open(output_filename, "wt", encoding="utf-8") as output:
        output.write(f"author,{','.join(map(lambda b: hex(b)[2:], unique_bigrams))}\n")

        for submission, bigram_frequency in enumerate(feature_set):
            bigram_count = sum(bigrams.values())

            output.write(submission_authors[submission])
            for bigram in unique_bigrams:
                output.write(f",{bigram_frequency.get(bigram, 0) / bigram_count:.3}")
            output.write("\n")  # Terminate the record entry and flush the buffer


def export_static(
    sources: str | Sequence[str],
    output_filename: str | bytes | PathLike,
    output_format: Literal["csv"] = "csv",
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
        output_format: The desired output format. Currently, only "csv" is
            supported.
    """

    if output_format != "csv":
        raise NotImplementedError()

    # TODO: Implement `cppKeywords` (lexical)

    def max_node_depth(node: AST, depth: int = 0) -> int:
        """Find the maximum depth of an AST node."""
        max_depth = depth + 1  # Include current node (+1)
        for child in node.children:
            # TODO: find clever way to handle max recusion errors
            max_depth = max(max_depth, max_node_depth(child, depth + 1))
        return max_depth

    def node_type_average_depth(
        node: AST,
        features: list[tuple[int, int]],
        depth: int = 0,
    ) -> None:
        """Find the average depth of all AST node types, excluding leaves."""
        if len(children := node.children) == 0:
            return  # Exclude leaves from average depth

        node_type = AST_NODE_TYPES.index(node.name)  # Micro-optimzation
        summation, count = features[node_type]  # Unpack previous average
        features[node_type] = (summation + depth + 1, count + 1)
        for child in children:  # Recursivley update the depths
            node_type_average_depth(child, features, depth + 1)

    max_depth: list[int] = []
    submission_authors: list[str] = []
    feature_set: list[list[tuple[int, int]]] = []
    node_usage: list[set[str]] = [set() for _ in range(len(AST_NODE_TYPES))]
    for idx, source in enumerate(sources):
        # TODO: shift from splitext to reading file signature
        if os.path.splitext(source)[1] != "bin":
            with Graph(source, "r") as graph:
                for graph_soure in graph.schema.sources:
                    average_depth = [(0, 0)] * len(AST_NODE_TYPES)
                    root = AST(graph, graph_soure)
                    source_filename: str = root.properties["NAME"]
                    author = source_filename[: source_filename.rindex("_")]

                    # Update author submissions with current submission
                    submission_authors.append(author)

                    max_depth.append(max_node_depth(root))
                    node_type_average_depth(root, average_depth)
                    feature_set.append(average_depth)

                    for node_idx, (_, count) in enumerate(average_depth):
                        if count > 0:  # Only add author if node is present
                            node_usage[node_idx].add(author)
        else:
            average_depth = [(0, 0)] * len(AST_NODE_TYPES)
            with AST.open(source) as root:
                # Resolve the author name from the source filename
                source_filename: str = root.properties["NAME"]
                author = source_filename[: source_filename.rindex("_")]

                # Update author submissions with current submission
                submission_authors.append(author)

                max_depth.append(max_node_depth(root))
                node_type_average_depth(root, average_depth)
                feature_set.append(average_depth)

                for node_idx, (_, count) in enumerate(average_depth):
                    if count > 0:  # Only add author if node is present
                        node_usage[node_idx].add(author)

    ratio = lambda f: f",{f[0]/max(f[1], 1):3}"  # TF / (# of authors used)
    document_frequency: list[int] = [len(n) for n in node_usage]
    with open(output_filename, "wt", encoding="utf-8") as output:
        output.write("author,max-depth")
        output.write("".join(map(lambda f: f",{f}-NF", AST_NODE_TYPES)))
        output.write("".join(map(lambda f: f",{f}-ID", AST_NODE_TYPES)))
        output.write("".join(map(lambda f: f",{f}-ND", AST_NODE_TYPES)) + "\n")

        for idx, submission_features in enumerate(feature_set):
            output.write(f"{submission_authors[idx]},{max_depth[idx]}")

            n = sum(map(lambda f: f[1], submission_features))
            term_frequency = [c / n for _, c in submission_features]

            output.write("".join(map(lambda tf: f",{tf:.3}", term_frequency)))
            output.write("".join(map(ratio, zip(term_frequency, document_frequency))))
            output.write("".join(map(ratio, submission_features)))
            output.write("\n")  # Flush and terminate the record


def export_leaves(
    sources: str | Sequence[str],
    output_filename: str | bytes | PathLike,
    output_format: Literal["csv"] = "csv",
) -> None:
    if output_format != "csv":
        raise NotImplementedError()

    unique_leaves: set[int] = set()
    feature_set: list[dict[int, int]] = []

    def leaf_term_frequency(
        node: AST, depth: int, features: dict[int, tuple[int, int]]
    ):
        if not node.children:
            node_hash = zlib.crc32(node.code.encode())
            count, sum_depth = features.get(node_hash, (0, 0))
            count, sum_depth = count + 1, sum_depth + depth
            features[node_hash] = (count, sum_depth)
            return  # Don't try to process any children

        for child in node.children:
            leaf_term_frequency(child, depth + 1, features)

    submission_authors: list[str] = []
    for source in sources:
        # TODO: shift from splitext to reading file signature
        if os.path.splitext(source)[1] != "bin":
            with Graph(source, "r") as graph:
                for graph_soure in graph.schema.sources:
                    root = AST(graph, graph_soure)
                    leaves = {}  # Populated with bigram term frequency
                    source_filename: str = root.properties["NAME"]
                    author = source_filename[: source_filename.rindex("_")]
                    submission_authors.append(author)

                    leaf_term_frequency(root, 0, leaves)
                    unique_leaves.update(leaves.keys())
                    feature_set.append(leaves)

        else:
            leaves = {}  # Populated with bigram term frequency

            with AST.open(source) as root:
                # Resolve the author name from the source filename
                source_filename: str = root.properties["NAME"]
                author = source_filename[: source_filename.rindex("_")]
                submission_authors.append(author)

                leaf_term_frequency(root, 0, leaves)
                unique_leaves.update(leaves.keys())
                feature_set.append(leaves)

    with open(output_filename, "wt", encoding="utf-8") as output:
        output.write(
            f"author,{','.join(map(lambda b: f'TF.{hex(b)[2:]},AD.{hex(b)[2:]}', unique_leaves))}\n"
        )

        for submission, leaves in enumerate(feature_set):
            leaf_count = sum(map(lambda f: f[0], leaves.values()))

            output.write(submission_authors[submission])
            for leaf in unique_leaves:
                count, depth = leaves.get(leaf, (0, 0))
                avg_depth = depth / count if count else -1.
                output.write(f",{count / leaf_count:.3},{avg_depth:.3}")
            output.write("\n")  # Terminate the record entry and flush the buffer


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
    export_bigrams(args.files, args.bigram_path)
    export_leaves(args.files, args.leaf_path)


if __name__ == "__main__":
    main()
