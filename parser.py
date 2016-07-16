"""The ShivyC parser. It's written entirely by hand because automatic parser
generators are no fun.

"""
import ast

from errors import CompilerError
import token_kinds

class Parser:
    """Provides the parser functionality to convert a list of tokens into an
    AST.

    Each internal function corresponds to a unique non-terminal symbol in the C
    grammar (I think). It parses the given tokens to try to match a grammar rule
    that generates the desired symbol. If a match is found, it returns the Node
    for that match. If a match is not found and the `error` parameter is True,
    it raises a compiler exception; if `error` is False, it simply returns None.

    """
    def parse(self, tokens):
        """Parse the provided list of tokens into an abstract syntax tree (AST)

        tokens (List[Token]) - A list of the tokens, as generated by the lexer
        returns (Node) - The root node of the generated AST"""

        return self.expect_main(tokens)

    def match_tokens(self, tokens, kinds_expected):
        """Checks if the provided tokens match the expected token kinds, in
        order. If any of the tokens do not have the expected kind, returns
        False.

        tokens (List[Token]) - A list of tokens
        expected (List[TokenKind, None]) - A list of token kinds to expect

        """
        if len(tokens) < len(kinds_expected): return False
        return all(kind == token.kind
                   for kind, token in zip(kinds_expected, tokens))

    def expect_main(self, tokens, error=True):
        """Ex: int main() { return 4; } """

        # The token kinds we expect to appear before the return value
        kinds_before = [token_kinds.int_kw, token_kinds.main,
                        token_kinds.open_paren, token_kinds.close_paren,
                        token_kinds.open_brack, token_kinds.return_kw]
        
        # The token kinds we expect to appear after the return value
        kinds_after = [token_kinds.semicolon, token_kinds.close_brack]
        
        kinds_match = (self.match_tokens(tokens, kinds_before) and
                       self.match_tokens(tokens[7:], kinds_after))

        if kinds_match:
            return ast.MainNode(tokens[6])
        else:
            if error:
                raise CompilerError("expected main function starting at '{}'".
                                    format(tokens[0].content))
            else: return None
