import pygame.midi

class MidiHandler:
    def __init__(self, device_id=1):
        pygame.midi.init()
        self.device_id = device_id
        self.midi_input = pygame.midi.Input(device_id)

    def read_midi_events(self):
        events = []
        if self.midi_input.poll():
            midi_events = self.midi_input.read(10)
            for event in midi_events:
                data, _ = event
                status, note, velocity, _ = data
                events.append((status, note, velocity))
        return events

    def close(self):
        self.midi_input.close()
        pygame.midi.quit()
