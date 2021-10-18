import random
import string
import enum
from typing import Callable, Optional

# ------------------ Abstract Syntax Tree ---------------------


class Genexp:
    def __init__(self, sequence: list[Callable[[], str]]):
        self.sequence = sequence

    def generate(self) -> str:
        return "".join(genexp() for genexp in self.sequence)


class SingleChar(Genexp):
    def __init__(self, choices: str):
        gen = (lambda: choices) if len(choices) <= 1 else lambda: random.choice(choices)
        super().__init__(sequence=[gen])


class ConcatExp(Genexp):
    def __init__(self, genexps: list[Genexp]):
        super().__init__(sequence=[g.generate for g in genexps])


class ChooseExp(Genexp):
    def __init__(self, genexps: list[Genexp]):
        choice = lambda: random.choice(genexps).generate()
        super().__init__(sequence=[choice])


class RepeatExp(ConcatExp):
    def __init__(self, g: Genexp, n: int):
        super().__init__(genexps=[g] * n)


class OptionalExp(ChooseExp):
    def __init__(self, g: Genexp):
        super().__init__(genexps=[g, SingleChar("")])


# ------------------ TOKENS ---------------------


class TokenKind(enum.Enum):

    LITERAL = "x"

    ALPHANUM = "\\w"
    ALPHABETICAL = "\\a"
    LOWERCASE = "\\l"
    UPPERCASE = "\\u"
    DIGIT = "\\d"
    PUNCTUATION = "\\p"
    SPACE = "\\s"
    ANYPRINTABLE = "."

    GROUP_OPEN = "("
    GROUP_CLOSE = ")"

    QUANTIFIER_TIMES = "{0-9}"
    QUANTIFIER_MAYBE = "?"

    CHOICE_OPEN = "["
    CHOICE_CLOSE = "]"
    OR = "|"

    EOF = "EOF"

class MergeOpt(enum.Enum):
    CONCAT = "concat"
    CHOOSE = "choose"

class Token:
    def __init__(self, kind: TokenKind, value=""):
        self._kind = kind
        self._value = value

    @property
    def kind(self):
        return self._kind

    @property
    def value(self):
        return self._value

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Token)
            and type(self) == type(other)
            and self.value == other.value
        )


# ------------------ SCANNER ---------------------


class Scanner:
    def __init__(self, genex: str):
        self._genex_str: str = genex
        self._index: int = 0
        self._length: int = len(self._genex_str)

    def at_eof(self):
        return self._index == self._length

    def peek_char(self):
        if self.at_eof():
            raise IndexError(f"Invalid lookup: {self._genex_str} at {self._index}")
        return self._genex_str[self._index]

    def pop_char(self):
        c = self._genex_str[self._index]
        self._index += 1
        return c


# ------------------ LEXER ---------------------


class Lexer:
    def __init__(self, scanner: Scanner):
        self._scanner = scanner
        self._next: Optional[str] = None

    def peek_lexeme(self) -> str:
        if not self._next:
            self._next = self._get_next_lexeme()
        return self._next

    def pop_lexeme(self) -> str:
        lex = self.peek_lexeme()
        self._next = self._get_next_lexeme()
        return lex

    def _get_next_lexeme(self) -> str:
        if self._scanner.at_eof():
            return "EOF"

        lex = self._scanner.pop_char()

        match lex:
            case "\\":
                lex += self._scanner.pop_char()
                return lex

            case "{":
                next_c = None
                while next_c != "}":
                    if self._scanner.at_eof():
                        raise ValueError(f"EOF while looking for closing parens: {lex}")
                    next_c = self._scanner.pop_char()
                    lex += next_c
                return lex

            case "}":
                raise ValueError(f"Found unbalanced parens: {lex}")

            case _:
                return lex


# ------------------ TOKENIZER ---------------------


class Tokenizer:
    def __init__(self, lexer: Lexer):
        self._lexer = lexer
        self._next: Optional[Token] = None

    def peek_token(self) -> Token:
        if not self._next:
            self._next = self._get_next_token()
        return self._next

    def pop_token(self) -> Token:
        tok = self.peek_token()
        self._next = self._get_next_token()
        return tok

    def _get_next_token(self) -> Token:
        lex = self._lexer.pop_lexeme()

        match lex:
            case "EOF":
                return Token(kind=TokenKind.EOF)

            case "\\w":
                return Token(kind=TokenKind.ALPHANUM)
            case "\\a":
                return Token(kind=TokenKind.ALPHABETICAL)
            case "\\l":
                return Token(kind=TokenKind.LOWERCASE)
            case "\\u":
                return Token(kind=TokenKind.UPPERCASE)
            case "\\d":
                return Token(kind=TokenKind.DIGIT)
            case "\\p":
                return Token(kind=TokenKind.PUNCTUATION)
            case "\\s":
                return Token(kind=TokenKind.SPACE)
            case ".":
                return Token(kind=TokenKind.ANYPRINTABLE)

            case "(":
                return Token(kind=TokenKind.GROUP_OPEN)
            case ")":
                return Token(kind=TokenKind.GROUP_CLOSE)

            case "[":
                return Token(kind=TokenKind.CHOICE_OPEN)
            case "]":
                return Token(kind=TokenKind.CHOICE_CLOSE)
            case "|":
                return Token(kind=TokenKind.OR)

            case "?":
                return Token(kind=TokenKind.QUANTIFIER_MAYBE)

            case _:
                if lex.startswith("{") and lex.endswith("}"):
                    return Token(kind=TokenKind.QUANTIFIER_TIMES, value=lex)
                
                if lex.startswith("\\"):
                    lex = lex[1:]
                return Token(kind=TokenKind.LITERAL, value=lex)


# ------------------ PARSER ---------------------


class Parser:
    def __init__(self, tokenizer: Tokenizer):
        self._tokenizer = tokenizer
        self._next: Optional[Token] = None
        # self._genexseq: list[Genexp] = []

    def parse(self) -> Genexp:
        return self._parse(end_tokens = [TokenKind.EOF], merge = MergeOpt.CONCAT)

    def _parse(self, end_tokens : list[TokenKind], merge: MergeOpt) -> Genexp:
        
        genexpseq :list[Genexp]= []

        match merge:
            case MergeOpt.CONCAT:
                merge_func = lambda seq: ConcatExp(seq)
            case MergeOpt.CHOOSE:
                merge_func = lambda seq: ChooseExp(seq)
            case _:
                raise NotImplementedError

        tok: Token = self._tokenizer.pop_token()

        while True:

            if tok.kind in end_tokens:
                break

            match tok.kind:
                case TokenKind.EOF:
                    fail_string = ' or '.join(str(t) for t in end_tokens)
                    raise ValueError(f"Unexpected EOF: expected {fail_string}")

                case TokenKind.LITERAL:
                    genexpseq.append(SingleChar(tok.value))
                case TokenKind.ALPHANUM:
                    genexpseq.append(SingleChar(string.ascii_letters + string.digits))
                case TokenKind.ALPHABETICAL:
                    genexpseq.append(SingleChar(string.ascii_letters))
                case TokenKind.LOWERCASE:
                    genexpseq.append(SingleChar(string.ascii_lowercase))
                case TokenKind.UPPERCASE:
                    genexpseq.append(SingleChar(string.ascii_uppercase))
                case TokenKind.DIGIT:
                    genexpseq.append(SingleChar(string.digits))
                case TokenKind.PUNCTUATION:
                    genexpseq.append(SingleChar(string.punctuation))
                case TokenKind.SPACE:
                    genexpseq.append(SingleChar(string.whitespace))
                case TokenKind.ANYPRINTABLE:
                    genexpseq.append(SingleChar(string.printable))

                case TokenKind.QUANTIFIER_MAYBE:
                    assert len(genexpseq)>0, "Modifier applied to missing expression"
                    prev = genexpseq[-1]
                    genexpseq[-1] = OptionalExp(prev)

                case TokenKind.QUANTIFIER_TIMES:
                    assert len(genexpseq)>0, "Modifier applied to missing expression"
                    prev = genexpseq[-1]

                    try:
                        bounds = str(tok.value)[1:-1].split(",")

                        match len(bounds):
                            case 1:
                                n_times = int(bounds[0])
                                genexpseq[-1] = RepeatExp(prev, n_times)
                            case 2:
                                min_times, max_times = int(bounds[0]), int(bounds[1])
                                assert min_times <= max_times
                                genexpseq[-1] = ChooseExp(
                                    [RepeatExp(prev,n) for n in range(min_times, max_times+1)]
                                )
                            case _:
                                raise ValueError
                    except (IndexError, ValueError, AssertionError):
                        raise IndexError(f"Modifier is not formatted correctly: {tok.value}")

                case TokenKind.GROUP_OPEN:
                    sub_exp = self._parse(end_tokens=[TokenKind.GROUP_CLOSE], merge=MergeOpt.CONCAT)
                    genexpseq.append(sub_exp)
            
                case TokenKind.CHOICE_OPEN:
                    sub_exp = self._parse(end_tokens=[TokenKind.CHOICE_CLOSE], merge=MergeOpt.CHOOSE)
                    genexpseq.append(sub_exp)

                case TokenKind.GROUP_CLOSE | TokenKind.CHOICE_CLOSE:
                    raise ValueError(f"Unexpected token: {tok}")

                case TokenKind.OR:
                    next_exp = self._parse(end_tokens=end_tokens, merge=merge)
                    return ChooseExp([merge_func(genexpseq), next_exp]  )

                case _:
                    raise NotImplementedError

            tok = self._tokenizer.pop_token()

        return merge_func(genexpseq)

def parse(genex_str: str) -> Genexp:
    parser = Parser(Tokenizer(Lexer(Scanner(genex_str))))
    ast: Genexp = parser.parse()
    return ast


if __name__ == "__main__":

    test_cases = [
        "fixedstring",
        "\\d",
        "\\ltf?",
        "\\u",
        "\\d\\d\\l",
        "\\p.\\.",
        "a{4}",
        "\\l{1,4}",
        "a{4}?",
        "\\d?{4}",
        "(abc){3}",
        "[abc]",
        "[abc]{3}",
        "[\\p\\u\\d]{3}",
        "abc|def",
        "(abc|def)",
        "\\d?abc(123|def|[\\u\\d]{4}){1,2}xxx",
    ]

    print()
    for t in test_cases:
        for n in range(3):
            print(f"{t} --> ",end="")
            ast: Genexp = parse(t)
            res = ast.generate()
            print(res)


        print()
