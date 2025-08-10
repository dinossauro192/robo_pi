import queue
import sounddevice as sd
import json
import wave
import threading
import time
from vosk import Model, KaldiRecognizer
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw
import pyttsx3

# === Config OLED ===
serial_left = i2c(port=1, address=0x3C)
oled_left = ssd1306(serial_left)
serial_right = i2c(port=1, address=0x3D)
oled_right = ssd1306(serial_right)

def desenhar_olho(oled, estado):
    img = Image.new("1", (oled.width, oled.height), "black")
    draw = ImageDraw.Draw(img)
    if estado == "aberto":
        draw.ellipse((20, 20, 100, 60), outline="white", fill="white")
    elif estado == "piscando":
        draw.rectangle((20, 30, 100, 40), outline="white", fill="white")
    elif estado == "esperando":
        # Olho meio aberto (linha)
        draw.line((20, 40, 100, 40), fill="white", width=2)
    oled.display(img)

def animar_olhos_continuo():
    while True:
        for estado in ["aberto", "piscando", "aberto", "esperando"]:
            desenhar_olho(oled_left, estado)
            desenhar_olho(oled_right, estado)
            time.sleep(0.4)

# Inicializa síntese de voz offline
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Velocidade da fala

# Config Vosk
model = Model("vosk_model")
recognizer = KaldiRecognizer(model, 16000)

q = queue.Queue()

def callback(indata, frames, time_, status):
    if status:
        print(status)
    q.put(bytes(indata))

# Função para falar texto
def falar(texto):
    engine.say(texto)
    engine.runAndWait()

# Função para gravar áudio dinâmico (enquanto fala)
def gravar_dinamico(duracao_max=10):
    print("🎤 Gravando fala...")
    gravação = sd.rec(int(duracao_max * 16000), samplerate=16000, channels=1, dtype='int16')
    sd.wait()
    return gravação

# Função principal do robô
def robo():
    print("Aguardando wake word 'IVA'...")

    # Começa thread da animação dos olhos
    anim_thread = threading.Thread(target=animar_olhos_continuo, daemon=True)
    anim_thread.start()

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        while True:
            data = q.get()
            if recognizer.AcceptWaveform(data):
                result = recognizer.Result()
                result_dict = json.loads(result)
                texto = result_dict.get("text", "").lower()
                if "iva" in texto:
                    print("Wake word 'IVA' detectada!")

                    # Olhos piscando durante gravação
                    for _ in range(4):
                        desenhar_olho(oled_left, "piscando")
                        desenhar_olho(oled_right, "piscando")
                        time.sleep(0.3)
                        desenhar_olho(oled_left, "aberto")
                        desenhar_olho(oled_right, "aberto")
                        time.sleep(0.3)

                    # Gravação dinâmica (aqui só um tempo fixo, pode melhorar)
                    grava_audio = gravar_dinamico(duracao_max=6)

                    # Salva áudio
                    with wave.open("fala.wav", 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(grava_audio.tobytes())

                    # Transcrever gravação
                    wf = wave.open("fala.wav", "rb")
                    rec = KaldiRecognizer(model, wf.getframerate())
                    texto_final = ""
                    while True:
                        dados = wf.readframes(4000)
                        if len(dados) == 0:
                            break
                        if rec.AcceptWaveform(dados):
                            res = json.loads(rec.Result())
                            texto_final += res.get("text", "") + " "
                    res = json.loads(rec.FinalResult())
                    texto_final += res.get("text", "")

                    texto_final = texto_final.strip()
                    print(f"🗣 Você disse: {texto_final}")

                    # Responder falando
                    if texto_final:
                        resposta = f"Você disse: {texto_final}"
                    else:
                        resposta = "Não entendi o que você falou."
                    falar(resposta)

                    print("Aguardando wake word 'IVA' novamente...")

if __name__ == "__main__":
    robo()
