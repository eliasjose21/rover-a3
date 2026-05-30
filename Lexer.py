from enum import Enum, auto

# Aqui criei os tokens acredito estar tudo nos conformes
class TokenType(Enum):
    MOVER = auto()
    RECUAR = auto()
    ESQUERDA = auto()
    DIREITA = auto()
    ESCANEAR = auto()
    SE = auto()
    OBSTACULO = auto()
    ENTAO = auto()
    REPETIR = auto()
    NUMBER = auto()
    LBRACE = auto()
    RBRACE = auto()
    EOF = auto()


class Token:
    def __init__(self, tipo: TokenType, valor: str, linha: int): # aqui ele cria token
        self.tipo = tipo
        self.valor = valor
        self.linha = linha

    def __repr__(self):
        return f"Token({self.tipo.name}, '{self.valor}', linha {self.linha})"

class LexerException(Exception): # Lança o excepiton pra caso tenha erro
    def __init__(self, mensagem, linha):
        super().__init__(f"Erro na linha {linha}: {mensagem}")

class Lexer:
    def __init__(self, texto: str):
        self.texto = texto
        self.pos = 0
        self.linha = 1
        self.char_atual = self.texto[self.pos] if len(self.texto) > 0 else None
        
        self.palavras_reservadas = {
            'MOVER': TokenType.MOVER,
            'RECUAR': TokenType.RECUAR,
            'ESQUERDA': TokenType.ESQUERDA,
            'DIREITA': TokenType.DIREITA,
            'ESCANEAR': TokenType.ESCANEAR,
            'SE': TokenType.SE,
            'OBSTACULO': TokenType.OBSTACULO,
            'ENTAO': TokenType.ENTAO,
            'REPETIR': TokenType.REPETIR
        }

    def avancar(self):
        self.pos += 1
        if self.pos > len(self.texto) - 1:
            self.char_atual = None
        else:
            self.char_atual = self.texto[self.pos]

    def pular_espacos(self):
        while self.char_atual is not None and self.char_atual.isspace():
            if self.char_atual == '\n':
                self.linha += 1
            self.avancar()

    def pular_comentario(self): # acho esse comentário inutil, mas como tava no checklist ta aq
        while self.char_atual is not None and self.char_atual != '\n':
            self.avancar()

    def ler_numero(self):
        resultado = ''
        while self.char_atual is not None and self.char_atual.isdigit():
            resultado += self.char_atual
            self.avancar()
        return Token(TokenType.NUMBER, resultado, self.linha)

    def ler_identificador(self):
        resultado = ''
        while self.char_atual is not None and self.char_atual.isalpha():
            resultado += self.char_atual
            self.avancar()
        
        tipo = self.palavras_reservadas.get(resultado.upper())
        if tipo is None:
            raise LexerException(f"Palavra inválida '{resultado}'", self.linha)
        
        return Token(tipo, resultado.upper(), self.linha)

    def gerar_tokens(self):
        tokens = []
        while self.char_atual is not None:
            if self.char_atual.isspace():
                self.pular_espacos()
                continue
            
            if self.char_atual == '#':
                self.pular_comentario()
                continue
                
            if self.char_atual.isdigit():
                tokens.append(self.ler_numero())
                continue
                
            if self.char_atual.isalpha():
                tokens.append(self.ler_identificador())
                continue
                
            if self.char_atual == '{':
                tokens.append(Token(TokenType.LBRACE, '{', self.linha))
                self.avancar()
                continue
                
            if self.char_atual == '}':
                tokens.append(Token(TokenType.RBRACE, '}', self.linha))
                self.avancar()
                continue
                
            raise LexerException(f"Caractere inválido '{self.char_atual}'", self.linha) # achou caractere invalido ele lança exception
            
        tokens.append(Token(TokenType.EOF, 'EOF', self.linha))
        return tokens