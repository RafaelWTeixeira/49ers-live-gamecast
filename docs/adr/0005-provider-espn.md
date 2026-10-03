# Provider real: API pública e não oficial da ESPN

O Provider de jogo real usa a API pública da ESPN (`site.api.espn.com`). Ela é gratuita, não pede chave e traz tudo o que o Game State usa: placar, relógio, situação ao vivo, última jogada, estatísticas de passe e jogadas com tipo. Foi validada contra jogos reais antes da adoção. As APIs comerciais testadas ou não trazem down & distance e posição da bola nos planos baratos, ou não liberam a NFL no teste grátis (SportsDataIO), ou exigem contrato empresarial (Sportradar). O risco de uma API não oficial, que pode mudar ou sair do ar sem aviso, é coberto pelo Control Mode Manual (`docs/adr/0002`).

O que os dados reais ensinaram e o Provider trata:

- O `yardLine` da ESPN é medido a partir da goal line do time da casa.
- O scoreboard chega antes do summary; o atraso do summary passou de um minuto num jogo. Por isso os Game Events saem da última jogada do scoreboard. Do summary vêm só os QBs e as pontuações que o scoreboard não anunciou.
- A ESPN às vezes devolve uma resposta mais antiga do que a anterior. O Provider guarda a mais nova de cada endpoint, comparando o id da jogada mais recente, que cresce ao longo do jogo.
- Valores provisórios aparecem por instantes, como a bola sobre a goal line. A situação incompleta ou impossível é escondida, não exibida.
- Cada resposta que muda é gravada em `data/recordings/<evento>/`, para reproduzir e depurar o jogo depois.
