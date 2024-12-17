import pygame.midi
import threading
import time

class MidiHandler:
    def __init__(self, event_queue):
        self.event_queue = event_queue
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._midi_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _midi_loop(self):
        # Find the first available MIDI input device
        input_device = None
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            if info[2]:  # is_input
                input_device = pygame.midi.Input(i)
                print(f"Using MIDI input device: {info[1].decode()}")
                break

        if input_device is None:
            print("No MIDI input devices found!")
            return

        try:
            while self.running:
                if input_device.poll():
                    midi_events = input_device.read(10)
                    for event in midi_events:
                        self._process_midi_event(event)
                time.sleep(0.001)
        finally:
            if input_device:
                input_device.close()

    def _process_midi_event(self, event):
        # event[0] is a list: [status, data1, data2, unused]
        status = event[0][0]
        data1 = event[0][1]
        data2 = event[0][2]

        # Note on event
        if status >= 144 and status <= 159:
            if data2 > 0:  # velocity > 0 means note on
                self.event_queue.put({
                    'type': 'note_on',
                    'note': data1,
                    'velocity': data2,
                    'channel': status - 144
                })
            else:  # velocity = 0 means note off
                self.event_queue.put({
                    'type': 'note_off',
                    'note': data1,
                    'velocity': 0,
                    'channel': status - 144
                })

        # Note off event
        elif status >= 128 and status <= 143:
            self.event_queue.put({
                'type': 'note_off',
                'note': data1,
                'velocity': data2,
                'channel': status - 128
            })
