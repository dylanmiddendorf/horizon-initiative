import json  # Resource Deseralization
from os import path  # File Mangment
import re  # Regular Expressions

from tokenizer import Tokenizer

RESOURCE_PATH = path.join(path.dirname(path.realpath(__file__)), "resources")


def load_resource(name: str):
    with open(path.join(RESOURCE_PATH, name), encoding="utf-8") as fp:
        return json.load(fp)  # Desearalize json array/object


CPP_KEYWORDS = set(load_resource("cpp_keywords.json"))
CONTROL_KEYWORDS = ("do", "else-if", "if", "else", "switch", "for", "while")
NUMERIC_LITERAL_PATTERN = re.compile(
    r"""
    (0[0-7]*      # Octal
    |0x[0-9a-f]+  # Hexadecimal
    |0b[01]+      # Binary
    |[1-9][0-9]*  # Decimal
    )([ul]|ul{1,2}|l{1,2}u)? # Optional integer suffixes
    |
    ([0-9]+\.[0-9]*(e[+-]?[0-9]+)?       # generic floating point
    |\.[0-9]+                            # edge case... ".1"
    |[0-9]+e[+-]?[0-9]+                  # edge case... "1e2"
    |0x[0-9a-f]+\.[0-9a-f]*p[+-]?[0-9]+  # hexadecimal floating point voodoo
    )[fl]?""",
    re.IGNORECASE,
)


class LexicalFeatures:
    def __init__(self, file: str) -> None:
        tokenizer = Tokenizer()
        with open(file, "rt", encoding="utf-8") as fp:
            buffer = fp.read()  # Read whole file into temporary buffer
        tokenizer.digest(buffer)  # Tokenize the C++ *valid* file
        self.file_size = len(buffer)  # Used for general frequencies

        self._word_unigram_tf = {}
        self._keyword_frequency = {kw: 0 for kw in CONTROL_KEYWORDS}
        self._ternary_frequency = 0
        self._literal_frequency = 0
        self._macro_frequency = 0
        self._unique_keywords = 0

        self._max_depth = 0
        self._parse(tokenizer)

    def _parse(self, tokenizer: Tokenizer) -> None:
        self._unique_keywords = set()  # Use a set for unique keywords

        prev = None  # Previous token for else-if
        depth = 0  # The depth of control flow statements
        for token in tokenizer.tokens:
            # Feature #1: WordUnigramTF
            if token not in self._word_unigram_tf:
                self._word_unigram_tf[token] = 0
            self._word_unigram_tf[token] += 1

            # Feature #2: ln(num*keyword*/length)
            if prev == "else" and token == "if":
                self._keyword_frequency["else-if"] += 1
            elif token in CONTROL_KEYWORDS:
                self._keyword_frequency[token] += 1

            # Feature #3: ln(numTernary/length)
            elif token == "?":
                self._ternary_frequency += 1

            # Feature #6: ln(numLiterals/length)
            elif prev != "include" and token[0] == '"':
                self._literal_frequency += 1
            elif re.match(NUMERIC_LITERAL_PATTERN, token):
                self._literal_frequency += 1

            # Feature #7: ln(numKeywords/length)
            elif token in CPP_KEYWORDS:
                self._unique_keywords.add(token)

            # Feature #9: n(numMacros/length)
            elif prev == "#" and token == "define":
                self._macro_frequency

            # Feature #10: nestingDepth
            elif token == "{":
                self._max_depth = max(self._max_depth, depth := depth + 1)
            elif token == "}":
                depth -= 1

        n = len(tokenizer.tokens)  # Count of tokens for term frequency
        self._word_unigram_tf = {k: v / n for k, v in self._word_unigram_tf.items()}
        self._unique_keywords = len(self._unique_keywords)

    @property
    def term_frequency(self) -> dict[str, float]:
        return self._word_unigram_tf

    @property
    def keyword_frequency(self) -> dict[str, float]:
        return self._keyword_frequency

    def jsonify(self):
        """Convert the instance of the class to a JSON string.

        This method serializes the instance of the class into a JSON formatted string.
        It uses the `json.dumps` method to achieve this, with custom handling for objects
        to ensure they are converted to their dictionary representations.

        Returns:
            str: A JSON formatted string representing the instance of the class.
        """
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)
