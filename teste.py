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
import audioop
import noisereduce as nr

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
        self.audio_threshold = 500  # Limite para detecção de voz
        
        # Configuração de Áudio
        sd.default.samplerate = self.sample_rate
        sd.default.channels = self.channels
        sd.default.dtype = 'int16'
        
        # Inicializa síntese de voz
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        
        # Expressões faciais
        self.expressions = {
            "sleep": self.draw_sleep,
            "listen": self.draw_listen,
            "think": self.draw_think,
            "speak": self.draw_speak
        }
        
        self.current_expression = "sleep"
        self.update_display()

    def process_audio(self, audio_data):
        """Processamento avançado do áudio"""
        # Converte para numpy array
        audio = np.frombuffer(audio_data, dtype=np.int16)
        
        # Redução de ruído
        audio = nr.reduce_noise(y=audio, sr=self.sample_rate)
        
        # Normalização
        audio = audio / np.max(np.abs(audio))
        
        return audio

    def listen(self):
        """Captura áudio com detecção de voz ativada"""
        self.set_expression("listen")
        
        print("\n🔊 Ouvindo... (diga 'IVA' para ativar)")
        with sd.InputStream(callback=self.audio_callback):
            while True:
                audio_data = self.audio_queue.get()
                if self.is_speech(audio_data):
                    return self.record_command()

    def record_command(self):
        """Grava um comando de voz completo"""
        frames = []
        silence_frames = 0
        max_silence = 3  # 3 segundos de silêncio para parar
        
        print("🎤 Gravando comando...")
        with sd.InputStream(callback=self.audio_callback):
            while silence_frames < max_silence:
                audio_data = self.audio_queue.get()
                frames.append(audio_data)
                if not self.is_speech(audio_data):
                    silence_frames += 1
                else:
                    silence_frames = 0
        
        return b''.join(frames)

    def is_speech(self, audio_data):
        """Detecta se há voz no áudio usando RMS"""
        rms = audioop.rms(audio_data, 2)
        return rms > self.audio_threshold

    def understand(self, audio):
        """Reconhecimento de fala com Whisper"""
        self.set_expression("think")
        
        try:
            # Converte para float32 e normaliza
            audio = np.frombuffer(audio, dtype=np.int16)
            audio = audio.astype(np.float32) / 32768.0
            
            result = self.model.transcribe(audio)
            text = result["text"].lower().strip()
            print(f"👂 Reconhecido: {text}")
            return text
        except Exception as e:
            print(f"Erro no reconhecimento: {e}")
            return ""

    def respond(self, text):
        """Responde por voz e display"""
        self.set_expression("speak")
        print(f"🗣️ IVA: {text}")
        
        self.engine.say(text)
        self.engine.runAndWait()
        self.set_expression("sleep")

    # Métodos de Display (expressões faciais)
    def set_expression(self, expression):
        self.current_expression = expression
        self.update_display()

    def update_display(self):
        self.expressions[self.current_expression]()

    def draw_sleep(self):
        # Implemente suas expressões aqui
        pass
        
    # [...] (outros métodos de desenho)

def main():
    assistant = IVAAssistant()
    
    try:
        while True:
            # Aguarda ativação por voz
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
