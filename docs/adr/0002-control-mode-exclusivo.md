# Control Mode exclusivo: Auto ou Manual

Em qualquer momento, só uma origem pode alterar o Game State: o Provider (modo Auto) ou o operador pelo painel `/control` (modo Manual), com troca explícita por um botão. Descartamos o override por campo e a regra "quem escreve por último vence" porque, durante uma live, uma correção manual não pode ser sobrescrita silenciosamente pelo próximo poll da API, e o operador precisa saber, sem ambiguidade, quem está no comando. A queda da API se resolve trocando para Manual.
