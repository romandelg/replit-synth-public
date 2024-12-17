import asyncio
import numpy as np
import sounddevice as sd
from queue import Queue
import threading
from collections import deque
from synth_core import SynthCore, SAMPLE_RATE, BUFFER_SIZE

class AsyncSynthesizer:
    def __init__(self):
        self.synth_core = SynthCore()
        self.audio_buffer = deque(maxlen=BUFFER_SIZE * 2)
        self.running = True
        
        # Audio stream configuration
        self.buffer_size = 1024  # Smaller chunks for lower latency
        self.streams = []
        
    async def start(self):
        # Initialize audio output
        try:
            # Configure sounddevice to use virtual device
            try:
                # Try to initialize with null device first
                stream = sd.OutputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    blocksize=self.buffer_size,
                    callback=self._audio_callback,
                    finished_callback=None,
                    device='null',  # Use null device for virtual environment
                    dtype=np.float32,
                    latency='high'  # Use high latency for better stability
                )
                print("Successfully initialized virtual audio device")
            except Exception as e:
                print(f"Could not initialize audio device: {e}")
                return
                    
            # Start audio processing
            with stream:
                print("\nSynthesizer is running! Press Ctrl+C to stop.")
                await asyncio.gather(
                    self._midi_loop(),
                    self._audio_generation_loop()
                )
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()
            
    def _audio_callback(self, outdata, frames, time, status):
        if status:
            print(f'Audio callback status: {status}')
            
        try:
            # Get audio block with error handling
            if len(self.audio_buffer) < frames:
                # Not enough samples, generate more
                self._fill_buffer(frames * 2)
                
            # Copy samples from buffer to output
            for i in range(frames):
                if self.audio_buffer:
                    outdata[i] = self.audio_buffer.popleft()
                else:
                    outdata[i] = 0
                    
        except Exception as e:
            print(f"Error in audio callback: {e}")
            outdata.fill(0)
            
    def _fill_buffer(self, min_samples):
        while len(self.audio_buffer) < min_samples and self.running:
            # Generate new samples
            new_samples = self.synth_core.get_next_samples(BUFFER_SIZE)
            self.audio_buffer.extend(new_samples.reshape(-1))
            
    async def _midi_loop(self):
        try:
            while self.running:
                # Process MIDI input
                self.synth_core.process_midi()
                await asyncio.sleep(0.001)  # Small sleep to prevent busy waiting
        except Exception as e:
            print(f"Error in MIDI loop: {e}")
            
    async def _audio_generation_loop(self):
        try:
            while self.running:
                # Keep the buffer filled
                self._fill_buffer(BUFFER_SIZE * 2)
                await asyncio.sleep(0.001)  # Small sleep to prevent busy waiting
        except Exception as e:
            print(f"Error in audio generation loop: {e}")
            
    def cleanup(self):
        self.running = False

if __name__ == "__main__":
    synth = AsyncSynthesizer()
    asyncio.run(synth.start())
