from __future__ import annotations
from dataclasses import dataclass
from typing import Generator, Callable


# Nós da árvore (entrada)
@dataclass
class CommandNode:
    pass

@dataclass
class MoverCMD(CommandNode):
    n: int

@dataclass
class RecuarCMD(CommandNode):
    n: int

@dataclass
class EsquerdaCMD(CommandNode):
    pass

@dataclass
class DireitaCMD(CommandNode):
    pass

@dataclass
class EscanearCMD(CommandNode):
    pass

@dataclass
class SeObstaculoCMD(CommandNode):
    action: EsquerdaCMD | DireitaCMD

@dataclass
class RepetirCMD(CommandNode):
    n: int
    body: list[CommandNode]


# Saída 
@dataclass
class FlatAction:
    action: str
    value: int | None = None


# Engine
class ASTEngine:

    @staticmethod
    def execute(
        nodes: list[CommandNode],
        verificar_obstaculo: Callable[[], bool] | None = None,
    ) -> Generator[FlatAction, None, None]:
        """
        Gerador que achata a árvore de comandos.
        Resolve Repetir e SeObstaculo internamente,
        e faz yield apenas das ações executáveis.
        """
        for node in nodes:

            if isinstance(node, MoverCMD):
                yield FlatAction(action="MOVER", value=node.n)

            elif isinstance(node, RecuarCMD):
                yield FlatAction(action="RECUAR", value=node.n)

            elif isinstance(node, EsquerdaCMD):
                yield FlatAction(action="ESQUERDA")

            elif isinstance(node, DireitaCMD):
                yield FlatAction(action="DIREITA")

            elif isinstance(node, EscanearCMD):
                yield FlatAction(action="ESCANEAR")

            elif isinstance(node, SeObstaculoCMD):

                # Consulta o executor/simulação para saber se há obstáculo
                if verificar_obstaculo and verificar_obstaculo():
                    yield from ASTEngine.execute( [node.action], verificar_obstaculo )

            elif isinstance(node, RepetirCMD):

                for _ in range(node.n):
                    yield from ASTEngine.execute( node.body, verificar_obstaculo )

