# Jogo dos Dedos - Guia de Implementacao

Este arquivo descreve, passo a passo, como foi montado o projeto do jogo dos dedos em Python, desde a instalacao das bibliotecas ate a organizacao dos arquivos e a logica principal.

## 1. Objetivo do projeto

O jogo usa a webcam para detectar quantos dedos estao levantados e transforma isso em resposta de multipla escolha.

Fluxo geral:

1. O jogador abre o menu inicial.
2. O jogo mostra uma pergunta com duas opcoes.
3. O sistema detecta 1 ou 2 dedos levantados.
4. Se a resposta estiver correta, toca som de acerto e soma ponto.
5. Se errar, toca som de erro e vai para a tela vermelha de fim de jogo.
6. No fim de jogo, um clique em qualquer lugar volta ao menu.

## 2. Instalacao das bibliotecas

### 2.1. Criar e ativar ambiente virtual

No Windows, a ideia foi usar um ambiente virtual local para isolar as dependencias.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 2.2. Instalar dependencias

As bibliotecas usadas no projeto foram:

```powershell
pip install opencv-python mediapipe pygame
```

- `opencv-python`: captura da webcam, desenho de texto, botões e telas.
- `mediapipe`: detecao da mao e landmarks.
- `pygame`: reproducao dos sons de acerto e erro em MP3.

### 2.3. Observacao sobre o MediaPipe

Na versao instalada aqui, o `mediapipe` nao expunha `mp.solutions`, entao a solucao foi usar a API moderna de `mp.tasks.vision.HandLandmarker`.

O modelo da mao e baixado automaticamente na primeira execucao e salvo como:

- `hand_landmarker.task`

## 3. Estrutura dos arquivos

O projeto ficou organizado assim:

- [main.py](main.py): arquivo principal do jogo.
- [perguntas.txt](perguntas.txt): banco de perguntas e respostas.
- [placar.txt](placar.txt): arquivo simples para salvar o placar.
- [sons/certo.mp3](sons/certo.mp3): som tocado quando o jogador acerta.
- [sons/errado.mp3](sons/errado.mp3): som tocado quando o jogador erra.
- [hand_landmarker.task](hand_landmarker.task): modelo usado pelo MediaPipe para detectar a mao.

## 4. Arquivo `perguntas.txt`

Esse arquivo guarda as perguntas em linhas separadas no formato:

```text
pergunta;resposta_correta;resposta_errada
```

Exemplo:

```text
Quanto é 8 x 8 - 41?;23;22
```

### 4.1. Como o arquivo é lido

A funcao de carregamento:

1. Abre o arquivo em UTF-8.
2. Ignora linhas vazias.
3. Ignora linhas comentadas com `#`.
4. Divide cada linha por `;`.
5. Espera exatamente 3 partes.
6. Salva tudo em uma lista de dicionarios.

### 4.2. Estrutura interna usada no jogo

Cada pergunta vira algo assim:

```python
{
    "pergunta": "Quanto é 8 x 8 - 41?",
    "correta": "23",
    "errada": "22"
}
```

Depois, o jogo embaralha as opcoes e decide em qual posicao ficou a resposta correta.

## 5. Arquivo `placar.txt`

O placar foi guardado em um arquivo de texto simples para persistir entre execucoes.

### 5.1. Regra do arquivo

- Se o arquivo nao existir, ele eh criado com `0`.
- Se existir, o jogo tenta ler o valor inteiro salvo.
- Se der erro de leitura, o jogo retorna `0`.

### 5.2. Uso no jogo

O placar eh salvo sempre que o jogador acerta uma resposta.

Funcoes usadas:

- `carregar_placar()`
- `salvar_placar(placar)`

## 6. Sons

Foram adicionados dois arquivos de audio dentro da pasta `sons`:

- `certo.mp3`
- `errado.mp3`

### 6.1. Como os sons sao tocados

O projeto usa `pygame.mixer` para carregar e tocar os MP3.

Fluxo:

1. O mixer do `pygame` e inicializado no inicio do jogo.
2. Os sons sao carregados sob demanda.
3. Quando o jogador acerta, toca `certo.mp3`.
4. Quando erra ou o tempo acaba, toca `errado.mp3`.

## 7. Detecao de mao com MediaPipe

A versao do MediaPipe instalada no ambiente nao usava mais `mp.solutions`, entao o jogo foi adaptado para `mp.tasks.vision.HandLandmarker`.

### 7.1. Modelo de mao

O jogo baixa automaticamente este modelo se ele nao existir no projeto:

```text
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

### 7.2. Fluxo de deteccao

1. A camera captura o frame.
2. O frame e espelhado com `cv2.flip(frame, 1)`.
3. O frame e convertido para RGB.
4. O frame vira `mp.Image`.
5. O `HandLandmarker` roda em modo `VIDEO`.
6. O jogo recebe os landmarks da mao detectada.
7. A funcao `contar_dedos()` decide se o gesto vale como 1 ou 2 dedos.

## 8. Contagem de dedos

A contagem foi feita de forma mais conservadora para evitar falso positivo.

### 8.1. O que foi considerado

- O polegar foi removido da contagem para reduzir erro.
- Apenas indicador, medio, anelar e mindinho sao avaliados.
- Para cada dedo, a ponta precisa estar acima da junta PIP por um limite minimo.

### 8.2. Limiar usado

O projeto usa um limiar em `y` para considerar o dedo realmente esticado:

```python
LIMIAR_DEDO_ESTICADO = 0.05
```

Se quiser deixar ainda mais rigoroso, esse valor pode ser aumentado.

## 9. Estados do jogo

O jogo usa uma maquina de estados simples:

### 9.1. `MENU`

- Mostra o nome do jogo.
- Mostra instrucoes centrais.
- Espera clique no botao iniciar.

### 9.2. `PERGUNTA`

- Mostra a pergunta.
- Mostra as 2 opcoes.
- Conta o tempo restante.
- Detecta 1 ou 2 dedos.
- Se o gesto ficar estavel por um tempo, valida a resposta.

### 9.3. `FEEDBACK`

- Mostra fundo verde para acerto ou vermelho para erro.
- Toca o som correspondente.
- Depois de um pequeno intervalo, segue para a proxima pergunta ou para o fim de jogo.

### 9.4. `GAME_OVER`

- Mostra tela vermelha de fim de jogo.
- Mantem a tela travada.
- Ao clicar em qualquer lugar, volta para o menu principal.

## 10. Interface visual

Alguns ajustes visuais foram feitos para melhorar a leitura:

- Tela em fullscreen.
- Fundo escuro no menu e nas telas de texto.
- Caixa preta atrás dos textos para aumentar contraste.
- Texto de sair movido para o canto inferior direito.
- Instrucoes do menu centralizadas horizontalmente.

## 11. Arquivo principal `main.py`

O arquivo principal contem toda a implementacao do jogo. Ele centraliza a captura da webcam, a deteccao da mao, a logica de pontuacao, os estados da interface e a reproducao de sons.

Voce pode consultar o codigo completo em:

- [main.py](main.py)

## 12. Como executar

Depois de instalar as dependencias, rode:

```powershell
python main.py
```

Se estiver usando o ambiente virtual:

```powershell
.\.venv\Scripts\activate
python main.py
```

## 13. Resumo das decisoes tecnicas

1. O projeto usa OpenCV para interface e webcam.
2. O MediaPipe moderno foi usado via `HandLandmarker`.
3. O reconhecimento foi simplificado para 1 ou 2 dedos.
4. O polegar foi removido da contagem para reduzir falsos positivos.
5. O placar fica persistido em `placar.txt`.
6. Os sons de certo e errado sao tocados com `pygame`.
7. O fim de jogo fica travado ate um clique.
8. A interface ganhou fullscreen e mais contraste nos textos.

## 14. Possiveis melhorias futuras

- Adicionar mais perguntas.
- Permitir mais de duas alternativas.
- Ajustar a sensibilidade por calibracao.
- Trocar os arquivos de audio por efeitos mais curtos.
- Criar uma tela de configuracao para volume e dificuldade.
