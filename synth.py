import asyncio
import numpy as np
import sounddevice as sd
from queue import Queue
import threading
from collections import deque
from synth_core import SynthCore, SAMPLE_RATE, BUFFER_SIZE
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
            # List available devices
            devices = sd.query_devices()
            logger.info("Available audio devices:")
            for i, dev in enumerate(devices):
                logger.info(f"{i}: {dev['name']}")

            # Try different audio backends
            try:
                # Get list of available devices
                devices = sd.query_devices()
                logger.info(f"Available devices:\n{devices}")
                
                # Try different audio backends and devices
                output_device = None
                backends = ['pulse', 'alsa', 'jack', 'default']
                
                for backend in backends:
                    try:
                        try:
                            with sd.Stream(device=backend, samplerate=SAMPLE_RATE, channels=1, dtype=np.float32):
                                output_device = backend
                                logger.info(f"Selected {backend} output device")
                                break
                        except sd.PortAudioError:
                            continue
                            if output_device:
                                break
                    except Exception as e:
                        logger.warning(f"Could not use {backend} backend: {e}")
                        continue
                
                # Configure stream with optimal settings for continuous audio
                stream_settings = {
                    'samplerate': SAMPLE_RATE,
                    'channels': 1,
                    'dtype': np.float32,
                    'blocksize': 1024,  # Smaller block size for lower latency
                    'callback': self._audio_callback,
                    'finished_callback': None
                }

                if output_device:
                    stream_settings['device'] = output_device

                try:
                    # Try virtual audio device first
                    stream_settings['device'] = 'virtual'
                    stream = sd.OutputStream(**stream_settings)
                    logger.info("Initialized virtual audio device")
                except Exception as virtual_error:
                    logger.warning(f"Could not initialize virtual device: {virtual_error}")
                    try:
                        # Try null device as fallback
                        stream_settings['device'] = None
                        stream = sd.OutputStream(
                            **stream_settings,
                            latency='high',  # Use high latency for stability
                            prime_output_buffers_using_stream_callback=True
                        )
                        logger.info("Initialized null audio device")
                    except Exception as null_error:
                        logger.warning(f"Could not initialize null device: {null_error}")
                        # Last resort: try default system device
                        stream_settings.pop('device', None)  # Remove device specification
                        stream = sd.OutputStream(**stream_settings)
                        logger.info("Initialized default system audio device")
                logger.info("Successfully initialized audio output")
                
            except Exception as e:
                logger.error(f"Could not initialize audio device: {e}")
                logger.warning("Falling back to dummy output device")
                # Create a dummy output device for testing
                stream = sd.OutputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    blocksize=self.buffer_size,
                    callback=self._audio_callback,
                    finished_callback=None,
                    dtype=np.float32,
                    latency='high'
                )
                    
            # Start audio processing
            with stream:
                logger.info("\nSynthesizer is running! Press Ctrl+C to stop.")
                await asyncio.gather(
                    self._midi_loop(),
                    self._audio_generation_loop()
                )
                
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        finally:
            self.cleanup()
            
    def _audio_callback(self, outdata, frames, time, status):
        if status:
            logger.debug(f'Audio callback status: {status}')
            
        try:
            # Ensure buffer is always well-populated
            current_buffer_size = len(self.audio_buffer)
            if current_buffer_size < frames * 4:
                logger.debug(f"Buffer running low ({current_buffer_size} samples), refilling...")
                self._fill_buffer(max(frames * 8, BUFFER_SIZE))
                
            # Apply buffer underrun protection
            if len(self.audio_buffer) < frames and hasattr(self, 'prev_output'):
                logger.warning("Buffer underrun, using fadeout")
                fade = np.linspace(1, 0, frames)
                outdata[:] = self.prev_output * fade.reshape(-1, 1)
                return
                
            if len(self.audio_buffer) < frames:
                logger.warning("Buffer underrun")
                if hasattr(self, 'prev_samples') and len(self.prev_samples) == frames:
                    # Use previous samples with fadeout to prevent clicks
                    fade_out = np.linspace(1, 0, frames)
                    outdata[:] = (self.prev_samples * fade_out).reshape(-1, 1)
                else:
                    outdata.fill(0)
                return
                
            # Get samples from buffer with overlap
            overlap = 64  # Small overlap for crossfading
            if frames > overlap:
                main_frames = frames - overlap
                overlap_frames = overlap
            else:
                main_frames = frames
                overlap_frames = 0
                
            # Get main samples
            samples = np.array([self.audio_buffer.popleft() for _ in range(main_frames)])
            
            # Handle overlap
            if overlap_frames > 0 and hasattr(self, 'prev_overlap'):
                # Crossfade overlap region
                fade_out = np.linspace(1, 0, overlap_frames)
                fade_in = np.linspace(0, 1, overlap_frames)
                
                overlap_samples = np.array([self.audio_buffer.popleft() for _ in range(overlap_frames)])
                samples = np.concatenate([
                    samples,
                    self.prev_overlap * fade_out + overlap_samples * fade_in
                ])
                self.prev_overlap = overlap_samples
            else:
                if overlap_frames > 0:
                    self.prev_overlap = np.array([self.audio_buffer.popleft() for _ in range(overlap_frames)])
                
            # Apply anti-aliasing filter
            if len(samples) > 0:
                nyquist = SAMPLE_RATE / 2
                cutoff = nyquist * 0.95  # Slight cutoff to prevent aliasing
                b, a = butter(4, cutoff / nyquist, btype='low')
                samples = lfilter(b, a, samples)
            
            # Store for possible underrun recovery
            self.prev_samples = samples.copy()
            
            # Reshape and copy to output buffer
            outdata[:] = samples.reshape(-1, 1)
            
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
            outdata.fill(0)
            
    def _fill_buffer(self, min_samples):
        try:
            # Maintain a larger buffer for virtual devices
            target_size = max(min_samples * 4, BUFFER_SIZE * 2)  # Keep quadruple the required samples
            current_size = len(self.audio_buffer)
            
            while len(self.audio_buffer) < target_size and self.running:
                # Generate in smaller chunks for better responsiveness
                chunk_size = min(1024, target_size - len(self.audio_buffer))
                new_samples = self.synth_core.get_next_samples(chunk_size)
                
                if new_samples is not None:
                    samples = new_samples.reshape(-1)
                    
                    # Apply smooth fade in/out at buffer boundaries
                    if len(self.audio_buffer) == 0 and len(samples) > 0:
                        fade_len = min(256, len(samples))
                        fade_in = np.linspace(0, 1, fade_len)
                        samples[:fade_len] *= fade_in
                    
                    # Apply fade out at the end of the chunk
                    if len(samples) > 256:
                        fade_len = 256
                        fade_out = np.linspace(1, 0.9, fade_len)  # Slight fade for smoother transitions
                        samples[-fade_len:] *= fade_out
                    
                    self.audio_buffer.extend(samples)
                    
                    # Prevent buffer from growing too large
                    if len(self.audio_buffer) > BUFFER_SIZE * 4:
                        excess = len(self.audio_buffer) - BUFFER_SIZE * 2
                        for _ in range(excess):
                            self.audio_buffer.popleft()
                else:
                    # Add small amount of silence if no samples
                    silence_len = min(256, target_size - len(self.audio_buffer))
                    silence = np.zeros(silence_len) * 0.001  # Very quiet to maintain continuity
                    self.audio_buffer.extend(silence)
                    
        except Exception as e:
            logger.error(f"Error filling buffer: {e}")
            # Add silence in case of error to prevent complete audio dropout
            silence_samples = min(1024, min_samples - len(self.audio_buffer))
            self.audio_buffer.extend(np.zeros(silence_samples))
            
    async def _midi_loop(self):
        try:
            while self.running:
                # Process MIDI input
                self.synth_core.process_midi()
                await asyncio.sleep(0.001)  # Small sleep to prevent busy waiting
        except Exception as e:
            logger.error(f"Error in MIDI loop: {e}")
            
    async def _audio_generation_loop(self):
        try:
            while self.running:
                # Keep the buffer filled
                self._fill_buffer(BUFFER_SIZE * 2)
                await asyncio.sleep(0.001)  # Small sleep to prevent busy waiting
        except Exception as e:
            logger.error(f"Error in audio generation loop: {e}")
            
    def cleanup(self):
        self.running = False
        self.synth_core.cleanup()

if __name__ == "__main__":
    synth = AsyncSynthesizer()
    asyncio.run(synth.start())
