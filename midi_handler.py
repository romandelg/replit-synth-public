
import pygame.midi
import threading
from queue import Queue

class MidiHandler:
    def __init__(self):
        pygame.midi.init()
        self.callback = None
        self.running = False
        self.event_queue = Queue()
        
    def set_callback(self, callback):
        self.callback = callback

    def start(self):
        try:
            # Find first available input device
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info[2]:  # is_input
                    self.midi_input = pygame.midi.Input(i)
                    print(f"Using MIDI device: {info[1].decode()}")
                    break
            else:
                print("No MIDI input devices found")
                return

            self.running = True
            self.midi_thread = threading.Thread(target=self._midi_callback_loop)
            self.midi_thread.daemon = True
            self.midi_thread.start()

        except Exception as e:
            print(f"Error initializing MIDI: {e}")

    def _midi_callback_loop(self):
        while self.running:
            if self.midi_input.poll():
                events = self.midi_input.read(1)
                if self.callback:
                    for event in events:
                        status = event[0][0]
                        note = event[0][1]
                        velocity = event[0][2]
                        self.callback(status, note, velocity)

    def stop(self):
        self.running = False
        if hasattr(self, 'midi_input'):
            self.midi_input.close()
        pygame.midi.quit()
