import numpy as np
import pygame.midi
from scipy.signal import butter, lfilter

SAMPLE_RATE = 44100
BUFFER_SIZE = SAMPLE_RATE // 10  # 100ms buffer chunks

class Note:
    def __init__(self, note_num, velocity):
        self.note_num = note_num
        self.velocity = velocity / 127.0
        self.frequency = 440.0 * (2.0 ** ((note_num - 69) / 12.0))
        self.phase = 0.0
        self.active = True
        
        # ADSR envelope
        self.attack = 0.01
        self.decay = 0.1
        self.sustain = 0.7
        self.release = 0.2
        self.envelope_state = 'attack'
        self.envelope_pos = 0
        self.current_level = 0.0
        
    def generate_samples(self, num_samples):
        if not self.active:
            return np.zeros(num_samples)
            
        # Generate base waveform
        t = np.arange(num_samples) / SAMPLE_RATE + self.phase
        samples = np.sin(2 * np.pi * self.frequency * t)
        
        # Update phase for next block (prevent discontinuities)
        self.phase = (self.phase + (num_samples / SAMPLE_RATE)) % (1.0 / self.frequency)
        
        # Apply envelope
        envelope = self._get_envelope(num_samples)
        return samples * envelope * self.velocity
        
    def _get_envelope(self, num_samples):
        envelope = np.zeros(num_samples)
        pos = 0
        
        while pos < num_samples:
            if self.envelope_state == 'attack':
                attack_samples = int(self.attack * SAMPLE_RATE)
                remaining = attack_samples - self.envelope_pos
                samples_to_fill = min(remaining, num_samples - pos)
                
                envelope[pos:pos+samples_to_fill] = np.linspace(
                    self.envelope_pos / attack_samples,
                    (self.envelope_pos + samples_to_fill) / attack_samples,
                    samples_to_fill
                )
                
                self.envelope_pos += samples_to_fill
                if self.envelope_pos >= attack_samples:
                    self.envelope_state = 'decay'
                    self.envelope_pos = 0
                
            elif self.envelope_state == 'decay':
                decay_samples = int(self.decay * SAMPLE_RATE)
                remaining = decay_samples - self.envelope_pos
                samples_to_fill = min(remaining, num_samples - pos)
                
                start_level = 1.0 - (self.envelope_pos / decay_samples) * (1.0 - self.sustain)
                end_level = 1.0 - ((self.envelope_pos + samples_to_fill) / decay_samples) * (1.0 - self.sustain)
                
                envelope[pos:pos+samples_to_fill] = np.linspace(start_level, end_level, samples_to_fill)
                
                self.envelope_pos += samples_to_fill
                if self.envelope_pos >= decay_samples:
                    self.envelope_state = 'sustain'
                    
            elif self.envelope_state == 'sustain':
                samples_to_fill = num_samples - pos
                envelope[pos:pos+samples_to_fill] = self.sustain
                
            elif self.envelope_state == 'release':
                release_samples = int(self.release * SAMPLE_RATE)
                remaining = release_samples - self.envelope_pos
                samples_to_fill = min(remaining, num_samples - pos)
                
                if remaining <= 0:
                    self.active = False
                    return envelope
                
                start_level = self.sustain * (1.0 - self.envelope_pos / release_samples)
                end_level = self.sustain * (1.0 - (self.envelope_pos + samples_to_fill) / release_samples)
                
                envelope[pos:pos+samples_to_fill] = np.linspace(start_level, end_level, samples_to_fill)
                
                self.envelope_pos += samples_to_fill
                
            pos += samples_to_fill
            
        return envelope
        
    def release_note(self):
        if self.envelope_state != 'release':
            self.envelope_state = 'release'
            self.envelope_pos = 0

class SynthCore:
    def __init__(self):
        self.active_notes = {}
        self.cc_values = {i: 0 for i in range(128)}  # MIDI CC values
        
        # Initialize MIDI
        pygame.midi.init()
        self.midi_input = None
        
        # Create virtual MIDI input for testing
        try:
            self.midi_input = pygame.midi.Input(0)  # Try default virtual device
            print("Using virtual MIDI input device")
        except:
            print("Could not initialize MIDI input, running in test mode")
            self.midi_input = None
                
        # Initialize high-pass filter
        nyquist = SAMPLE_RATE / 2
        cutoff = 20  # 20 Hz high-pass filter
        self.hp_b, self.hp_a = butter(2, cutoff / nyquist, btype='high')
        
    def process_midi(self):
        if not self.midi_input:
            return
            
        if self.midi_input.poll():
            events = self.midi_input.read(10)
            for event in events:
                status = event[0][0]
                data1 = event[0][1]
                data2 = event[0][2]
                
                if status >= 144 and status <= 159:  # Note On
                    if data2 > 0:
                        self.note_on(data1, data2)
                    else:
                        self.note_off(data1)
                elif status >= 128 and status <= 143:  # Note Off
                    self.note_off(data1)
                elif status >= 176 and status <= 191:  # CC
                    self.handle_cc(data1, data2)
                    
    def note_on(self, note_num, velocity):
        self.active_notes[note_num] = Note(note_num, velocity)
        
    def note_off(self, note_num):
        if note_num in self.active_notes:
            self.active_notes[note_num].release_note()
            
    def handle_cc(self, cc_num, value):
        self.cc_values[cc_num] = value / 127.0
        
        # Handle common MIDI CC messages
        if cc_num == 1:  # Modulation wheel
            # Implement modulation
            pass
        elif cc_num == 7:  # Volume
            # Implement volume control
            pass
        elif cc_num == 10:  # Pan
            # Implement panning
            pass
            
    def get_next_samples(self, num_samples):
        # Mix all active notes
        mixed = np.zeros(num_samples)
        notes_to_remove = []
        
        for note_num, note in self.active_notes.items():
            samples = note.generate_samples(num_samples)
            mixed += samples
            
            if not note.active:
                notes_to_remove.append(note_num)
                
        # Remove finished notes
        for note_num in notes_to_remove:
            del self.active_notes[note_num]
            
        # Apply high-pass filter
        mixed = lfilter(self.hp_b, self.hp_a, mixed)
        
        # Apply CC-controlled effects
        master_volume = self.cc_values[7]  # CC 7 is volume
        if master_volume > 0:
            mixed *= master_volume
            
        # Prevent clipping
        mixed = np.clip(mixed, -1.0, 1.0)
        
        return mixed.reshape(-1, 1)
        
    def cleanup(self):
        if self.midi_input:
            self.midi_input.close()
        pygame.midi.quit()
