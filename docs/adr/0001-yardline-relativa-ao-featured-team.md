# Yardline medida a partir do Featured Team

A posição da bola é guardada como um único número de 0 a 100, medido a partir da goal line defendida pelo Featured Team (49ers), e não como `side + yard_line`, que é o formato usado pela maioria das APIs da NFL. Escolhemos isso porque a linha 50 não tem "lado" no formato das APIs, e com um número único o cálculo de posição no campo, do first down marker e da red zone vira aritmética simples. O texto exibido (ex.: "DEN 34") e o lado da tela são derivados desse número. Cada Provider é responsável por converter o formato da sua fonte para a Yardline.
