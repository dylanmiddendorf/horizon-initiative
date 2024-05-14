import sys
from features import LexicalFeatures

def main():
    lexer = LexicalFeatures(sys.argv[1])
    print(lexer.jsonify())

if __name__ == '__main__':
    main()