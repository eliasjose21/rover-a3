"""
  SIMULADOR DO ROVER ESPACIAL — A3

"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import re
import time
import random
from enum import Enum
from PIL import Image, ImageTk

# Pipeline Lexer → Parser → AST → Executor
from Lexer import Lexer, LexerException
from Parser import Parser, ParserException, compilar
from AST import (
    ASTEngine, FlatAction,
    MoverCMD, RecuarCMD, EsquerdaCMD, DireitaCMD,
    EscanearCMD, SeObstaculoCMD, RepetirCMD,
)
from Executor import Executor

# 
#  CONFIGURAÇÕES DO AMBIENTE
#
GRID_SIZE = 20          
CELL_SIZE = 45
INITIAL_X, INITIAL_Y = 10, 10
INITIAL_DIR = "N"

DIRS      = ["N", "E", "S", "W"]
DIR_ARROW = {"N": "↑", "E": "→", "S": "↓", "W": "←"}
MOVE_DELTA = {
    "N": (0, -1),
    "S": (0,  1),
    "E": (1,  0),
    "W": (-1, 0),
}
# 
#  CAMINHOS DAS IMAGENS
#
import os as _os

def _find_image(filename):
    candidates = [
        _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), filename),
        _os.path.join(_os.getcwd(), filename),
        _os.path.join(_os.path.expanduser("~"), filename),
        _os.path.join(_os.path.expanduser("~"), "Downloads", filename),
        _os.path.join(_os.path.expanduser("~"), "Desktop", filename),
    ]
    for p in candidates:
        if _os.path.isfile(p):
            return p
    return None

IMG_SOIL  = _find_image("solo.jpeg")
IMG_ROCK  = _find_image("pedra.jpeg")
IMG_ROVER = _find_image("rover.jpeg")


#
#  ENUM DIRECTION  (N / S / L / O)
# 

class Direction(Enum):
    
    N = "N"   # Norte  → W interno
    S = "S"   # Sul    → S interno
    L = "E"   # Leste  → E interno  (L de Leste)
    O = "W"   # Oeste  → W interno  (O de Oeste)

    # ── Lógica de rotação 
    def turn_right(self) -> "Direction":
        """Gira 90° para a direita: N→L→S→O→N"""
        _right = {
            Direction.N: Direction.L,
            Direction.L: Direction.S,
            Direction.S: Direction.O,
            Direction.O: Direction.N,
        }
        return _right[self]

    def turn_left(self) -> "Direction":
        """Gira 90° para a esquerda: N→O→S→L→N"""
        _left = {
            Direction.N: Direction.O,
            Direction.O: Direction.S,
            Direction.S: Direction.L,
            Direction.L: Direction.N,
        }
        return _left[self]

    def arrow(self) -> str:
        """Símbolo visual da direção."""
        return {"N": "↑", "S": "↓", "E": "→", "W": "←"}[self.value]

    def label(self) -> str:
        """Nome legível: N, S, L ou O."""
        return self.name


# 
#  CLASSE GRID  
# 

class Grid:

    MIN_SIZE = 15

    def __init__(
        self,
        size: int = 15,
        n_obs: int = 10,
        init_pos: tuple = (7, 7),
        seed: int | None = None,
    ):
        self.size = max(size, self.MIN_SIZE)
        self.obstacles: set[tuple[int, int]] = set()
        self._generate_obstacles(n_obs, init_pos, seed)

    # ── Validação de posição 
    def is_valid(self, x: int, y: int) -> bool:
        """Retorna True se (x, y) está dentro dos limites da grade."""
        return 0 <= x < self.size and 0 <= y < self.size

    # ── Verificação de obstáculo 
    def has_obstacle(self, x: int, y: int) -> bool:
        """Retorna True se há um obstáculo na célula (x, y)."""
        return (x, y) in self.obstacles

    # ── Geração aleatória de obstáculos 
    def _generate_obstacles(
        self,
        n_obs: int,
        init_pos: tuple,
        seed: int | None,
    ) -> None:
        """
        Gera até n_obs obstáculos em posições válidas
        """
        rng = random.Random(seed)
        all_cells = [
            (x, y)
            for x in range(self.size)
            for y in range(self.size)
            if (x, y) != init_pos
        ]
        chosen = rng.sample(all_cells, min(n_obs, len(all_cells)))
        self.obstacles = set(chosen)


# 
#  CLASSE ROVER
# 

class Rover:
    """
    Representa o rover com posição, direção e histórico de posições.

    Parâmetros
    ----------
    x, y      : posição inicial
    direction : Direction inicial (padrão Norte)
    """

    def __init__(
        self,
        x: int = INITIAL_X,
        y: int = INITIAL_Y,
        direction: Direction = Direction.N,
    ):
        self.x = x
        self.y = y
        self.direction = direction
        self.history: list[tuple[int, int]] = []   # histórico de posições visitadas

    # ── Posição à frente 
    def front_position(self) -> tuple[int, int]:
        """
        Calcula a célula imediatamente à frente do rover
        de acordo com a direção atual, SEM mover o rover.

        Retorna
        -------
        (nx, ny) : coordenadas da célula à frente
        """
        dx, dy = MOVE_DELTA[self.direction.value]
        return self.x + dx, self.y + dy

    # ── Posição atrás 
    def back_position(self) -> tuple[int, int]:
        """
        Calcula a célula imediatamente atrás do rover
        (direção oposta), SEM mover o rover.

        Retorna
        -------
        (nx, ny) : coordenadas da célula atrás
        """
        opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}
        dx, dy = MOVE_DELTA[opposite[self.direction.value]]
        return self.x + dx, self.y + dy

    # ── Helpers de estado 
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    def pos_str(self) -> str:
        return f"({self.x}, {self.y})"

    def dir_str(self) -> str:
        return f"{self.direction.label()} {self.direction.arrow()}"

    def reset(self, x: int = INITIAL_X, y: int = INITIAL_Y) -> None:
        self.x = x
        self.y = y
        self.direction = Direction.N
        self.history = []

# 
#  CORES
# 
C = {
    "bg":         "#080d14",
    "panel":      "#0d1520",
    "panel2":     "#111d2e",
    "border":     "#1e3a5f",
    "border_hi":  "#2e5a8f",
    "accent":     "#c724f7",
    "accent_dim": "#6a1488",
    "green":      "#2dfa8a",
    "green_dim":  "#0d6635",
    "orange":     "#ff7043",
    "orange_dim": "#7a2a10",
    "text":       "#e8eef5",
    "muted":      "#8aa0ba",
    "error":      "#ff4466",
    "warn":       "#ffb020",
    "grid_bg":    "#0a1a2a",
    "grid_ln":    "#0d2540",
    "rover":      "#ffffff",
    "trail":      "#0d3322",
    "obs":        "#2a0d00",
    "btn_exec":   "#0a2a12",
    "btn_step":   "#1a0a2a",
    "btn_reset":  "#2a1400",
    "btn_clear":  "#0a1520",
}


# 
#  COMPILADOR (Lexer → Parser → AST)
#  Substituiu o tokenize/tokenize_lines anterior
# 

def compilar_com_erros(source: str):
    """
    Executa o pipeline Lexer → Parser e retorna (ast_nodes, errors).
    Compatível com a chamada tokenize() anterior:
      - ast_nodes: list[CommandNode]  (None se houve erro)
      - errors:    list[str]          (vazia se ok)

    Nota: o Lexer/Parser do projeto usa ESQUERDA/DIREITA como comandos
    independentes. O comando GIRAR foi removido — use ESQUERDA ou DIREITA
    diretamente.
    """
    try:
        ast_nodes = compilar(source)
        return ast_nodes, []
    except (LexerException, ParserException) as e:
        return None, [str(e)]
    except Exception as e:
        return None, [f"Erro inesperado: {e}"]


# 
#  INTERPRETADOR / EXECUTOR
# 

class RoverState:
    """
    Adaptador entre as novas classes Rover/Grid e o motor
    existente (Interpreter + RoverApp).

    Expõe os mesmos atributos .x .y .dir .trail usados pelo
    Interpreter, mas delega internamente ao Rover e ao Grid.
    """

    def __init__(self):
        # Grid com geração aleatória de obstáculos (criado UMA VEZ só)
        self.grid = Grid(size=GRID_SIZE, n_obs=20, init_pos=(INITIAL_X, INITIAL_Y))
        self._rover = Rover(INITIAL_X, INITIAL_Y, Direction.N)
        # 'trail' exposto como lista (compatibilidade com canvas)
        self.trail = self._rover.history
        # Células reveladas — começa revelando apenas a posição inicial do rover
        self.revealed: set[tuple[int, int]] = {(INITIAL_X, INITIAL_Y)}

    # ── Propriedades de compatibilidade 
    @property
    def x(self) -> int:
        return self._rover.x

    @x.setter
    def x(self, v: int):
        self._rover.x = v

    @property
    def y(self) -> int:
        return self._rover.y

    @y.setter
    def y(self, v: int):
        self._rover.y = v

    @property
    def dir(self) -> str:
        """Retorna a direção no formato interno N/E/S/W."""
        return self._rover.direction.value

    @dir.setter
    def dir(self, v: str):
        """Aceita N/E/S/W e converte para Direction."""
        self._rover.direction = Direction(v)

    # ── Delegação para métodos do Rover 
    def front_position(self) -> tuple[int, int]:
        return self._rover.front_position()

    def back_position(self) -> tuple[int, int]:
        return self._rover.back_position()

    # ── Reset 
    def reset(self):
        # O grid NÃO é recriado — obstáculos permanecem fixos durante toda a sessão
        # revealed é limpo — o SCAN precisa ser refeito após reset
        self._rover.reset(INITIAL_X, INITIAL_Y)
        self.trail = self._rover.history
        self.revealed = {(INITIAL_X, INITIAL_Y)}

    def pos_str(self):
        return self._rover.pos_str()

    def dir_str(self):
        return self._rover.dir_str()


class Interpreter:
    """
    Executa uma lista de CommandNode (AST) sobre o RoverState.
    Usa o ASTEngine para achatar a árvore em FlatActions,
    com um callback verificar_obstaculo para o SE OBSTACULO.
    """

    def __init__(self, state: RoverState):
        self.state = state

    def execute_nodes(self, nodes) -> list:
        """
        Executa uma lista de CommandNode e retorna lista de (msg, tag).
        Ponto de entrada principal chamado por run_all e step_once.
        """
        s = self.state
        logs = []

        def verificar_obstaculo() -> bool:
            fx, fy = s.front_position()
            out_of_bounds = not s.grid.is_valid(fx, fy)
            return out_of_bounds or s.grid.has_obstacle(fx, fy)

        for action in ASTEngine.execute(nodes, verificar_obstaculo):
            logs.extend(self._executar_flat(action))

        return logs

    def _executar_flat(self, action: FlatAction) -> list:
        """Executa uma FlatAction sobre o estado do rover."""
        s = self.state
        logs = []

        if action.action == "MOVER":
            n = action.value
            moved = 0
            for _ in range(n):
                nx, ny = s.front_position()
                if not s.grid.is_valid(nx, ny):
                    logs.append((f"  \u26a0 Limite do grid ap\u00f3s {moved} passo(s)", "warn"))
                    break
                if s.grid.has_obstacle(nx, ny):
                    s.revealed.add((nx, ny))
                    logs.append((f"  \U0001faa8 Obst\u00e1culo bloqueou ap\u00f3s {moved} passo(s) em ({nx},{ny})", "warn"))
                    break
                s.trail.append((s.x, s.y))
                s.x, s.y = nx, ny
                s.revealed.add((s.x, s.y))
                moved += 1
            logs.append((f"  MOVER {n} \u2192 moveu {moved} \u2014 pos: {s.pos_str()}", "step"))

        elif action.action == "RECUAR":
            n = action.value
            moved = 0
            for _ in range(n):
                nx, ny = s.back_position()
                if not s.grid.is_valid(nx, ny):
                    logs.append((f"  \u26a0 Limite do grid ap\u00f3s {moved} passo(s) de recuo", "warn"))
                    break
                if s.grid.has_obstacle(nx, ny):
                    s.revealed.add((nx, ny))
                    logs.append((f"  \U0001faa8 Obst\u00e1culo bloqueou recuo ap\u00f3s {moved} passo(s) em ({nx},{ny})", "warn"))
                    break
                s.trail.append((s.x, s.y))
                s.x, s.y = nx, ny
                s.revealed.add((s.x, s.y))
                moved += 1
            logs.append((f"  RECUAR {n} \u2192 recuou {moved} \u2014 pos: {s.pos_str()}", "step"))

        elif action.action == "ESQUERDA":
            s._rover.direction = s._rover.direction.turn_left()
            logs.append((f"  ESQUERDA \u2192 dir: {s.dir_str()}", "step"))

        elif action.action == "DIREITA":
            s._rover.direction = s._rover.direction.turn_right()
            logs.append((f"  DIREITA \u2192 dir: {s.dir_str()}", "step"))

        elif action.action == "ESCANEAR":
            SCAN_RADIUS = 4
            found = []
            for dx in range(-SCAN_RADIUS, SCAN_RADIUS + 1):
                for dy in range(-SCAN_RADIUS, SCAN_RADIUS + 1):
                    nx, ny = s.x + dx, s.y + dy
                    if s.grid.is_valid(nx, ny):
                        s.revealed.add((nx, ny))
                        if s.grid.has_obstacle(nx, ny):
                            found.append((nx, ny))
            if found:
                coords = ", ".join(f"({x},{y})" for x, y in sorted(found))
                logs.append((f"  ESCANEAR \u2192 \U0001faa8 {len(found)} obst\u00e1culo(s): {coords}", "warn"))
            else:
                logs.append(("  ESCANEAR \u2192 \u2713 Nenhum obst\u00e1culo no raio de 4 c\u00e9lulas", "ok"))

        return logs


# 
#  INTERFACE GRÁFICA  (tkinter)
# 

class RoverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🛰 Simulador do Rover Espacial — A3 Unicuritiba")
        self.configure(bg=C["bg"])
        self.resizable(True, True)

        self.rover = RoverState()
        self.interp = Executor(self.rover)
        self.compiled_tokens = []
        self.step_index = 0

        self._load_images()
        self._build_ui()
        self._draw_grid()
        self._update_status()

    # 
    #  CARREGAMENTO DAS IMAGENS
    # 
    def _load_images(self):
        """
        Pré-processa as três imagens para uso no canvas.
        Todas as referências ficam em self._img_* para evitar GC.
        Imprime no terminal se as imagens foram encontradas ou não.
        """
        cs = CELL_SIZE

        print("─── Carregando imagens ───")
        print(f"  Solo  : {IMG_SOIL}")
        print(f"  Rocha : {IMG_ROCK}")
        print(f"  Rover : {IMG_ROVER}")

        # ── Solo: uma imagem grande cobrindo todo o canvas ──────────
        canvas_px = GRID_SIZE * cs
        self._img_soil_full = None
        self._img_soil_tiles = []   # mantido por compatibilidade
        try:
            if IMG_SOIL is None:
                raise FileNotFoundError("Arquivo de solo não encontrado")
            soil_raw = Image.open(IMG_SOIL).convert("RGB")
            # Redimensiona para cobrir o canvas inteiro
            soil_full = soil_raw.resize((canvas_px, canvas_px), Image.LANCZOS)
            self._img_soil_full = ImageTk.PhotoImage(soil_full)
            print("  ✓ Solo carregado (imagem de fundo completa)")
        except Exception as e:
            print(f"  ✗ Solo: {e}")

        # ── Rocha: fundo branco → transparente, redimensionada ──
        self._img_rock = None
        try:
            if IMG_ROCK is None:
                raise FileNotFoundError("Arquivo de rocha não encontrado")
            rock_raw = Image.open(IMG_ROCK).convert("RGBA")
            # Remove fundo branco via operação de array numpy
            import numpy as np
            arr = np.array(rock_raw)
            white_mask = (arr[:,:,0] > 230) & (arr[:,:,1] > 230) & (arr[:,:,2] > 230)
            arr[white_mask, 3] = 0
            rock_raw = Image.fromarray(arr)
            self._img_rock = ImageTk.PhotoImage(
                rock_raw.resize((cs, cs), Image.LANCZOS))
            print("  ✓ Rocha carregada")
        except Exception as e:
            print(f"  ✗ Rocha: {e}")

        # ── Rover: fundo preto → transparente + 4 rotações ──
        self._img_rover = None
        try:
            if IMG_ROVER is None:
                raise FileNotFoundError("Arquivo de rover não encontrado")
            rover_raw = Image.open(IMG_ROVER).convert("RGBA")
            # Remove fundo preto via array numpy
            import numpy as np
            arr = np.array(rover_raw)
            black_mask = (arr[:,:,0] < 20) & (arr[:,:,1] < 20) & (arr[:,:,2] < 20)
            arr[black_mask, 3] = 0
            rover_raw = Image.fromarray(arr)
            rover_fit = rover_raw.resize((cs, cs), Image.LANCZOS)
            self._img_rover = {
                "N": ImageTk.PhotoImage(rover_fit),
                "E": ImageTk.PhotoImage(rover_fit.rotate(-90, expand=True)
                                         .resize((cs, cs), Image.LANCZOS)),
                "S": ImageTk.PhotoImage(rover_fit.rotate(180, expand=True)
                                         .resize((cs, cs), Image.LANCZOS)),
                "W": ImageTk.PhotoImage(rover_fit.rotate(90, expand=True)
                                         .resize((cs, cs), Image.LANCZOS)),
            }
            print("  ✓ Rover carregado")
        except Exception as e:
            print(f"  ✗ Rover: {e}")
        print("─────────────────────────")


    # 
    #  CONSTRUÇÃO DA UI
    # 
    def _build_ui(self):
        # ── Cabeçalho 
        hdr = tk.Frame(self, bg=C["panel2"], pady=12)
        hdr.pack(fill="x")
        # borda superior colorida
        top_border = tk.Frame(self, bg=C["accent"], height=3)
        top_border.place(x=0, y=0, relwidth=1)

        tk.Label(hdr, text="\U0001f6f0  ROVER ESPACIAL \u2014 SIMULADOR",
                 bg=C["panel2"], fg=C["accent"],
                 font=("Courier", 18, "bold")).pack()
        tk.Label(hdr, text="TEORIA DA COMPUTA\u00c7\u00c3O E COMPILADORES  \u00b7  A3  \u00b7  UNICURITIBA",
                 bg=C["panel2"], fg=C["muted"],
                 font=("Courier", 9)).pack(pady=(2, 0))

        sep = tk.Frame(self, bg=C["border"], height=2)
        sep.pack(fill="x")

        # ── Corpo principal 
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=0, pady=0)

        # Grid (esquerda)
        left = tk.Frame(body, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        canvas_size = GRID_SIZE * CELL_SIZE
        # moldura ao redor do canvas
        canvas_border = tk.Frame(left, bg=C["accent"], padx=2, pady=2)
        canvas_border.pack()
        self.canvas = tk.Canvas(canvas_border,
            width=canvas_size, height=canvas_size,
            bg=C["grid_bg"], highlightthickness=0)
        self.canvas.pack()

        # Barra de status
        status_frame = tk.Frame(left, bg=C["panel2"], pady=6, padx=10,
                                highlightbackground=C["border"], highlightthickness=1)
        status_frame.pack(fill="x", pady=(8,0))

        self.lbl_pos = self._status_label(status_frame, "POS")
        self.lbl_dir = self._status_label(status_frame, "DIR")
        self.lbl_step = self._status_label(status_frame, "PASSO")
        self.lbl_status = self._status_label(status_frame, "STATUS")

        # Painel direito
        right = tk.Frame(body, bg=C["panel"], width=355,
                         highlightbackground=C["border"], highlightthickness=1)
        right.pack(side="right", fill="y", padx=0, pady=0)
        right.pack_propagate(False)

        self._build_right_panel(right)

    def _status_label(self, parent, title):
        f = tk.Frame(parent, bg=C["panel2"],
                     highlightbackground=C["border"], highlightthickness=1,
                     padx=8, pady=4)
        f.pack(side="left", padx=6)
        tk.Label(f, text=title, bg=C["panel2"], fg=C["muted"],
                 font=("Courier", 7, "bold")).pack()
        val = tk.Label(f, text="\u2014", bg=C["panel2"], fg=C["accent"],
                       font=("Courier", 11, "bold"))
        val.pack()
        return val

    def _build_right_panel(self, parent):
        # ── Editor 
        self._section_title(parent, "EDITOR DE COMANDOS")

        editor_box = tk.Frame(parent, bg=C["border"], padx=1, pady=1)
        editor_box.pack(padx=10, pady=(0, 6), fill="x")
        self.editor = scrolledtext.ScrolledText(editor_box,
            width=36, height=12,
            bg="#06111e", fg=C["green"],
            insertbackground=C["accent"],
            font=("Courier", 10),
            relief="flat", bd=0,
            highlightthickness=0,
            selectbackground=C["accent_dim"],
            selectforeground=C["text"])
        self.editor.pack()
        self.editor.insert("end", "# Digite os comandos aqui\nMOVER 3\nDIREITA\nMOVER 2\nESCANEAR\n")

        # ── Botões em caixas individuais
        self._section_title(parent, "CONTROLES")

        btn_outer = tk.Frame(parent, bg=C["panel"])
        btn_outer.pack(padx=10, pady=(0, 6), fill="x")

        # linha 1
        row1 = tk.Frame(btn_outer, bg=C["panel"])
        row1.pack(fill="x", pady=(0, 4))

        exec_box = tk.Frame(row1, bg=C["green_dim"], padx=2, pady=2)
        exec_box.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._btn(exec_box, "\u25b6  EXECUTAR", self.run_all, C["green"], C["btn_exec"]).pack(fill="x")

        step_box = tk.Frame(row1, bg=C["accent_dim"], padx=2, pady=2)
        step_box.pack(side="left", expand=True, fill="x")
        self._btn(step_box, "\u23ed  STEP", self.step_once, C["accent"], C["btn_step"]).pack(fill="x")

        # linha 2
        row2 = tk.Frame(btn_outer, bg=C["panel"])
        row2.pack(fill="x")

        reset_box = tk.Frame(row2, bg=C["orange_dim"], padx=2, pady=2)
        reset_box.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._btn(reset_box, "\u21ba  RESET", self.reset_rover, C["orange"], C["btn_reset"]).pack(fill="x")

        clear_box = tk.Frame(row2, bg=C["border"], padx=2, pady=2)
        clear_box.pack(side="left", expand=True, fill="x")
        self._btn(clear_box, "\u2715  LIMPAR LOG", self.clear_console, C["muted"], C["btn_clear"]).pack(fill="x")

        # ── Console 
        self._section_title(parent, "CONSOLE DE SA\u00cdDA")

        console_box = tk.Frame(parent, bg=C["border"], padx=1, pady=1)
        console_box.pack(padx=10, pady=(0, 6), fill="x")
        self.console = scrolledtext.ScrolledText(console_box,
            width=36, height=8,
            bg="#06111e", fg=C["text"],
            font=("Courier", 9),
            state="disabled",
            relief="flat", bd=0,
            highlightthickness=0,
            selectbackground=C["accent_dim"])
        self.console.pack()

        # Tags de cor no console
        self.console.tag_config("ok",   foreground=C["green"])
        self.console.tag_config("warn", foreground=C["warn"])
        self.console.tag_config("error",foreground=C["error"])
        self.console.tag_config("cmd",  foreground=C["accent"])
        self.console.tag_config("step", foreground="#7ec8e3")
        self.console.tag_config("info", foreground=C["text"])
        self.console.tag_config("sep",  foreground=C["border"])

        # ── Referência 
        self._section_title(parent, "REFER\u00caNCIA R\u00c1PIDA")

        ref_box = tk.Frame(parent, bg=C["border"], padx=1, pady=1)
        ref_box.pack(padx=10, fill="x")
        ref = tk.Frame(ref_box, bg=C["panel2"], padx=6, pady=6)
        ref.pack(fill="x")

        cmds = [
            ("MOVER n",                    "Avança n posições"),
            ("RECUAR n",                   "Recua n posições"),
            ("ESQUERDA",                   "Gira 90° à esquerda"),
            ("DIREITA",                    "Gira 90° à direita"),
            ("ESCANEAR",                   "Detecta obstáculos"),
            ("SE OBSTACULO ENTAO ...",     "⭐ Condicional"),
            ("REPETIR n { ... }",          "⭐ Repetição"),
        ]
        for i, (cmd, desc) in enumerate(cmds):
            row_bg = C["panel2"] if i % 2 == 0 else C["panel"]
            row_f = tk.Frame(ref, bg=row_bg)
            row_f.pack(fill="x")
            tk.Label(row_f, text=f" {cmd}", bg=row_bg, fg=C["green"],
                     font=("Courier", 8), anchor="w", width=20).pack(side="left")
            tk.Label(row_f, text=desc, bg=row_bg, fg=C["muted"],
                     font=("Courier", 8), anchor="w").pack(side="left")

        # ── Exemplos 
        self._section_title(parent, "EXEMPLOS R\u00c1PIDOS")

        ex_outer = tk.Frame(parent, bg=C["panel"])
        ex_outer.pack(padx=10, fill="x", pady=(0, 12))

        examples = [
            ("Navega\u00e7\u00e3o b\u00e1sica",   "basic"),
            ("Detectar obst\u00e1culos", "scan"),
            ("REPEAT (b\u00f4nus)",      "repeat"),
            ("IF OBSTACLE (b\u00f4nus)", "if_obs"),
            ("Erros de sintaxe",         "errors"),
        ]
        for name, key in examples:
            ex_box = tk.Frame(ex_outer, bg=C["border"], padx=1, pady=1)
            ex_box.pack(fill="x", pady=2)
            btn = tk.Button(ex_box, text=f"  \u25b8  {name}",
                bg=C["panel2"], fg=C["muted"],
                activebackground=C["panel"], activeforeground=C["accent"],
                font=("Courier", 8), relief="flat", bd=0,
                anchor="w", cursor="hand2", pady=4,
                command=lambda k=key: self.load_example(k))
            btn.pack(fill="x")
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=C["panel"], fg=C["accent"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=C["panel2"], fg=C["muted"]))

        self._log("Sistema inicializado. Rover em (7,7) \u2192 N", "info")
        self._log("\u2500" * 38, "sep")

    def _section_title(self, parent, text):
        f = tk.Frame(parent, bg=C["panel"], pady=0)
        f.pack(fill="x", padx=10, pady=(10, 4))
        inner = tk.Frame(f, bg=C["border"], pady=1)
        inner.pack(fill="x")
        title_row = tk.Frame(inner, bg=C["panel2"])
        title_row.pack(fill="x")
        tk.Label(title_row, text=f"  \u25c8  {text}  ",
                 bg=C["panel2"], fg=C["accent"],
                 font=("Courier", 8, "bold"),
                 pady=4).pack(side="left")

    def _btn(self, parent, text, cmd, color, bg_color=None):
        bg = bg_color if bg_color else C["panel2"]
        btn = tk.Button(parent, text=text, command=cmd,
            bg=bg, fg=color,
            activebackground=color, activeforeground=C["bg"],
            font=("Courier", 9, "bold"), relief="flat", bd=0,
            highlightbackground=color, highlightthickness=2,
            padx=14, pady=7, cursor="hand2")
        btn.bind("<Enter>", lambda e: btn.config(bg=color, fg=C["bg"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg, fg=color))
        return btn

    # 
    #  DESENHO DO GRID
    # 
    def _draw_grid(self):
        self.canvas.delete("all")
        s = self.rover
        trail_set = set(s.trail)
        cs = CELL_SIZE
        gs = s.grid.size
        total = gs * cs

        # ─────────────────────────────────────────
        # CAMADA 1: imagem do solo cobrindo TODO o canvas de uma vez
        # ─────────────────────────────────────────
        if self._img_soil_full:
            self.canvas.create_image(0, 0, anchor="nw", image=self._img_soil_full)
        else:
            self.canvas.create_rectangle(0, 0, total, total,
                fill=C["grid_bg"])

        # ─────────────────────────────────────────
        # CAMADA 2: conteúdo das células
        # (obstáculos, rover, trilha, fog of war)
        # ─────────────────────────────────────────
        for row in range(gs):
            for col in range(gs):
                x1 = col * cs
                y1 = row * cs
                x2 = x1 + cs
                y2 = y1 + cs
                cx = x1 + cs // 2
                cy = y1 + cs // 2
                pos = (col, row)
                revealed = pos in s.revealed
                is_rover = pos == (s.x, s.y)
                is_trail = pos in trail_set

                if is_rover:
                    # Rover sempre visível — marca como revelado também
                    s.revealed.add(pos)
                    if self._img_rover:
                        self.canvas.create_image(x1, y1, anchor="nw",
                                                  image=self._img_rover[s.dir])
                    else:
                        arrow = {"N": "▲", "S": "▼", "E": "▶", "W": "◀"}[s.dir]
                        self.canvas.create_oval(x1+4, y1+4, x2-4, y2-4,
                            fill=C["accent"], outline="white", width=2)
                        self.canvas.create_text(cx, cy, text=arrow,
                            fill="black", font=("Courier", 14, "bold"))

                elif s.grid.has_obstacle(col, row) and revealed:
                    # Obstáculo visível só se foi revelado pelo SCAN
                    if self._img_rock:
                        self.canvas.create_image(x1, y1, anchor="nw",
                                                  image=self._img_rock)
                    else:
                        self.canvas.create_rectangle(x1, y1, x2, y2,
                            fill=C["obs"])
                        self.canvas.create_text(cx, cy, text="🪨", font=("", 14))

                elif is_trail and not s.grid.has_obstacle(col, row):
                    # Trilha visitada — sempre visível
                    self.canvas.create_rectangle(x1, y1, x2, y2,
                        fill=C["trail"], outline="", stipple="gray50")
                    self.canvas.create_text(cx, cy, text="·",
                        fill="#2aff80", font=("Courier", 14))

                elif not revealed and not is_trail:
                    # Fog of war — célula nunca vista
                    self.canvas.create_rectangle(x1, y1, x2, y2,
                        fill="#050d14", outline="", stipple="gray75")

        # ─────────────────────────────────────────
        # CAMADA 3: grade translúcida por cima de tudo
        # ─────────────────────────────────────────
        grid_color = "#1a3a4a"   # azul-escuro translúcido
        for r in range(gs + 1):
            self.canvas.create_line(0, r * cs, total, r * cs,
                fill=grid_color, width=1)
        for c in range(gs + 1):
            self.canvas.create_line(c * cs, 0, c * cs, total,
                fill=grid_color, width=1)


    # 
    #  AÇÕES DOS BOTÕES
    # 
    def run_all(self):
        self.clear_console()
        src = self.editor.get("1.0", "end")
        ast_nodes, errors = compilar_com_erros(src)

        if errors:
            self._log("═══ ERROS DE SINTAXE ═══", "error")
            for e in errors:
                self._log(e, "error")
            self._log("─── Corrija os erros e tente novamente ───", "warn")
            self._set_status_color(C["error"])
            self.lbl_status.config(text="ERRO")
            return

        self._log(f"═══ COMPILAÇÃO OK — {len(ast_nodes)} instrução(ões) ═══", "ok")
        self._log("Iniciando execução...", "info")
        self.rover.reset()

        logs = self.interp.executar(ast_nodes)
        for msg, tag in logs:
            self._log(msg, tag)

        self._draw_grid()
        self._update_status()
        self._set_status_color(C["green"])
        self.lbl_status.config(text="CONCLUÍDO")
        self._log("─" * 38, "sep")
        self._log(f"✓ Execução concluída. Pos: {self.rover.pos_str()} dir: {self.rover.dir_str()}", "ok")

    def step_once(self):
        if self.step_index == 0:
            src = self.editor.get("1.0", "end")
            ast_nodes, errors = compilar_com_erros(src)
            if errors:
                self._log("═══ ERROS DE SINTAXE ═══", "error")
                for e in errors:
                    self._log(e, "error")
                return

            # Achata toda a AST em FlatActions para passo a passo
            s = self.rover
            def verificar_obstaculo() -> bool:
                fx, fy = s.front_position()
                return not s.grid.is_valid(fx, fy) or s.grid.has_obstacle(fx, fy)

            self.compiled_tokens = self.interp.preparar_passo_a_passo(ast_nodes)
            self.rover.reset()
            self._draw_grid()
            self._log(f"═══ MODO PASSO A PASSO — {len(self.compiled_tokens)} ação(ões) ═══", "ok")

        if self.step_index >= len(self.compiled_tokens):
            self._log("✓ Todos os passos executados.", "ok")
            self.step_index = 0
            return

        action = self.compiled_tokens[self.step_index]
        total = len(self.compiled_tokens)
        self._log(f"[Passo {self.step_index+1}/{total}]", "cmd")
        logs = self.interp.executar_passo(action)
        for msg, tag in logs:
            self._log(msg, tag)
        self.step_index += 1
        self._draw_grid()
        self._update_status()
        self.lbl_step.config(text=f"{self.step_index}/{total}")
        if self.step_index >= len(self.compiled_tokens):
            self.lbl_status.config(text="CONCLUÍDO")
            self._set_status_color(C["green"])

    def reset_rover(self):
        self.rover.reset()
        self.step_index = 0
        self._draw_grid()
        self._update_status()
        self._set_status_color(C["accent"])
        self.clear_console()
        self._log("Sistema reiniciado. Rover em (7,7) → N  [novo mapa gerado]", "info")

    def clear_console(self):
        self.console.config(state="normal")
        self.console.delete("1.0", "end")
        self.console.config(state="disabled")

    # 
    #  STATUS BAR
    # 
    def _update_status(self):
        s = self.rover
        self.lbl_pos.config(text=s.pos_str())
        self.lbl_dir.config(text=s.dir_str())
        self.lbl_status.config(text="PRONTO")
        self.lbl_step.config(text="—")
        self._set_status_color(C["accent"])

    def _set_status_color(self, color):
        self.lbl_status.config(fg=color)

    # 
    #  CONSOLE
    # 
    def _log(self, msg, tag="info"):
        self.console.config(state="normal")
        self.console.insert("end", msg + "\n", tag)
        self.console.see("end")
        self.console.config(state="disabled")

    # 
    #  EXEMPLOS
    # 
    def load_example(self, name):
        examples = {
            "basic": (
                "# Exemplo 1 — Navegação básica\n"
                "MOVER 3\n"
                "DIREITA\n"
                "MOVER 2\n"
                "ESQUERDA\n"
                "MOVER 1\n"
                "ESCANEAR\n"
            ),
            "scan": (
                "# Exemplo 2 — Detectar obstáculos\n"
                "ESCANEAR\n"
                "MOVER 2\n"
                "DIREITA\n"
                "ESCANEAR\n"
                "MOVER 3\n"
                "ESCANEAR\n"
                "ESQUERDA\n"
                "RECUAR 1\n"
            ),
            "repeat": (
                "# Exemplo 3 — REPETIR\n"
                "MOVER 1\n"
                "REPETIR 3 {\n"
                "  DIREITA\n"
                "  MOVER 1\n"
                "}\n"
                "ESCANEAR\n"
            ),
            "if_obs": (
                "# Exemplo 4 — SE OBSTACULO ENTAO\n"
                "MOVER 2\n"
                "ESCANEAR\n"
                "SE OBSTACULO ENTAO DIREITA\n"
                "MOVER 2\n"
                "ESQUERDA\n"
                "ESCANEAR\n"
                "SE OBSTACULO ENTAO ESQUERDA\n"
            ),
            "errors": (
                "# Exemplo 5 — Erros de sintaxe\n"
                "MOVER\n"
                "MOVERR 3\n"
                "GIRAR NORTE\n"
                "ANDAR 2\n"
                "RECUAR abc\n"
                "ESCANEAR 5\n"
            ),
        }
        self.editor.delete("1.0", "end")
        self.editor.insert("end", examples.get(name, ""))
        self.clear_console()
        self._log(f'Exemplo "{name}" carregado. Clique em EXECUTAR.', "info")


# 
#  PONTO DE ENTRADA
# 
if __name__ == "__main__":
    app = RoverApp()
    app.mainloop()
