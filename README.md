# 🛰 Simulador do Rover Espacial
**Teoria da Computação e Compiladores — A3 · Unicuritiba**

Sistema de navegação com linguagem de comandos própria, compilador e simulador visual.

---

## 🚀 Como rodar

**Instalar dependências:**
```bash
pip install pillow numpy
```

**Executar:**
```bash
python rover.py
```

---

## 📁 Estrutura do projeto

```
rover/
├── rover.py1.1.py   # Interface gráfica + ponto de entrada
├── Lexer.py         # Análise léxica — transforma texto em tokens
├── Parser.py        # Análise sintática — valida e monta a AST
├── AST.py           # Nós da árvore sintática abstrata
├── Executor.py      # Executa os comandos sobre o estado do rover
├── solo.jpeg        # Imagem do chão do grid
├── pedra.jpeg       # Imagem dos obstáculos
└── rover.jpeg       # Imagem do rover
```

---

## 🧠 Arquitetura

O sistema funciona como um compilador real, em 4 fases:

```
script .rover
     ↓
  Lexer        → reconhece os símbolos (tokens)
     ↓
  Parser       → valida a estrutura e monta a AST
     ↓
  Executor     → executa os comandos
     ↓
  Simulador    → atualiza e exibe o estado do rover
```

---

## 📋 Comandos da linguagem

| Comando | O que faz | Exemplo |
|---|---|---|
| `MOVER n` | Avança n posições pra frente | `MOVER 3` |
| `RECUAR n` | Recua n posições pra trás | `RECUAR 2` |
| `ESQUERDA` | Gira 90° pra esquerda | `ESQUERDA` |
| `DIREITA` | Gira 90° pra direita | `DIREITA` |
| `ESCANEAR` | Revela obstáculos num raio de 4 células | `ESCANEAR` |
| `SE OBSTACULO ENTAO ESQUERDA\|DIREITA` | Vira se houver obstáculo à frente | `SE OBSTACULO ENTAO DIREITA` |
| `REPETIR n { }` | Repete o bloco n vezes | `REPETIR 3 { MOVER 1 }` |
| `# comentário` | Linha ignorada pelo sistema | `# indo pra frente` |

---

## 📝 Exemplo de script

```
# Missão de exploração
MOVER 3
DIREITA
ESCANEAR
SE OBSTACULO ENTAO ESQUERDA
REPETIR 2 {
    MOVER 1
    ESQUERDA
}
RECUAR 1
ESCANEAR
```

---

## 🖥 Interface

A tela é dividida em duas áreas:

**Esquerda — Grid 20x20**
| Elemento | Significado |
|---|---|
| Imagem do rover | Posição atual, aponta pra direção |
| Vermelho (pedra) | Obstáculo revelado pelo ESCANEAR |
| Verde escuro com `·` | Rastro do caminho percorrido |
| Célula bem escura | Fog of war — área não explorada |

**Direita — Painel de controle**
- **Editor de comandos** — onde o script é digitado
- **EXECUTAR** — roda todos os comandos de uma vez
- **STEP** — executa um comando por vez
- **RESET** — volta o rover à posição inicial `(7,7)` apontando pra Norte
- **LIMPAR LOG** — limpa o console de saída
- **Referência rápida** — lista de todos os comandos
- **Exemplos rápidos** — scripts prontos pra carregar com um clique

---

## ❌ Erros tratados

| Erro | Causa | Solução |
|---|---|---|
| `Erro léxico: Palavra inválida` | Comando com erro de digitação | Verificar se está em maiúsculo |
| `Erro de sintaxe` | Estrutura incorreta | Ex: `MOVER` sem número |
| `MOVER bloqueado` | Obstáculo ou borda à frente | Usar `ESCANEAR` antes de mover |
| `REPETIR não fechado` | Faltou o `}` | Fechar o bloco |

---

