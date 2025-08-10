from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw
import sounddevice as sd
import numpy as np
import wave
import json
from vosk import Model, KaldiRecognizer

# === CONFIGURAÇÃO OLED ===
# Ajuste os endereços conforme seus displays. Normalmente 0x3C e 0x3D.
serial_left = i2c(port=1, address=0x3C)
oled_left = ssd1306(serial_left)

serial_right = i2c(port=1, address=0x3D)
oled_right = ssd1306(serial_right)

def desenhar_olho(oled, piscando=False):
    img = Image.new("1", (oled.width, oled.height), "black")
    draw = ImageDraw.Draw(img)

    if piscando:
        # Olho fechado (retângulo)
        draw.rectangle((20, 30, 100, 40), outline="white", fill="white")
    else:
        # Olho aberto (elipse)
        draw.ellipse((20, 20, 100, 60), outline="white", fill="white")

    oled.display(img)

# Mostrar olhos abertos inicialmente
desenhar_olho(oled_left)
desenhar_olho(oled_right)

# === CONFIGURAÇÃO DO VOSK ===
model = Model("vosk_model")
rec = KaldiRecognizer(model, 16000)

def gravar_audio(arquivo, duracao=4):
    print("🎤 Gravando... fale agora!")
    audio = sd.rec(int(duracao * 16000), samplerate=16000, channels=1, dtype='int16')
    sd.wait()
    with wave.open(arquivo, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio.tobytes())
    print("✅ Gravação concluída!")

def transcrever_audio(arquivo):
    wf = wave.open(arquivo, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    texto_final = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            texto_final += res.get("text", "") + " "
    res = json.loads(rec.FinalResult())
    texto_final += res.get("text", "")
    return texto_final.strip()

# === LOOP PRINCIPAL ===
while True:
    comando = input("\nPressione ENTER para gravar ou 'q' para sair: ")
    if comando.lower() == 'q':
        break

    # Piscar os olhos para indicar gravação
    desenhar_olho(oled_left, piscando=True)
    desenhar_olho(oled_right, piscando=True)

    gravar_audio("fala.wav", duracao=4)

    # Olhos abertos após gravação
    desenhar_olho(oled_left)
    desenhar_olho(oled_right)

    texto = transcrever_audio("fala.wav")
    print(f"🗣 Você disse: {texto}")
