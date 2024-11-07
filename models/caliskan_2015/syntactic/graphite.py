#!/usr/bin/env python
# Copright (C) 2024 Dylan Middendorf
# SPDX-License-Identifier: BSD-2-Clause

from argparse import ArgumentParser, Namespace

from flatgraph import Graph
from flatgraph.layers.ast import AST


def cpg_files(args: Namespace):
    with Graph(args.cpg, "r") as cpg:
        schema = cpg.schema  # Reduce additional method overhead
        for file_node in schema.nodes[schema.index["FILE"]]:
            if file_node._properties["NAME"] in ("<includes>", "<unknown>"):
                continue  # Present in all cpg databases
            print(file_node._properties["NAME"])


def cpg_tree(args: Namespace):
    root = AST.open(args.cpg)  # Only extract the AST layer

    def traverse(node: AST, indentation: str = "") -> None:
        if indentation:
            print(indentation, end=' ')
            is_tail = indentation[-3] == '└' # Final node in the level?
            indentation = f'{indentation[:-3]}{' ' if is_tail else '│'}   '
        
        print(node.name, node.properties['CODE'].encode())
        n = len(node.children)  # number of children in given node
        for idx, child in enumerate(node.children, start=1):
            traverse(child, indentation + ("├──" if idx < n else "└──"))

    traverse(root)


def main():
    parser = ArgumentParser()
    operations = parser.add_mutually_exclusive_group(required=True)

    operations.add_argument(
        "--list-files",
        action="store_const",
        const=cpg_files,
        dest="operation",
    )
    operations.add_argument(
        "--tree",
        action="store_const",
        const=cpg_tree,
        dest="operation",
    )

    parser.add_argument("cpg")
    args = parser.parse_args()
    args.operation(args)


if __name__ == "__main__":
    main()
