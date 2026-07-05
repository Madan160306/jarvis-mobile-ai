import queue, json, sounddevice as sd
from vosk import Model, KaldiRecognizer

class VoiceEngine:
    def __init__(self):
        self.q = queue.Queue()
        self.model = Model("models/vosk-model-small-en-us-0.15")
        self.rec = KaldiRecognizer(self.model, 16000)

    def callback(self, indata, frames, time, status):
        self.q.put(bytes(indata))

    def listen(self):
        with sd.RawInputStream(samplerate=16000, blocksize=8000,
                               dtype='int16', channels=1,
                               callback=self.callback):
            while True:
                data = self.q.get()
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    return result["text"]
