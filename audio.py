import numpy as np
from scipy.signal import butter, lfilter

SAMPLE_RATE = 44100

class Synth:
    def __init__(self):
        self.active_notes = {}
        self.voices = {}  # For GUI compatibility
        self.param_callbacks = []  # List to store parameter update callbacks
        
        # Initialize synthesis parameters
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

    def generate_waveform(self, frequency, duration):
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        # Apply detune
        detuned_freq = frequency * (2 ** (self.voice_params['detune'] / 1200))  # Detune in cents
        
        # Generate basic waveform
        if self.voice_params['waveform'] == "sine":
            wave = np.sin(2 * np.pi * detuned_freq * t)
        elif self.voice_params['waveform'] == "sawtooth":
            wave = 2 * (t * detuned_freq - np.floor(t * detuned_freq + 0.5))
        elif self.voice_params['waveform'] == "triangle":
            wave = 2 * np.abs(2 * (t * detuned_freq - np.floor(t * detuned_freq + 0.5))) - 1
        elif self.voice_params['waveform'] == "square":
            wave = np.where((t * detuned_freq) % 1 < 0.5, 1.0, -1.0)
        else:
            wave = np.sin(2 * np.pi * detuned_freq * t)  # Default to sine
            
        # Apply LFO if enabled
        if self.voice_params['lfo_amount'] > 0:
            lfo = np.sin(2 * np.pi * self.voice_params['lfo_rate'] * t)
            wave *= (1 + lfo * self.voice_params['lfo_amount'])
            
        return wave

    def apply_adsr(self, wave):
        total_samples = len(wave)
        attack_samples = int(self.voice_params['amp_attack'] * SAMPLE_RATE)
        decay_samples = int(self.voice_params['amp_decay'] * SAMPLE_RATE)
        sustain_level = self.voice_params['amp_sustain']
        release_samples = int(self.voice_params['amp_release'] * SAMPLE_RATE)
        sustain_samples = max(0, total_samples - (attack_samples + decay_samples + release_samples))

        env = np.zeros(total_samples)
        if attack_samples > 0:
            env[:attack_samples] = np.linspace(0, 1, attack_samples)
        if decay_samples > 0:
            env[attack_samples:attack_samples + decay_samples] = np.linspace(1, sustain_level, decay_samples)
        if sustain_samples > 0:
            env[attack_samples + decay_samples:attack_samples + decay_samples + sustain_samples] = sustain_level
        if release_samples > 0:
            env[-release_samples:] = np.linspace(sustain_level, 0, release_samples)

        return wave * env

    def high_pass_filter(self, signal, cutoff=100):
        nyquist = SAMPLE_RATE / 2
        normalized_cutoff = cutoff / nyquist
        b, a = butter(2, normalized_cutoff, btype="high", analog=False)
        return lfilter(b, a, signal)

    def mix_notes(self):
        if not self.active_notes:
            return np.zeros(int(SAMPLE_RATE * 0.1))  # Silence if no notes active

        mixed_wave = sum(self.active_notes.values())

        # Normalize to prevent clipping
        max_amplitude = np.max(np.abs(mixed_wave)) if len(mixed_wave) > 0 else 1.0
        if max_amplitude > 1.0:
            mixed_wave /= max_amplitude

        # Apply high-pass filter to remove sub-bass frequencies
        mixed_wave = self.high_pass_filter(mixed_wave, cutoff=80)

        return mixed_wave

    def add_note(self, note, frequency, duration, velocity):
        waveform = self.generate_waveform(frequency, duration)
        adsr_waveform = self.apply_adsr(waveform)
        # Scale by velocity
        self.active_notes[note] = adsr_waveform * (velocity / 127.0)

    def remove_note(self, note):
        if note in self.active_notes:
            del self.active_notes[note]
            
    def update_parameter(self, param, value):
        """Update a synthesis parameter and notify callbacks"""
        if param in self.voice_params:
            self.voice_params[param] = value
            # Notify all registered callbacks
            for callback in self.param_callbacks:
                try:
                    callback(param, value)
                except Exception as e:
                    print(f"Error in parameter callback: {e}")
