import pygame.midi

class MidiHandler:
    def __init__(self, device_id=1):
        pygame.midi.init()
        self.device_id = device_id
        
        # Print available MIDI devices
        print("\nAvailable MIDI devices:")
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            if info[2]:  # is_input
                print(f"Input Device {i}: {info[1].decode()}")
            else:
                print(f"Output Device {i}: {info[1].decode()}")
                
        try:
            self.midi_input = pygame.midi.Input(device_id)
            info = pygame.midi.get_device_info(device_id)
            print(f"\nUsing MIDI input device {device_id}: {info[1].decode()}")
        except Exception as e:
            print(f"\nError opening MIDI device {device_id}: {e}")
            print("Trying default device (0)...")
            try:
                self.midi_input = pygame.midi.Input(0)
                info = pygame.midi.get_device_info(0)
                print(f"Using default MIDI input device 0: {info[1].decode()}")
            except:
                print("No MIDI input devices available")
                self.midi_input = None

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
