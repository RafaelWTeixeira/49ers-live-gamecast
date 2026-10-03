# Operação no StreamYard

Como colocar o Gamecast na live: o StreamYard compõe a cena e o Gamecast entra como compartilhamento de tela
(`docs/adr/0003`).

## Como o Gamecast se comporta na tela

- Ele é desenhado em 16:9 (1920×1080) e se ajusta ao tamanho da janela, sem cortar nada. Se a janela não for 16:9,
  sobram faixas escuras nas bordas.
- O fundo é opaco e escuro. Não há áreas de câmera nem banner: câmeras e banners são do StreamYard.
- Em MANUAL, a faixa dos QBs some e o campo ocupa o espaço (`docs/adr/0004`).

## 1. Antes da live

Suba o servidor:

```sh
uv run uvicorn app.main:app
```

Em live, rode sem `--reload`: um arquivo salvo por engano reiniciaria o servidor no meio do jogo. Se ele reiniciar
mesmo assim, o Gamecast reconecta sozinho e o jogo é retomado do snapshot.

Abra no navegador:

- `http://localhost:8000/control`: painel do operador, numa aba ou janela qualquer.
- `http://localhost:8000/overlay`: o Gamecast, numa **janela separada**, usada só para ele.

## 2. Janela do Gamecast

- Para aproveitar a resolução toda, deixe a janela em tela cheia (F11), de preferência num monitor 16:9. Numa janela
  comum também funciona, mas sobram faixas nas bordas.
- Não use essa janela para mais nada. O compartilhamento mostra exatamente o que estiver nela.

## 3. Compartilhar no StreamYard

No estúdio do StreamYard:

1. **Compartilhar tela** → escolha a **janela** ou a **aba** do Gamecast.
2. Não compartilhe o áudio da aba: o Gamecast não tem som.
3. Use o layout com a **tela compartilhada grande e as câmeras numa faixa ao lado** (2 ou 3 câmeras).
4. Coloque o banner ("Deixa o like e se inscreva") pelos banners do StreamYard.
5. Desligue os elementos do StreamYard que cobririam o Gamecast, como nomes sobre a tela.

A resolução do compartilhamento depende do plano do StreamYard.

## 4. Durante a live

- **AUTO:** o Provider atualiza o jogo sozinho. O painel mostra se ele está respondendo.
- **MANUAL:** use quando a API cair ou para corrigir algo. Você edita o placar, a situação e os eventos pelo painel,
  e as estatísticas dos QBs somem até voltar para AUTO.
- O painel tem uma prévia do Gamecast, então dá para conferir sem olhar o StreamYard.

## 5. Checklist

- [ ] Servidor rodando sem `--reload`
- [ ] `/control` aberto e Control Mode correto (AUTO com o Provider OK, ou MANUAL)
- [ ] Times, placar e lado do campo conferidos no painel
- [ ] Janela do Gamecast dedicada e em tela cheia
- [ ] Compartilhamento ativo, layout com câmeras ao lado e banner configurado no StreamYard
- [ ] Prévia do StreamYard mostrando o Gamecast inteiro e legível
