# Plano

Painel gráfico ao vivo dos jogos do San Francisco 49ers para lives no YouTube: placar, campo, situação do drive,
última jogada e QBs, atualizados em tempo real e exibidos ao lado das câmeras.

## Arquitetura

```text
  Provider (Mock ou ESPN)
          │  ProviderUpdate: Game State + Game Events
          ▼
  ┌──────────────────────────────┐          ┌────────────────────┐
  │ FastAPI                      │  REST    │ /control           │
  │  GameService (Control Mode,  │◄────────►│ painel do operador │
  │  snapshot, undo)             │          └────────────────────┘
  │  WebSocket /ws/game          │
  └──────────────┬───────────────┘
                 │  GAME_STATE / GAME_EVENT
                 ▼
  Gamecast (/overlay) numa janela do navegador
                 │  compartilhamento de tela
                 ▼
  StreamYard: câmeras + Gamecast no layout ──► YouTube
```

- **Provider:** o resto do sistema não conhece a fonte de dados. Cada Provider traduz a sua fonte para o Game State
  (ver `GLOSSARY.md` e `docs/adr/0001`).
- **Control Mode:** AUTO (o Provider no comando) ou MANUAL (o operador no comando), nunca os dois ao mesmo tempo
  (`docs/adr/0002`). Se a API cair, a live continua em MANUAL.
- **StreamYard:** compõe a live. O Gamecast entra como compartilhamento de tela, sem OBS (`docs/adr/0003`).
- **ESPN:** o Provider de jogo real usa a API pública da ESPN (`docs/adr/0005`). O lado do campo é sempre do
  operador (`docs/adr/0006`).

## Princípios

- Primeiro o estado correto, depois a animação.
- Funciona com dados simulados antes de depender de uma API real.
- O frontend é uma tela única que recebe estado e renderiza: HTML, CSS e JavaScript puros, sem framework.
- Valores derivados (Line to Gain, Field Position Label, Passer Rating…) são calculados no backend, nunca informados.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn, Pydantic |
| Tempo real | WebSocket |
| Frontend | HTML, CSS Grid/Flexbox, JavaScript (módulos ES) |
| Testes e lint | pytest, Ruff |
| Dependências | uv |
| Transmissão | navegador → compartilhamento de tela → StreamYard → YouTube |

## Roadmap

| Versão | Capacidade | Status |
|---|---|---|
| 0.1 | Layout estático | ✅ |
| 0.2 | Campo dinâmico | ✅ |
| 0.3 | FastAPI + Game State | ✅ |
| 0.4 | MockProvider + snapshot | ✅ |
| 0.5 | WebSocket | ✅ |
| 0.6 | Painel de controle e Control Mode | ✅ |
| 0.7 | Estatísticas dos QBs (só em AUTO, `docs/adr/0004`) | ✅ |
| **0.8** | **Gamecast no StreamYard: layout para compartilhamento de tela e guia de operação. MVP utilizável.** | ✅ |
| **0.9** | **Provider da ESPN (`docs/adr/0005`)** | ✅ live real no DEN @ SF, 04/10 |
| 1.0 | Live real com a API | ✅ DEN @ SF, 04/10, toda em AUTO |
| **1.1** | **Animações dos Game Events** | ✅ |
| **1.2** | **Executável para Windows, para outra pessoa operar a live** | ✅ |
| **1.3** | **Atraso do Provider ajustável no painel** | ✅ WSH @ SF, 19/10 |

O MVP é a 0.8: com ela já é possível fazer uma live real com o placar em MANUAL.

### 0.8 em detalhe

- Gamecast só com o painel do jogo, em 16:9 e com fundo opaco: o compartilhamento de tela não tem transparência, e
  quem posiciona as câmeras (numa faixa ao lado) e o banner é o StreamYard.
- O canvas de 1920×1080 se ajusta à janela compartilhada, sem cortes.
- `docs/STREAMYARD.md` com a operação da live.
- Validada numa transmissão de teste no StreamYard.

### 0.9 em detalhe

- `EspnProvider`: placar, fase, relógio, situação ao vivo, última jogada, QBs e Game Events, a partir do scoreboard
  e do summary da ESPN, com proteção contra respostas atrasadas e gravação de tudo que chega.
- Validado com jogos encerrados da NFL e com jogos ao vivo de college football (mesmo formato).
- Primeira live real no DEN @ SF (04/10, 24 x 14), toda em AUTO. Com as 863 gravações do jogo:
  - placar e fase sem erro, sem voltar para trás; 21 respostas atrasadas da ESPN foram ignoradas;
  - corrigidos: time errado em timeouts, turnovers perdidos ou com o time errado (FG bloqueado, fumble no punt),
    flag sem time ("Penalty on" em minúsculas) e o lado do campo no 2º tempo (`docs/adr/0006`);
  - a ESPN mostra cada jogada, em mediana, 36s depois de ela acontecer (p90 56s).

### 1.1 em detalhe

- Estilo vibrante, nas cores do time protagonista:
  - touchdown toma o painel inteiro: faixas varrendo a tela, letras caindo uma a uma, onda de choque e "+6";
  - field goal, safety, extra point e 2 pontos entram com impacto sobre o campo, com brilho e borda pulsando;
  - turnover entra num chicote lateral e treme; flag é amarela e cai balançando; timeout é uma faixa rápida;
  - quando um time pontua, o placar dele salta e a caixa do time pisca.
- Os eventos entram numa fila e aparecem um de cada vez. Se a fila encher, saem primeiro os sem pontos.
- `/overlay?demo` repete todas as animações (ou `?demo=touchdown`, só uma), para conferir antes da live.

### 1.2 em detalhe

- `Gamecast.exe` (PyInstaller): sobe o servidor com ESPN em AUTO, escolhe uma porta livre a partir da 8000 e abre o
  painel no navegador. Dados numa pasta `dados` ao lado do `.exe`.
- O painel ganhou atalhos para abrir o Gamecast e a demo das animações.
- `scripts/build.ps1` gera `dist\Gamecast-<versão>.zip` com o `LEIA-ME.txt`, o guia de quem opera a live.
- As estatísticas avançadas, planejadas antes para a 1.2, foram descartadas: as atuais bastam.

### 1.3 em detalhe

- O operador ajusta no `/control` quantos segundos (0 a 120) cada atualização da ESPN espera antes de ir para o
  Gamecast, para não adiantar a transmissão. Vale na hora, mantém a ordem e não descarta nada: com menos atraso, o
  que já esperou sai na hora.
- Só segura o Provider: as ações do operador (MANUAL, inverter o campo, desfazer) continuam instantâneas, e o que
  está na fila não sobrescreve o MANUAL. A saúde do Provider no painel continua sem atraso.
- O painel mostra "Atraso ativo: Ns" e as jogadas na fila, ou "Sem atraso". O valor inicial vem de
  `GAMECAST_DELAY_SECONDS` e o do painel não sobrevive a um reinício.
- Usado na live do WSH @ SF (19/10, 23 x 17), com 8 a 10s.

## Fora do escopo, por enquanto

Banco de dados, Docker, deploy em servidor, autenticação, múltiplos jogos simultâneos, histórico da temporada,
fantasy, aplicativo mobile e estatísticas avançadas (além do placar, situação, última jogada e QBs).
