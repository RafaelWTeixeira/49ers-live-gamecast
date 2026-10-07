# Operação no StreamYard

Como colocar o Gamecast na live: o StreamYard compõe a cena e o Gamecast entra como compartilhamento de tela
(`docs/adr/0003`). Os dados vêm da ESPN em modo AUTO; o MANUAL é o plano B.

## Como o Gamecast se comporta na tela

- Ele é desenhado em 16:9 (1920×1080) e se ajusta ao tamanho da janela, sem cortar nada. Se a janela não for 16:9,
  sobram faixas escuras nas bordas.
- O fundo é opaco e escuro. Não há áreas de câmera nem banner: câmeras e banners são do StreamYard.
- Em MANUAL, a faixa dos QBs some e o campo ocupa o espaço (`docs/adr/0004`).

## 1. Antes da live

Suba o servidor com os dados da ESPN:

```powershell
.\scripts\live.ps1
```

O script roda sem `--reload` (um arquivo salvo por engano não reinicia o servidor no meio do jogo) e encontra
sozinho o jogo do 49ers em andamento ou o próximo. Se o servidor reiniciar, o Gamecast reconecta sozinho e o jogo é
retomado do snapshot.

Abra no navegador:

- `http://localhost:8000/control`: painel do operador, numa aba ou janela qualquer.
- `http://localhost:8000/overlay`: o Gamecast, numa **janela separada**, usada só para ele.

Para conferir as animações dos Game Events no StreamYard antes do jogo, abra `http://localhost:8000/overlay?demo`
numa janela à parte: ela repete todas as animações. Na live, use sempre `/overlay`, sem `?demo`.

No painel, confira:

- **AUTO** selecionado e o indicador do Provider verde, com o jogo certo (ex.: `ESPN DEN @ SF: OK`).
- **Pré-jogo** e times certos no preview.

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

**Lado do campo.** No kickoff, compare o campo do Gamecast com a TV. Se o 49ers estiver defendendo o lado oposto,
clique em **⇄ Inverter lado do campo** (no card do preview; funciona em AUTO). As trocas do 1º para o 2º quarto e do
3º para o 4º são automáticas. No intervalo e na prorrogação os lados são escolhidos de novo: o painel mostra um
aviso amarelo para conferir com a TV. Inverta se precisar ou clique em **Está certo**.

**AUTO (normal).** A ESPN atualiza placar, relógio, situação, última jogada, QBs e eventos sozinha.

- O placar e a situação chegam primeiro. As estatísticas dos QBs podem chegar alguns segundos depois e, às vezes,
  com até um minuto de atraso.
- O Gamecast segue a ESPN, que mostra cada jogada cerca de 30 a 60 segundos depois de ela acontecer (medido no
  DEN @ SF). É normal o Gamecast ficar atrás da TV.

**Quando passar para MANUAL.** Use quando:

- o indicador do Provider ficar vermelho ("falhando") por mais de alguns segundos;
- o jogo ficar travado ou visivelmente errado.

Em MANUAL você edita o placar, a situação e os eventos pelo painel, e as estatísticas dos QBs somem do Gamecast.
Quando a ESPN voltar, clique em **AUTO**: o Provider assume de novo e as estatísticas voltam.

**Correções.** Em AUTO não é possível editar o jogo. Para corrigir algo, passe para MANUAL, corrija e volte para
AUTO quando a ESPN alcançar.

## 5. Depois do jogo

As respostas da ESPN ficam gravadas em `data/recordings/<id do jogo>/`. Guarde essa pasta: ela serve para reproduzir
o jogo e ajustar o Provider.

## 6. Checklist

- [ ] `.\scripts\live.ps1` rodando
- [ ] Painel em AUTO, com `ESPN <jogo>: OK`
- [ ] Times e fase conferidos no preview
- [ ] Janela do Gamecast dedicada e em tela cheia
- [ ] Compartilhamento ativo, layout com câmeras ao lado e banner configurado no StreamYard
- [ ] No kickoff: lado do campo conferido com a TV
- [ ] Prévia do StreamYard mostrando o Gamecast inteiro e legível
