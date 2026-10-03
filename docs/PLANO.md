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
| **0.9** | **Provider da ESPN (`docs/adr/0005`)** | 🧪 teste no DEN @ SF, 04/10 |
| 1.0 | Live real com a API | |
| 1.1 | Animações dos Game Events | |
| 1.2 | Estatísticas avançadas | |

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
- Pendente: o primeiro jogo da NFL ao vivo (DEN @ SF, 04/10). Depois dele, revisar com as gravações: atraso em
  relação à TV, eventos perdidos ou errados e situações que a ESPN mande diferente do esperado.

## Fora do escopo, por enquanto

Banco de dados, Docker, deploy em servidor, autenticação, múltiplos jogos simultâneos, histórico da temporada,
fantasy e aplicativo mobile.
