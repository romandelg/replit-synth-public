import numpy as np

class Oscillator:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.phase = 0.0
        self.frequency = 440.0
        self.waveform = 'sine'
        
    def set_frequency(self, freq):
        self.frequency = freq

    def generate(self, num_samples):
        # Calculate phase increment
        phase_increment = 2.0 * np.pi * self.frequency / self.sample_rate
        
        # Generate phase array
        phases = self.phase + phase_increment * np.arange(num_samples)
        
        # Update phase for next block
        self.phase = phases[-1] + phase_increment
        self.phase %= 2.0 * np.pi
        
        if self.waveform == 'sine':
            return np.sin(phases)
        elif self.waveform == 'square':
            return np.sign(np.sin(phases))
        elif self.waveform == 'triangle':
            return 2.0 * np.abs(2.0 * (phases / (2.0 * np.pi) - 
                   np.floor(phases / (2.0 * np.pi) + 0.5))) - 1.0
        elif self.waveform == 'sawtooth':
            return 2.0 * (phases / (2.0 * np.pi) - 
                   np.floor(phases / (2.0 * np.pi) + 0.5))
