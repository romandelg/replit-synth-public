import numpy as np
import pygame.midi
from scipy.signal import butter, lfilter

SAMPLE_RATE = 44100
BUFFER_SIZE = SAMPLE_RATE // 10  # 100ms buffer chunks

class Voice:
    def __init__(self, note_num, velocity):
        self.note_num = note_num
        self.velocity = velocity / 127.0
        self.frequency = 440.0 * (2.0 ** ((note_num - 69) / 12.0))
        self.phase = 0.0
        self.active = True
        
        # Oscillator parameters
        self.waveform = 'sine'  # sine, square, saw, triangle
        self.detune = 0.0  # in cents
        self.pulse_width = 0.5  # for square wave
        
        # Filter parameters
        self.filter_cutoff = 1.0
        self.filter_resonance = 0.0
        self.filter_env_amount = 0.0
        
        # ADSR envelope
        self.amp_env = {
            'attack': 0.01,
            'decay': 0.1,
            'sustain': 0.7,
            'release': 0.2
        }
        self.filter_env = {
            'attack': 0.01,
            'decay': 0.1,
            'sustain': 0.5,
            'release': 0.2
        }
        self.envelope_state = 'attack'
        self.envelope_pos = 0
        self.current_level = 0.0
        
        # LFO parameters
        self.lfo_rate = 0.0
        self.lfo_amount = 0.0
        self.lfo_destination = 'none'  # pitch, filter, amplitude
        
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
        samples_to_fill = 0  # Initialize to prevent unbound warning
        
        while pos < num_samples:
            if self.envelope_state == 'attack':
                attack_samples = int(self.amp_env['attack'] * SAMPLE_RATE)
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
                decay_samples = int(self.amp_env['decay'] * SAMPLE_RATE)
                remaining = decay_samples - self.envelope_pos
                samples_to_fill = min(remaining, num_samples - pos)
                
                start_level = 1.0 - (self.envelope_pos / decay_samples) * (1.0 - self.sustain)
                end_level = 1.0 - ((self.envelope_pos + samples_to_fill) / decay_samples) * (1.0 - self.amp_env['sustain'])
                
                envelope[pos:pos+samples_to_fill] = np.linspace(start_level, end_level, samples_to_fill)
                
                self.envelope_pos += samples_to_fill
                if self.envelope_pos >= decay_samples:
                    self.envelope_state = 'sustain'
                    
            elif self.envelope_state == 'sustain':
                samples_to_fill = num_samples - pos
                envelope[pos:pos+samples_to_fill] = self.sustain
                
            elif self.envelope_state == 'release':
                release_samples = int(self.amp_env['release'] * SAMPLE_RATE)
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
        self.voices = {}  # Dictionary of active voices
        self.max_voices = 16
        self.cc_values = {i: 0 for i in range(128)}  # MIDI CC values
        
        # Global parameters
        self.master_volume = 0.8
        self.global_tune = 0.0
        self.voice_params = {
            'waveform': 'sine',
            'detune': 0.0,
            'filter_cutoff': 1.0,
            'filter_resonance': 0.0,
            'amp_attack': 0.01,
            'amp_decay': 0.1,
            'amp_sustain': 0.7,
            'amp_release': 0.2,
            'filter_attack': 0.01,
            'filter_decay': 0.1,
            'filter_sustain': 0.5,
            'filter_release': 0.2,
            'lfo_rate': 0.0,
            'lfo_amount': 0.0
        }
        
        # Parameter change callbacks for GUI updates
        self.param_callbacks = []
        
        # Initialize MIDI
        pygame.midi.init()
        self.midi_input = None
        
        try:
            # List available MIDI devices
            print("\nAvailable MIDI devices:")
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info[2]:  # is_input
                    print(f"{i}: {info[1].decode()}")
                    
            # Try to find a real MIDI input device first
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info[2]:  # is_input
                    try:
                        self.midi_input = pygame.midi.Input(i)
                        print(f"Using MIDI input device: {info[1].decode()}")
                        break
                    except Exception as e:
                        print(f"Could not initialize MIDI device {i}: {e}")
                        continue
        except Exception as e:
            print(f"Error initializing MIDI: {e}")
            
        # If no real device found, try virtual device
        if self.midi_input is None:
            try:
                self.midi_input = pygame.midi.Input(0)
                print("Using virtual MIDI input device")
            except:
                print("Could not initialize MIDI input, running in test mode")
                self.midi_input = None
                
        # Initialize high-pass filter
        nyquist = SAMPLE_RATE / 2
        cutoff = 20  # 20 Hz high-pass filter
        self.hp_b, self.hp_a = butter(2, cutoff / nyquist, btype='high')
        
    def process_midi_event(self, status, data1, data2):
        try:
            # Note On messages (144-159)
            if status >= 144 and status <= 159:
                if data2 > 0:  # velocity > 0 means note on
                    self.note_on(data1, data2)
                else:  # velocity = 0 means note off
                    self.note_off(data1)
                    
            # Note Off messages (128-143)
            elif status >= 128 and status <= 143:
                self.note_off(data1)
                
            # CC messages (176-191)
            elif status >= 176 and status <= 191:
                self.handle_cc(data1, data2)
                
            # Program Change (192-207)
            elif status >= 192 and status <= 207:
                # Handle program changes if needed
                pass
                
            # Pitch Bend (224-239)
            elif status >= 224 and status <= 239:
                # Convert 14-bit pitch bend value
                bend_value = (data2 << 7) + data1
                # Normalize to [-1, 1]
                normalized_bend = (bend_value / 8192.0) - 1.0
                # TODO: Implement pitch bend handling
                
        except Exception as e:
            logger.error(f"Error processing MIDI event: {e}")
                    
    def note_on(self, note_num, velocity):
        # Create new voice and manage polyphony
        self.voices[note_num] = Voice(note_num, velocity)
        # Remove oldest voice if we exceed max_voices
        if len(self.voices) > self.max_voices:
            oldest_note = min(self.voices.keys())
            del self.voices[oldest_note]
        
    def note_off(self, note_num):
        if note_num in self.voices:
            self.voices[note_num].release_note()
            
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
        
        for note_num, voice in self.voices.items():
            samples = voice.generate_samples(num_samples)
            mixed += samples
            
            if not voice.active:
                notes_to_remove.append(note_num)
                
        # Remove finished voices
        for note_num in notes_to_remove:
            del self.voices[note_num]
            
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
