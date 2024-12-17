import numpy as np
from oscillator import Oscillator
from envelope import ADSREnvelope
from collections import defaultdict
import threading

class AudioEngine:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.active_notes = defaultdict(list)
        self.lock = threading.Lock()
        
        # Initialize synthesis parameters
        self.max_polyphony = 16
        self.master_volume = 0.5

    def handle_midi_event(self, event):
        with self.lock:
            if event['type'] == 'note_on':
                self._handle_note_on(event)
            elif event['type'] == 'note_off':
                self._handle_note_off(event)

    def _handle_note_on(self, event):
        note = event['note']
        velocity = event['velocity'] / 127.0
        
        # Create new oscillator for the note
        osc = Oscillator(self.sample_rate)
        envelope = ADSREnvelope(self.sample_rate)
        
        # Set frequency based on MIDI note number
        freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
        osc.set_frequency(freq)
        
        self.active_notes[note].append({
            'oscillator': osc,
            'envelope': envelope,
            'velocity': velocity
        })
        
        # Limit polyphony
        if len(self.active_notes) > self.max_polyphony:
            oldest_note = min(self.active_notes.keys())
            self.active_notes.pop(oldest_note)

    def _handle_note_off(self, event):
        note = event['note']
        if note in self.active_notes:
            # Trigger release phase for all matching notes
            for voice in self.active_notes[note]:
                voice['envelope'].trigger_release()

    def get_audio_block(self, num_frames):
        with self.lock:
            # Initialize output buffer with overlap
            output = np.zeros(num_frames + 64, dtype=np.float32)  # Add small overlap
            
            # Process all active notes
            notes_to_remove = []
            for note, voices in self.active_notes.items():
                voices_to_remove = []
                
                for voice in voices:
                    # Generate oscillator samples with overlap
                    samples = voice['oscillator'].generate(num_frames + 64)
                    
                    # Apply envelope
                    envelope_values = voice['envelope'].generate(num_frames + 64)
                    samples *= envelope_values
                    
                    # Apply velocity and smoothing
                    samples *= voice['velocity']
                    
                    # Apply smoothing window to reduce clicks
                    if 'prev_samples' in voice:
                        # Crossfade with previous buffer
                        fade_len = 64
                        fade_in = np.linspace(0, 1, fade_len)
                        fade_out = np.linspace(1, 0, fade_len)
                        
                        output[:fade_len] += voice['prev_samples'][-fade_len:] * fade_out
                        samples[:fade_len] *= fade_in
                    
                    # Mix into output
                    output += samples
                    
                    # Store last samples for next buffer
                    voice['prev_samples'] = samples.copy()
                    
                    # Check if envelope is finished
                    if voice['envelope'].is_finished():
                        voices_to_remove.append(voice)
                
                # Remove finished voices
                for voice in voices_to_remove:
                    voices.remove(voice)
                
                # If no voices left for this note, mark for removal
                if not voices:
                    notes_to_remove.append(note)
            
            # Remove empty notes
            for note in notes_to_remove:
                del self.active_notes[note]
            
            # Apply master volume and prevent clipping
            output *= self.master_volume
            output = np.clip(output, -1.0, 1.0)
            
            # Return the main part of the buffer (excluding overlap)
            return output[:num_frames].reshape(-1, 1)
