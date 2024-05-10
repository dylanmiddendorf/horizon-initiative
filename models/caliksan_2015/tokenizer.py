# fmt: off
NORMAL_MODE              = 0b00000
CHARACTER_LITERAL_MODE   = 0b00001
STRING_LITERAL_MODE      = 0b00010
MULTI_LINE_COMMENT_MODE  = 0b00100
SINGLE_LINE_COMMENT_MODE = 0b01000
OPERATOR_MODE            = 0b10000

OPERATORS = ("{"  , "}" , "[" , "]" , "#" , "##"  , "("  , ")" ,
             "<:" , ":>", "<%", "%>", "%:", "%:%:", ";"  , ":" ,  "...",
                         "?" , "::", "." , ".*"  ,
             "+"  , "-" , "*" , "/" , "%" , "^"   , "&"  , "|"  , "~"  ,
             "!"  , "=" , "<" , ">" , "+=", "-="  , "*=" , "/=" , "%=" ,
             "^=" , "&=", "|=", "<<", ">>", ">>=" , "<<=", "==" , "!=" ,
             "<=" , ">=", "&&", "||", "++", "--"  , ","  , "->*", "->" ,
             "%:%", ".." # NOTE: These are used purely for greedy matching
            )
# fmt: on


class Tokenizer:
    """A naive C++ 17 complaint tokenizer, that assumes the provided source
    contains valid syntax."""

    def __init__(self) -> None:
        self.tokens = []  # Store the digested tokens
        self.buffer = ""  # Stores tokens between digests
        self.newline_escape = False  # True if newline escape is used in token
        self.mode = NORMAL_MODE

    def digest(self, buf: str) -> None:
        start = -1  # Denotes the starting index of a token
        prev = "" if not self.buffer else self.buffer[-1]

        for i, c in enumerate(buf):
            # Case 1: character literal
            if c == "'" and self.mode in (NORMAL_MODE, OPERATOR_MODE):
                if not prev.isspace():
                    self._process_token(start, i, buf)
                self.mode = CHARACTER_LITERAL_MODE
                start = i  # Start tracking the token
            elif c == "'" and self.mode == CHARACTER_LITERAL_MODE:
                if prev != "\\":  # Verify no escape sequence
                    self.mode = NORMAL_MODE
            elif self.mode == CHARACTER_LITERAL_MODE:
                pass  # Prevent subsequent elif statments from catching literals

            # Case 2: string literal
            elif c == '"' and self.mode in (NORMAL_MODE, OPERATOR_MODE):
                if not prev.isspace():
                    self._process_token(start, i, buf)
                self.mode, start = STRING_LITERAL_MODE, i
            elif c == '"' and self.mode == STRING_LITERAL_MODE:
                if prev != "\\":  # Verify no escape sequence
                    self.mode = NORMAL_MODE
            elif self.mode == STRING_LITERAL_MODE:
                pass

            # Case 3: multi-line comments
            elif prev == "/" and c == "*":
                self.mode = MULTI_LINE_COMMENT_MODE
            elif prev == "*" and c == "/" and self.mode == MULTI_LINE_COMMENT_MODE:
                self.mode = NORMAL_MODE
            elif self.mode == MULTI_LINE_COMMENT_MODE:
                pass  # Prevent subsequent elif statments from catching literals

            # Case 4: single-line comments (excludes literals & multi-line comments)
            elif c == "/" and prev == "/":
                self.mode = SINGLE_LINE_COMMENT_MODE
            elif c == "\n" and prev != "\\" and self.mode == SINGLE_LINE_COMMENT_MODE:
                self.mode = NORMAL_MODE
            elif self.mode == SINGLE_LINE_COMMENT_MODE:
                pass

            # Case 5: identifiers and keywords
            elif (c.isalnum() or c == "_") and self.mode == NORMAL_MODE:
                if prev.isspace():  # Start of new token identified
                    start = i
            elif (c.isalnum() or c == "_") and self.mode == OPERATOR_MODE:
                self._process_token(start, i, buf)
                self.mode, start = NORMAL_MODE, i

            # Case 6: operators and punctuators
            elif not c.isspace() and self.mode == NORMAL_MODE:
                if not prev.isspace():
                    self._process_token(start, i, buf)
                self.mode, start = OPERATOR_MODE, i
            elif not c.isspace() and self.mode == OPERATOR_MODE:
                if self._get_token(start, i + 1, buf) not in OPERATORS:
                    self._process_token(start, i, buf)
                    start = i  # Start new concatinated operator token

            # Case 6: whitespace
            elif c.isspace() and not (prev.isspace() or prev == "/"):
                self._process_token(start, i, buf)
                self.mode = NORMAL_MODE

            # Cycle the previous character
            prev = c

        # Enable cross-digest communication
        if start == -1:
            self.buffer += buf
        else:
            self.buffer = buf[start:]

    def _get_token(self, start: int, end: int, buf: str) -> str:
        token = self.buffer + buf[:end] if start == -1 else buf[start:end]
        if self.newline_escape:  # Remove all escaped newlines
            token = token.replace("\\\n", "")
        return token

    def _process_token(self, start: int, end: int, buf: str) -> None:
        token = self._get_token(start, end, buf)
        if token:  # Don't append empty tokens
            self.tokens.append(token)  # Append the extracted token to the list


class SourceFile:
    def __init__(self, pathname: str) -> None:
        tokenizer = Tokenizer()
        with open(pathname, "rt", encoding="utf-8") as fp:
            tokenizer.digest(fp.read())
