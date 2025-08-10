# -*- coding: utf-8 -*-
import os
import time
import numpy as np
import queue
import sounddevice as sd
from whisper import load_model
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from PIL import Image, ImageDraw, ImageFont
import pyttsx3

# Configurações do Display OLED
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)
font = ImageFont.load_default()

class IVAAssistant:
    def __init__(self):
        # Carrega o modelo Whisper (usando tiny para Raspberry Pi)
        self.model = load_model("tiny")
        self.audio_queue = queue.Queue()
        self.sample_rate = 16000
        self.channels = 1
        
        # Configuração de Áudio
        sd.default.samplerate = self.sample_rate
        sd.default.channels = self.channels
        
        # Inicializa síntese de voz
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)

    def draw_expression(self, expression):
        """Desenha expressões faciais básicas no OLED"""
        img = Image.new('1', (device.width, device.height))
        draw = ImageDraw.Draw(img)
        
        if expression == "neutral":
            draw.ellipse((30, 20, 60, 50), outline=255, fill=0)  # Olho esquerdo
            draw.ellipse((70, 20, 100, 50), outline=255, fill=0)  # Olho direito
            draw.line((40, 70, 90, 70), fill=255, width=2)        # Boca neutra
            
        elif expression == "listening":
            draw.ellipse((30, 20, 60, 50), outline=255, fill=0)
            draw.ellipse((70, 20, 100, 50), outline=255, fill=0)
            draw.arc((40, 60, 90, 80), 0, 180, fill=255, width=2)  # Boca aberta
            
        device.display(img)

    def audio_callback(self, indata, frames, time, status):
        """Callback para captura de áudio"""
        self.audio_queue.put(indata.copy())

    def listen(self):
        """Captura áudio do microfone"""
        self.draw_expression("listening")
        print("\nOuvindo... (diga 'IVA' para ativar)")
        
        with sd.InputStream(callback=self.audio_callback):
            audio = []
            for _ in range(int(5 * self.sample_rate / 1024)):  # Grava por 5 segundos
                audio.append(self.audio_queue.get())
            
            return np.concatenate(audio)

    def understand(self, audio):
        """Reconhecimento de fala com Whisper"""
        self.draw_expression("neutral")
        
        try:
            audio = audio.astype(np.float32) / 32768.0  # Normaliza
            result = self.model.transcribe(audio)
            text = result["text"].lower().strip()
            print(f"Reconhecido: {text}")
            return text
        except Exception as e:
            print(f"Erro no reconhecimento: {e}")
            return ""

    def respond(self, text):
        """Responde por voz e display"""
        self.draw_expression("listening")
        print(f"IVA: {text}")
        
        self.engine.say(text)
        self.engine.runAndWait()
        self.draw_expression("neutral")

def main():
    assistant = IVAAssistant()
    
    try:
        while True:
            # Aguarda comando
            audio = assistant.listen()
            command = assistant.understand(audio)
            
            if "iva" in command:
                assistant.respond("Sim, estou aqui! Como posso ajudar?")
            elif "hora" in command:
                assistant.respond(f"Agora são {time.strftime('%H:%M')}")
            elif "data" in command:
                assistant.respond(f"Hoje é {time.strftime('%d/%m/%Y')}")
            else:
                assistant.respond("Não entendi o comando")
                
    except KeyboardInterrupt:
        print("\nDesligando IVA...")

if __name__ == "__main__":
    main()
