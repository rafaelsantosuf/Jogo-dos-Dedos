import cv2
import mediapipe as mp
import random
import time
import os
import urllib.request
import textwrap
import pygame

ARQUIVO_PERGUNTAS = "perguntas.txt"
ARQUIVO_PLACAR = "placar.txt"
MODELO_MAO = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
URL_MODELO_MAO = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
SOM_ACERTO = os.path.join(os.path.dirname(__file__), "sons", "certo.mp3")
SOM_ERRO = os.path.join(os.path.dirname(__file__), "sons", "errado.mp3")

TEMPO_RESPOSTA = 15
TEMPO_ESTABILIDADE_GESTO = 0.8
TEMPO_FEEDBACK = 1.2
LIMIAR_DEDO_ESTICADO = 0.05


def carregar_perguntas():
    perguntas = []

    with open(ARQUIVO_PERGUNTAS, "r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()

            if not linha or linha.startswith("#"):
                continue

            partes = linha.split(";")

            if len(partes) != 3:
                print(f"Linha ignorada por formato inválido: {linha}")
                continue

            pergunta, correta, errada = partes

            perguntas.append({
                "pergunta": pergunta.strip(),
                "correta": correta.strip(),
                "errada": errada.strip()
            })

    if not perguntas:
        raise ValueError("Nenhuma pergunta válida encontrada em perguntas.txt")

    return perguntas


def carregar_placar():
    if not os.path.exists(ARQUIVO_PLACAR):
        salvar_placar(0)
        return 0

    try:
        with open(ARQUIVO_PLACAR, "r", encoding="utf-8") as arquivo:
            return int(arquivo.read().strip())
    except:
        return 0


def salvar_placar(placar):
    with open(ARQUIVO_PLACAR, "w", encoding="utf-8") as arquivo:
        arquivo.write(str(placar))


def sortear_pergunta(perguntas):
    item = random.choice(perguntas)

    opcoes = [item["correta"], item["errada"]]
    random.shuffle(opcoes)

    resposta_correta = opcoes.index(item["correta"]) + 1

    return {
        "pergunta": item["pergunta"],
        "opcoes": opcoes,
        "resposta_correta": resposta_correta
    }


def contar_dedos(hand_landmarks, handedness_label):
    """
    Conta dedos levantados usando os landmarks da mão.

    Para indicador, médio, anelar e mindinho:
    considera levantado quando a ponta do dedo está acima da articulação PIP.

    O polegar não entra na contagem para reduzir falsos positivos.
    """

    landmarks = hand_landmarks.landmark if hasattr(hand_landmarks, "landmark") else hand_landmarks
    dedos = 0

    # Indicador, médio, anelar e mindinho
    dedos_indices = [
        (8, 6),    # indicador
        (12, 10),  # médio
        (16, 14),  # anelar
        (20, 18)   # mindinho
    ]

    for ponta, junta in dedos_indices:
        if landmarks[ponta].y < landmarks[junta].y - LIMIAR_DEDO_ESTICADO:
            dedos += 1

    return dedos


def escrever_texto(img, texto, x, y, escala=0.8, cor=(255, 255, 255), espessura=2):
    tamanho_texto, baseline = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, espessura)
    margem_x = 10
    margem_y = 8

    x1 = max(0, x - margem_x)
    y1 = max(0, y - tamanho_texto[1] - margem_y)
    x2 = min(img.shape[1], x + tamanho_texto[0] + margem_x)
    y2 = min(img.shape[0], y + baseline + margem_y)

    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.putText(
        img,
        texto,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        escala,
        cor,
        espessura,
        cv2.LINE_AA
    )


def escrever_multilinha(img, texto, x, y, largura=45, escala=0.8, cor=(255, 255, 255)):
    linhas = textwrap.wrap(texto, width=largura)

    for i, linha in enumerate(linhas):
        escrever_texto(img, linha, x, y + i * 35, escala, cor)


def centralizar_texto_x(texto, largura_tela, escala=0.8, espessura=2):
    tamanho_texto, _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, espessura)
    return (largura_tela - tamanho_texto[0]) // 2


def desenhar_botao(img, texto, rect):
    x1, y1, x2, y2 = rect

    cv2.rectangle(img, (x1, y1), (x2, y2), (50, 120, 220), -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 2)

    tamanho_texto, _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    texto_x = x1 + ((x2 - x1) - tamanho_texto[0]) // 2
    texto_y = y1 + ((y2 - y1) + tamanho_texto[1]) // 2

    escrever_texto(img, texto, texto_x, texto_y, 0.8, (255, 255, 255), 2)


def clicou_no_retangulo(click, rect):
    if click["x"] is None or click["y"] is None:
        return False

    x, y = click["x"], click["y"]
    x1, y1, x2, y2 = rect

    return x1 <= x <= x2 and y1 <= y <= y2


def garantir_modelo_mao():
    if os.path.exists(MODELO_MAO) and os.path.getsize(MODELO_MAO) > 0:
        return MODELO_MAO

    print("Baixando o modelo de detecção de mãos do MediaPipe...")
    urllib.request.urlretrieve(URL_MODELO_MAO, MODELO_MAO)

    return MODELO_MAO


def desenhar_mao(frame, hand_landmarks):
    altura, largura = frame.shape[:2]
    pontos = [
        (int(landmark.x * largura), int(landmark.y * altura))
        for landmark in hand_landmarks
    ]

    for conexao in mp.tasks.vision.HandLandmarksConnections.HAND_CONNECTIONS:
        ponto_inicio = pontos[conexao.start]
        ponto_fim = pontos[conexao.end]
        cv2.line(frame, ponto_inicio, ponto_fim, (0, 255, 0), 2)

    for x, y in pontos:
        cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)


def tocar_som(caminho_som, sons_cache, audio_ativo):
    if not audio_ativo:
        return

    som = sons_cache.get(caminho_som)

    if som is None:
        if not os.path.exists(caminho_som):
            return

        som = pygame.mixer.Sound(caminho_som)
        sons_cache[caminho_som] = som

    som.play()


def main():
    perguntas = carregar_perguntas()
    placar = carregar_placar()
    modelo_mao = garantir_modelo_mao()

    sons_cache = {}
    audio_ativo = False

    try:
        pygame.mixer.init()
        audio_ativo = True
    except pygame.error:
        print("Aviso: não foi possível inicializar o áudio. O jogo seguirá sem sons.")

    hands = mp.tasks.vision.HandLandmarker.create_from_options(
        mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=modelo_mao),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7
        )
    )

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Erro: não foi possível abrir a câmera.")
        hands.close()
        return

    click = {"x": None, "y": None}

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            click["x"] = x
            click["y"] = y

    cv2.namedWindow("Jogo dos Dedos", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Jogo dos Dedos", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setMouseCallback("Jogo dos Dedos", mouse_callback)

    estado = "MENU"
    pergunta_atual = None
    inicio_pergunta = None

    ultimo_gesto = None
    inicio_gesto = None

    feedback_correto = False
    inicio_feedback = None

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Erro ao capturar imagem da câmera.")
                break

            frame = cv2.flip(frame, 1)
            altura, largura, _ = frame.shape

            botao_inicio = (
                largura // 2 - 140,
                altura // 2 + 80,
                largura // 2 + 140,
                altura // 2 + 140
            )

            dedos_detectados = 0

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imagem_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            resultado = hands.detect_for_video(imagem_mp, int(time.time() * 1000))

            if resultado.hand_landmarks:
                for hand_landmarks, handedness in zip(
                    resultado.hand_landmarks,
                    resultado.handedness
                ):
                    label_mao = handedness[0].category_name if handedness and handedness[0].category_name else "Left"
                    dedos_detectados = contar_dedos(hand_landmarks, label_mao)

                    desenhar_mao(frame, hand_landmarks)

                    break

            if estado == "MENU":
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (largura, altura), (30, 30, 30), -1)
                frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

                escrever_texto(frame, "JOGO DOS DEDOS", centralizar_texto_x("JOGO DOS DEDOS", largura, 1.2, 2), 120, 1.2)
                escrever_texto(frame, "1 dedo = Opcao 1", centralizar_texto_x("1 dedo = Opcao 1", largura, 0.8, 2), 190, 0.8)
                escrever_texto(frame, "2 dedos = Opcao 2", centralizar_texto_x("2 dedos = Opcao 2", largura, 0.8, 2), 230, 0.8)
                escrever_texto(frame, f"Placar atual: {placar}", centralizar_texto_x(f"Placar atual: {placar}", largura, 0.8, 2), 280, 0.8)

                desenhar_botao(frame, "INICIAR", botao_inicio)

                if clicou_no_retangulo(click, botao_inicio):
                    placar = 0
                    salvar_placar(placar)

                    pergunta_atual = sortear_pergunta(perguntas)
                    inicio_pergunta = time.time()

                    ultimo_gesto = None
                    inicio_gesto = None

                    estado = "PERGUNTA"

                    click["x"] = None
                    click["y"] = None

            elif estado == "PERGUNTA":
                tempo_passado = time.time() - inicio_pergunta
                tempo_restante = max(0, int(TEMPO_RESPOSTA - tempo_passado))

                escrever_texto(frame, f"Placar: {placar}", 30, 40, 0.8, (255, 255, 255))
                escrever_texto(frame, f"Tempo: {tempo_restante}s", largura - 180, 40, 0.8, (255, 255, 255))
                escrever_texto(frame, f"Dedos detectados: {dedos_detectados}", 30, altura - 30, 0.7, (255, 255, 0))

                escrever_multilinha(
                    frame,
                    pergunta_atual["pergunta"],
                    30,
                    100,
                    largura=55,
                    escala=0.8,
                    cor=(255, 255, 255)
                )

                escrever_texto(frame, f"1 - {pergunta_atual['opcoes'][0]}", 50, 240, 0.9, (255, 255, 255))
                escrever_texto(frame, f"2 - {pergunta_atual['opcoes'][1]}", 50, 300, 0.9, (255, 255, 255))

                if tempo_restante <= 0:
                    feedback_correto = False
                    inicio_feedback = time.time()
                    tocar_som(SOM_ERRO, sons_cache, audio_ativo)
                    estado = "FEEDBACK"

                elif dedos_detectados in [1, 2]:
                    if dedos_detectados != ultimo_gesto:
                        ultimo_gesto = dedos_detectados
                        inicio_gesto = time.time()
                    else:
                        tempo_estavel = time.time() - inicio_gesto

                        if tempo_estavel >= TEMPO_ESTABILIDADE_GESTO:
                            escolha = dedos_detectados

                            if escolha == pergunta_atual["resposta_correta"]:
                                placar += 1
                                salvar_placar(placar)
                                feedback_correto = True
                                tocar_som(SOM_ACERTO, sons_cache, audio_ativo)
                            else:
                                feedback_correto = False
                                tocar_som(SOM_ERRO, sons_cache, audio_ativo)

                            inicio_feedback = time.time()
                            estado = "FEEDBACK"

                            ultimo_gesto = None
                            inicio_gesto = None
                else:
                    ultimo_gesto = None
                    inicio_gesto = None

            elif estado == "FEEDBACK":
                if feedback_correto:
                    cor_fundo = (0, 180, 0)
                    texto = "ACERTOU!"
                else:
                    cor_fundo = (0, 0, 180)
                    texto = "ERROU!"

                frame[:] = cor_fundo

                escrever_texto(frame, texto, largura // 2 - 130, altura // 2, 1.5, (255, 255, 255), 3)
                escrever_texto(frame, f"Placar: {placar}", largura // 2 - 90, altura // 2 + 70, 1.0, (255, 255, 255), 2)

                if time.time() - inicio_feedback >= TEMPO_FEEDBACK:
                    if feedback_correto:
                        pergunta_atual = sortear_pergunta(perguntas)
                        inicio_pergunta = time.time()
                        estado = "PERGUNTA"
                    else:
                        estado = "GAME_OVER"

            elif estado == "GAME_OVER":
                frame[:] = (0, 0, 180)

                escrever_texto(frame, "FIM DE JOGO", largura // 2 - 150, 130, 1.3, (255, 255, 255), 3)
                escrever_texto(frame, f"Placar final: {placar}", largura // 2 - 130, 210, 1.0, (255, 255, 255), 2)

                escrever_texto(frame, "Clique em qualquer lugar para voltar ao menu", largura // 2 - 290, 290, 0.7, (255, 255, 255), 2)

                if click["x"] is not None and click["y"] is not None:
                    placar = 0
                    salvar_placar(placar)

                    pergunta_atual = None
                    inicio_pergunta = None

                    ultimo_gesto = None
                    inicio_gesto = None

                    estado = "MENU"

                    click["x"] = None
                    click["y"] = None

            escrever_texto(frame, "Pressione Q para sair", largura - 240, altura - 25, 0.45, (200, 200, 200), 1)

            cv2.imshow("Jogo dos Dedos", frame)

            tecla = cv2.waitKey(1) & 0xFF

            if tecla == ord("q"):
                break
    finally:
        hands.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()