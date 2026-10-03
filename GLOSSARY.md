# 49ers Live Gamecast

Overlay gráfico de transmissão ao vivo que acompanha jogos do San Francisco 49ers em tempo real, sobreposto às câmeras de uma live no YouTube.

## Language

### Times

**Featured Team**:
O time em torno do qual o Gamecast é organizado: sempre o San Francisco 49ers. Ocupa a posição de destaque no layout, seja ele mandante ou visitante.
_Avoid_: home team, our team, SF (como conceito)

**Opponent**:
O time que enfrenta o Featured Team no jogo exibido.
_Avoid_: away team, adversário, visitor

### Jogo

**Game State**:
A fotografia completa e atual do jogo exibido: placar, fase, relógio, posse, down & distance, posição da bola e última jogada.
_Avoid_: game data, status

**Game Phase**:
O estágio duradouro em que o jogo se encontra; o jogo está sempre em exatamente uma fase (Pre-Game, Live, Halftime, Final).
_Avoid_: status, state

**Game Event**:
Um acontecimento pontual e efêmero (Touchdown, Field Goal, Turnover, Flag, Timeout) que é anunciado e não faz parte do Game State.
_Avoid_: state, phase

**Game Clock**:
O tempo restante no quarto atual.
_Avoid_: timer, cronômetro

### Campo

**Yardline**:
A posição da bola expressa como um número de 0 a 100, medido a partir da goal line defendida pelo Featured Team (0 = goal line do Featured Team, 50 = meio-campo, 100 = goal line do Opponent).
_Avoid_: yard_line + side, field position (como dado)

**Line to Gain**:
A Yardline que o time com a posse precisa alcançar para conquistar um novo first down.
_Avoid_: first down line, marker

**Goal to Go**:
Situação em que a Line to Gain coincide com a goal line adversária: não há first down possível, só touchdown.
_Avoid_: red zone (é outra coisa)

**Field Direction**:
Para qual lado da tela fica a goal line defendida pelo Featured Team no quarto atual; ela se inverte a cada troca de lado do jogo real.
_Avoid_: orientation, lado

**Field Position Label**:
A forma convencional de ler a Yardline, com o time dono daquela metade e a jarda (ex.: "DEN 34", "50").
_Avoid_: spot

### Operação

**Control Mode**:
Quem tem autoridade para alterar o Game State num dado momento: o Provider (Auto) ou o operador pelo painel (Manual). Nunca os dois ao mesmo tempo.
_Avoid_: override, source

**Provider**:
Uma fonte de dados de jogo (simulada ou real) que produz Game State.
_Avoid_: API, adapter, feed
