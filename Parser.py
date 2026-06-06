from Lexer import Lexer, Token, TokenType
from AST import (
    CommandNode,
    MoverCMD, RecuarCMD,
    EsquerdaCMD, DireitaCMD,
    EscanearCMD, SeObstaculoCMD,
    RepetirCMD,
)


class ParserException(Exception):
    def __init__(self, mensagem: str, linha: int):
        super().__init__(f"Erro de sintaxe na linha {linha}: {mensagem}")


class Parser:

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.token_atual = self.tokens[0]

    def _avancar(self) -> Token:
        consumido = self.token_atual
        self.pos += 1
        if self.pos < len(self.tokens):
            self.token_atual = self.tokens[self.pos]
        return consumido

    def _esperar(self, tipo: TokenType) -> Token:
        # se o token atual não é o que esperamos, algo tá errado no script
        if self.token_atual.tipo != tipo:
            raise ParserException(
                f"esperado '{tipo.name}', mas encontrado "
                f"'{self.token_atual.tipo.name}' ('{self.token_atual.valor}')",
                self.token_atual.linha,
            )
        return self._avancar()

    def parsear(self) -> list[CommandNode]:
        nos = self._parsear_bloco_comandos()
        self._esperar(TokenType.EOF)
        return nos

    def _parsear_bloco_comandos(self, dentro_de_bloco: bool = False) -> list[CommandNode]:
        nos: list[CommandNode] = []

        # todos os tokens que podem começar um comando
        INICIADORES = {
            TokenType.MOVER,
            TokenType.RECUAR,
            TokenType.ESQUERDA,
            TokenType.DIREITA,
            TokenType.ESCANEAR,
            TokenType.SE,
            TokenType.REPETIR,
        }

        while self.token_atual.tipo in INICIADORES:
            nos.append(self._parsear_comando())

        return nos

    def _parsear_comando(self) -> CommandNode:
        tipo = self.token_atual.tipo

        if tipo == TokenType.MOVER:
            return self._parsear_mover()
        if tipo == TokenType.RECUAR:
            return self._parsear_recuar()
        if tipo == TokenType.ESQUERDA:
            return self._parsear_esquerda()
        if tipo == TokenType.DIREITA:
            return self._parsear_direita()
        if tipo == TokenType.ESCANEAR:
            return self._parsear_escanear()
        if tipo == TokenType.SE:
            return self._parsear_se_obstaculo()
        if tipo == TokenType.REPETIR:
            return self._parsear_repetir()

        raise ParserException(
            f"token inesperado '{self.token_atual.valor}'",
            self.token_atual.linha,
        )

    def _parsear_mover(self) -> MoverCMD:
        self._esperar(TokenType.MOVER)
        tok_num = self._esperar(TokenType.NUMBER)  # MOVER precisa de número
        return MoverCMD(n=int(tok_num.valor))

    def _parsear_recuar(self) -> RecuarCMD:
        self._esperar(TokenType.RECUAR)
        tok_num = self._esperar(TokenType.NUMBER)  # RECUAR precisa de número
        return RecuarCMD(n=int(tok_num.valor))

    def _parsear_esquerda(self) -> EsquerdaCMD:
        self._esperar(TokenType.ESQUERDA)
        return EsquerdaCMD()

    def _parsear_direita(self) -> DireitaCMD:
        self._esperar(TokenType.DIREITA)
        return DireitaCMD()

    def _parsear_escanear(self) -> EscanearCMD:
        self._esperar(TokenType.ESCANEAR)
        return EscanearCMD()

    def _parsear_se_obstaculo(self) -> SeObstaculoCMD:
        self._esperar(TokenType.SE)
        self._esperar(TokenType.OBSTACULO)
        self._esperar(TokenType.ENTAO)

        # depois do ENTAO só faz sentido virar pra um lado
        if self.token_atual.tipo == TokenType.ESQUERDA:
            action = self._parsear_esquerda()
        elif self.token_atual.tipo == TokenType.DIREITA:
            action = self._parsear_direita()
        else:
            raise ParserException(
                f"após 'SE OBSTACULO ENTAO' esperado 'ESQUERDA' ou 'DIREITA', "
                f"mas encontrado '{self.token_atual.valor}'",
                self.token_atual.linha,
            )

        return SeObstaculoCMD(action=action)

    def _parsear_repetir(self) -> RepetirCMD:
        self._esperar(TokenType.REPETIR)
        tok_num = self._esperar(TokenType.NUMBER)  # quantas vezes repetir
        self._esperar(TokenType.LBRACE)

        corpo = self._parsear_bloco_comandos(dentro_de_bloco=True)

        # garante que o bloco foi fechado com }
        if self.token_atual.tipo != TokenType.RBRACE:
            raise ParserException(
                f"bloco REPETIR não fechado — esperado '}}', "
                f"mas encontrado '{self.token_atual.valor}'",
                self.token_atual.linha,
            )
        self._esperar(TokenType.RBRACE)

        return RepetirCMD(n=int(tok_num.valor), body=corpo)


# junta o Lexer e o Parser numa função só pra facilitar
def compilar(codigo: str) -> list[CommandNode]:
    lexer = Lexer(codigo)
    tokens = lexer.gerar_tokens()
    parser = Parser(tokens)
    return parser.parsear()


if __name__ == "__main__":
    from AST import ASTEngine

    casos = [
        (
            "Script válido completo",
            """
            MOVER 3
            ESCANEAR
            SE OBSTACULO ENTAO ESQUERDA
            REPETIR 2 {
                MOVER 1
                ESCANEAR
                SE OBSTACULO ENTAO DIREITA
                RECUAR 1
            }
            DIREITA
            """,
            True,
        ),
        (
            "REPETIR aninhado",
            """
            REPETIR 3 {
                REPETIR 2 {
                    MOVER 1
                }
                ESQUERDA
            }
            """,
            True,
        ),
        ("MOVER sem número",            "MOVER",                    False),
        ("RECUAR sem número",           "RECUAR",                   False),
        ("SE sem ação válida depois",   "SE OBSTACULO ENTAO MOVER", False),
        ("REPETIR sem número",          "REPETIR { MOVER 1 }",      False),
        ("REPETIR sem bloco fechado",   "REPETIR 3 { MOVER 1",      False),
        ("Token desconhecido no meio",  "MOVER 2\nESCANEAR\nFOO",   False),
    ]

    print("=" * 60)
    print("TESTES DO PARSER")
    print("=" * 60)

    aprovados = 0
    for descricao, codigo, deve_passar in casos:
        try:
            ast = compilar(codigo)

            if deve_passar:
                print(f"  [OK] {descricao}")
                print(f"       AST: {ast}")
                acoes = list(ASTEngine.execute(ast))
                print(f"       Ações: {acoes}")
                aprovados += 1
            else:
                print(f"  [FALHOU] {descricao}")
                print(f"           Esperava erro, mas o parse teve sucesso.")

        except Exception as e:
            if not deve_passar:
                print(f"  [OK] {descricao}")
                print(f"       Erro capturado corretamente → {e}")
                aprovados += 1
            else:
                print(f"  [FALHOU] {descricao}")
                print(f"           Erro inesperado → {e}")

        print()

    print("=" * 60)
    print(f"Resultado: {aprovados}/{len(casos)} testes passaram.")
    print("=" * 60)
