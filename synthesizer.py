import asyncio
import numpy as np
import sounddevice as sd
import pygame.midi
from queue import Queue
from synth_core import SynthCore, SAMPLE_RATE, BUFFER_SIZE

class MIDISynthesizer:
    def __init__(self):
        self.synth_core = SynthCore()
        self.midi_queue = Queue()
        self.running = True
        
        # Audio stream configuration
        self.buffer_size = 1024  # Smaller chunks for lower latency
        self.streams = []
        
    async def start(self):
        # Initialize MIDI
        pygame.midi.init()
        
        # Find MIDI input device
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            if info[2]:  # is_input
                self.midi_input = pygame.midi.Input(i)
                print(f"Using MIDI input device: {info[1].decode()}")
                break
        else:
            print("No MIDI input devices found!")
            return
            
        # Initialize audio output
        try:
            # Try different audio backends
            stream = None
            backends = ['pulse', 'jack', 'default']
            
            for backend in backends:
                try:
                    print(f"\nTrying {backend} audio backend...")
                    stream = sd.OutputStream(
                        samplerate=SAMPLE_RATE,
                        channels=1,
                        blocksize=self.buffer_size,
                        callback=self._audio_callback,
                        finished_callback=None,
                        device=backend,
                        dtype=np.float32
                    )
                    print(f"Successfully initialized {backend} audio backend")
                    break
                except Exception as e:
                    print(f"Could not initialize {backend} backend: {e}")
                    continue
                    
            if stream is None:
                print("Could not initialize any audio backend")
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
            data = self.synth_core.get_audio_block(frames)
            if data is None or len(data) == 0:
                outdata.fill(0)
            else:
                if len(data) < len(outdata):
                    # Pad with silence if needed
                    padding = np.zeros((len(outdata) - len(data), 1))
                    data = np.vstack((data, padding))
                outdata[:] = data
                
        except Exception as e:
            print(f"Error in audio callback: {e}")
            outdata.fill(0)
            
    async def _midi_loop(self):
        try:
            while self.running:
                if self.midi_input.poll():
                    midi_events = self.midi_input.read(10)
                    for event in midi_events:
                        self._handle_midi_event(event[0])  # event[0] contains the MIDI data
                await asyncio.sleep(0.001)  # Small sleep to prevent busy waiting
        except Exception as e:
            print(f"Error in MIDI loop: {e}")
            
    def _handle_midi_event(self, event):
        status = event[0]
        note = event[1]
        velocity = event[2]
        
        # Note on event
        if status >= 144 and status <= 159:
            if velocity > 0:  # Note on with velocity
                self.synth_core.note_on(note, velocity)
            else:  # Note off (velocity = 0)
                self.synth_core.note_off(note)
                
        # Note off event
        elif status >= 128 and status <= 143:
            self.synth_core.note_off(note)
            
        # CC messages (implement as needed)
        elif status >= 176 and status <= 191:
            self._handle_cc_message(note, velocity)
            
    def _handle_cc_message(self, cc_num, value):
        # Implement CC handling here
        # Example: Modulation wheel
        if cc_num == 1:
            mod_amount = value / 127.0
            # Apply modulation
            
    async def _audio_generation_loop(self):
        try:
            while self.running:
                # Keep the buffer filled
                self.synth_core.fill_buffer()
                await asyncio.sleep(0.001)  # Small sleep to prevent busy waiting
        except Exception as e:
            print(f"Error in audio generation loop: {e}")
            
    def cleanup(self):
        self.running = False
        if hasattr(self, 'midi_input'):
            self.midi_input.close()
        pygame.midi.quit()

if __name__ == "__main__":
    synth = MIDISynthesizer()
    asyncio.run(synth.start())
