import numpy as np

class ADSREnvelope:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        
        # ADSR parameters in seconds
        self.attack = 0.01
        self.decay = 0.1
        self.sustain = 0.7
        self.release = 0.2
        
        self.current_level = 0.0
        self.current_sample = 0
        self.state = 'idle'
        self.release_level = 0.0
        
    def trigger_attack(self):
        self.state = 'attack'
        self.current_sample = 0
        
    def trigger_release(self):
        self.state = 'release'
        self.current_sample = 0
        self.release_level = self.current_level
        
    def is_finished(self):
        return self.state == 'idle' and self.current_level < 0.0001

    def generate(self, num_samples):
        samples = np.zeros(num_samples)
        
        for i in range(num_samples):
            if self.state == 'idle':
                self.current_level = 0.0
                
            elif self.state == 'attack':
                self.current_level = self.current_sample / (self.attack * self.sample_rate)
                if self.current_level >= 1.0:
                    self.current_level = 1.0
                    self.state = 'decay'
                    self.current_sample = 0
                    
            elif self.state == 'decay':
                decay_amount = (1.0 - self.sustain) * (self.current_sample / (self.decay * self.sample_rate))
                self.current_level = 1.0 - decay_amount
                if self.current_level <= self.sustain:
                    self.current_level = self.sustain
                    self.state = 'sustain'
                    
            elif self.state == 'sustain':
                self.current_level = self.sustain
                
            elif self.state == 'release':
                release_amount = self.release_level * (self.current_sample / (self.release * self.sample_rate))
                self.current_level = self.release_level - release_amount
                if self.current_level <= 0.0:
                    self.current_level = 0.0
                    self.state = 'idle'
                    
            samples[i] = self.current_level
            self.current_sample += 1
            
        return samples
