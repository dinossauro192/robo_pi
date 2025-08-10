import sounddevice as sd
import queue
import json
from vosk import Model, KaldiRecognizer
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import pyttsx3

# ==== CONFIGURAÇÃO OLED ====
serial = i2c(port=1, address=0x3C)
oled = ssd1306(serial)
font = ImageFont.load_default()

# ==== FUNÇÃO PARA EXIBIR TEXTO NA OLED ====
def display_text(text):
    image = Image.new("1", oled.size)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    draw.text((0, 20), text, font=font, fill=255)
    oled.display(image)

# ==== RECONHECIMENTO DE VOZ ====
model = Model("model")  # Coloque a pasta do modelo Vosk aqui
recognizer = KaldiRecognizer(model, 16000)
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

# ==== SÍNTESE DE VOZ ====
engine = pyttsx3.init()

# ==== LOOP PRINCIPAL ====
display_text("Aguardando IVA...")

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                       channels=1, callback=callback):

    while True:
        data = q.get()
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").lower()

            if text:
                print("Você disse:", text)
                display_text(text)

                if "iva" in text:
                    engine.say("Ouvindo comando")
                    engine.runAndWait()
                    display_text("Ouvindo...")
