import numpy as np
from scipy.signal import butter, lfilter

SAMPLE_RATE = 44100

class Synth:
    def __init__(self):
        self.active_notes = {}

    def generate_waveform(self, frequency, duration, waveform_type="sine"):
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        if waveform_type == "sine":
            return np.sin(2 * np.pi * frequency * t)
        elif waveform_type == "sawtooth":
            return 2 * (t * frequency - np.floor(t * frequency + 0.5))
        elif waveform_type == "triangle":
            return 2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1
        elif waveform_type == "pulse":
            return np.where((t * frequency) % 1 < 0.5, 1.0, -1.0)
        else:
            raise ValueError("Unsupported waveform type")

    def apply_adsr(self, wave, attack, decay, sustain, release):
        total_samples = len(wave)
        attack_samples = int(attack * SAMPLE_RATE)
        decay_samples = int(decay * SAMPLE_RATE)
        release_samples = int(release * SAMPLE_RATE)
        sustain_samples = max(0, total_samples - (attack_samples + decay_samples + release_samples))

        env = np.zeros(total_samples)
        env[:attack_samples] = np.linspace(0, 1, attack_samples)
        env[attack_samples:attack_samples + decay_samples] = np.linspace(1, sustain, decay_samples)
        env[attack_samples + decay_samples:attack_samples + decay_samples + sustain_samples] = sustain
        env[-release_samples:] = np.linspace(sustain, 0, release_samples)

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
        adsr_waveform = self.apply_adsr(waveform, 0.1, 0.1, 0.8, 0.1)  # Example ADSR values
        self.active_notes[note] = adsr_waveform

    def remove_note(self, note):
        if note in self.active_notes:
            del self.active_notes[note]
