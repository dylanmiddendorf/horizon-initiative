import pandas as pd
import zlib

from flatgraph.layers.ast import Cursor, TranslationUnit


def _max_depth(cursor: Cursor, level: int = 0) -> int:
    record = level + 1  # Include current node, as fallback value
    for child in cursor.children:
        record = max(record, _max_depth(child, level + 1))
    return record


def _bigram_term_frequency(cursor: Cursor) -> dict[int, float]:
    bigrams: dict[int, int] = {}

    def get_term_frequency(c: Cursor) -> None:
        for child in c.children:
            bigram_name = f"{c.properties['CODE']} -> {child.properties['CODE']}"
            bigram_hash = hex(zlib.crc32(bigram_name.encode()))[2:]
            if bigram_hash not in bigrams:
                bigrams[bigram_hash] = 0

            bigrams[bigram_hash] += 1
            get_term_frequency(child)

    get_term_frequency(cursor)  # Populate the bigram frequency map
    bigram_count = sum(bigrams.values())
    return {k: [v / bigram_count] for (k, v) in bigrams.items()}


def _leaf_term_frequency(cursor: Cursor) -> dict[int, float]:
    leafs: dict[int, int] = {}

    def get_term_frequency(c: Cursor) -> None:
        if len(children := c.children) == 0:
            leaf_hash = hex(zlib.crc32(c.properties["CODE"].encode()))[2:]
            leafs[leaf_hash] = leafs.get(leaf_hash, 0) + 1
            return  # Since this is the leaf, there are no children

        for child in children:
            get_term_frequency(child)

    get_term_frequency(cursor)  # Populate the leaf frequency map
    bigram_count = sum(leafs.values())
    return {k: v / bigram_count for (k, v) in leafs.items()}


def _average_leaf_depth(cursor: Cursor) -> dict[int, int]:
    leafs: dict[int, tuple[int, int]] = {}

    def get_average_depth(c: Cursor, depth: int = 0) -> None:
        if len(children := c.children) == 0:
            leaf_hash = hex(zlib.crc32(c.properties["CODE"].encode()))[2:]
            if leaf_hash not in leafs:
                leafs[leaf_hash] = (0, 0)
            a, n = leafs[leaf_hash]  # `a` is the summation of depth
            leafs[leaf_hash] = (a + depth, n + 1)
            return  # Since this is the leaf, there are no children

        for child in children:
            get_average_depth(child, depth + 1)

    get_average_depth(cursor)  # Populate the leaf frequency map
    return {k: a / n for (k, (a, n)) in leafs.items()}


def export_bigram_term_frequency(source_file: str, output_file: str) -> None:
    tu = TranslationUnit.from_source(source_file)
    bigrams = _bigram_term_frequency(tu.cursor)
    
    bigrams_dataframe = pd.DataFrame.from_dict(bigrams)
    
    bigrams_dataframe.to_csv(output_file)


