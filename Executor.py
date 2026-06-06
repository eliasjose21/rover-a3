from __future__ import annotations
from typing import List
from AST import ASTEngine, FlatAction


class ExecutorException(Exception):
    def __init__(self, mensagem: str):
        super().__init__(f"Erro de execução: {mensagem}")


class Executor:
    """
    Recebe a AST (lista de CommandNode) e executa cada comando
    sobre o estado do rover (RoverState), um por um.

    Parâmetros
    ----------
    state : RoverState
        Estado atual do rover (posição, direção, grid, trilha).
        Vem do rover.py — não instanciar aqui pra evitar conflito.
    """

    def __init__(self, state):
        self.state = state
        self.logs: List[tuple[str, str]] = []

    # ──────────────────────────────────────────
    #  PONTO DE ENTRADA — executa tudo de uma vez
    # ──────────────────────────────────────────

    def executar(self, nodes: list) -> list[tuple[str, str]]:
        """
        Executa uma lista de CommandNode e retorna o log
        como lista de tuplas (mensagem, tag).
        """
        self.logs = []
        for acao in ASTEngine.execute(nodes, self.tem_obstaculo_a_frente):
            self.executar_acao(acao)
        return self.logs

    # ──────────────────────────────────────────
    #  PASSO A PASSO (modo STEP)
    # ──────────────────────────────────────────

    def preparar_passo_a_passo(self, nodes: list) -> list[FlatAction]:
        """Achata a AST em FlatActions para execução passo a passo."""
        return list(ASTEngine.execute(nodes, self.tem_obstaculo_a_frente))

    def executar_passo(self, acao: FlatAction) -> list[tuple[str, str]]:
        """Executa uma única FlatAction e retorna o log do passo."""
        self.logs = []
        self.executar_acao(acao)
        return self.logs

    # ──────────────────────────────────────────
    #  DISPATCH — decide qual ação executar
    # ──────────────────────────────────────────

    def executar_acao(self, acao: FlatAction):
        """Executa uma FlatAction vinda do ASTEngine."""
        match acao.action:
            case "MOVER":
                self._executar_movimento(passos=acao.value or 1, reverso=False)
            case "RECUAR":
                self._executar_movimento(passos=acao.value or 1, reverso=True)
            case "ESQUERDA" | "DIREITA":
                self._girar(acao.action)
            case "ESCANEAR":
                self._escanear()
            case _:
                raise ExecutorException(f"Ação desconhecida: '{acao.action}'")

    # ──────────────────────────────────────────
    #  LÓGICA DE CADA COMANDO
    # ──────────────────────────────────────────

    def _executar_movimento(self, passos: int, reverso: bool):
        """Lógica unificada para MOVER e RECUAR, com N passos."""
        s = self.state
        label = "RECUAR" if reverso else "MOVER"
        movidos = 0

        for i in range(passos):
            nx, ny = s.back_position() if reverso else s.front_position()

            if not s.grid.is_valid(nx, ny):
                self._log(f"  ⚠ {label} bloqueado: fora dos limites após {movidos} passo(s)", "warn")
                break

            if s.grid.has_obstacle(nx, ny):
                s.revealed.add((nx, ny))
                self._log(f"  🪨 {label} bloqueado: obstáculo em ({nx},{ny}) após {movidos} passo(s)", "warn")
                break

            s.trail.append((s.x, s.y))
            s.x, s.y = nx, ny
            s.revealed.add((s.x, s.y))
            movidos += 1

        self._log(f"  {label} {passos} → moveu {movidos} — pos: {s.pos_str()}", "step")

    def _girar(self, lado: str):
        if lado == "DIREITA":
            self.state._rover.direction = self.state._rover.direction.turn_right()
        else:
            self.state._rover.direction = self.state._rover.direction.turn_left()
        self._log(f"  {lado} → dir: {self.state.dir_str()}", "step")

    def _escanear(self):
        s = self.state
        RAIO = 4
        encontrados = []

        for dx in range(-RAIO, RAIO + 1):
            for dy in range(-RAIO, RAIO + 1):
                nx, ny = s.x + dx, s.y + dy
                if s.grid.is_valid(nx, ny):
                    s.revealed.add((nx, ny))
                    if s.grid.has_obstacle(nx, ny):
                        encontrados.append((nx, ny))

        if encontrados:
            coords = ", ".join(f"({x},{y})" for x, y in sorted(encontrados))
            self._log(f"  ESCANEAR → 🪨 {len(encontrados)} obstáculo(s): {coords}", "warn")
        else:
            self._log("  ESCANEAR → ✓ Nenhum obstáculo no raio de 4 células", "ok")

    # ──────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────

    def tem_obstaculo_a_frente(self) -> bool:
        """Callback para o ASTEngine — verifica obstáculo ou borda à frente."""
        fx, fy = self.state.front_position()
        return not self.state.grid.is_valid(fx, fy) or self.state.grid.has_obstacle(fx, fy)

    def _log(self, mensagem: str, tag: str = "info"):
        self.logs.append((mensagem, tag))
