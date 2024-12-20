
import asyncio
import numpy as np
import sounddevice as sd
from audio import Synth
from midi import MidiHandler
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from gui import SynthGUI
import sys

# Configure Qt for headless/offscreen rendering
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'
os.environ['QT_FONT_DPI'] = '96'
os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-runner'
os.environ['DISPLAY'] = ':0'  # Virtual display for headless operation

SAMPLE_RATE = 44100

async def audio_output_loop(synth):
    # Circular buffer for audio data
    buffer_size = SAMPLE_RATE * 2  # Buffer for 2 seconds of audio
    waveform_buffer = np.zeros(buffer_size)
    buffer_start = 0
    buffer_end = 0

    def audio_callback(outdata, frames, time, status):
        nonlocal buffer_start, buffer_end, waveform_buffer
        if status:
            print(f"Audio stream error: {status}")
            outdata.fill(0)
            return

        try:
            # Check if there is enough audio data in the buffer
            available_frames = (buffer_end - buffer_start) % buffer_size
            if available_frames < frames:
                print(f"Buffer underrun: {available_frames} < {frames}")
                outdata.fill(0)
                return

            # Extract the next chunk of audio from the buffer
            for i in range(frames):
                outdata[i] = waveform_buffer[(buffer_start + i) % buffer_size]

            # Update the buffer start position
            buffer_start = (buffer_start + frames) % buffer_size
        except Exception as e:
            print(f"Error in audio callback: {e}")
            outdata.fill(0)

    async def generate_audio():
        nonlocal buffer_end, waveform_buffer
        while True:
            try:
                # Generate new audio data and append to the buffer
                new_waveform = synth.mix_notes()
                new_frames = len(new_waveform)

                # Write new data into the buffer
                for i in range(new_frames):
                    waveform_buffer[(buffer_end + i) % buffer_size] = new_waveform[i]

                # Update the buffer end position
                buffer_end = (buffer_end + new_frames) % buffer_size

                # Sleep to match real-time audio generation
                await asyncio.sleep(new_frames / SAMPLE_RATE)
            except Exception as e:
                print(f"Error generating audio: {e}")
                await asyncio.sleep(0.1)  # Sleep a bit before retrying

    # Start audio stream with error handling
    try:
        # Try to use dummy device for Replit environment
        stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=1024,
            callback=audio_callback,
            device=None,  # Let sounddevice choose the best available device
            latency='high'  # Use high latency for better stability
        )
        print("Successfully created audio stream")
        with stream:
            await generate_audio()
    except Exception as e:
        print(f"Error setting up audio stream: {e}")
        # Continue without audio output in Replit environment
        while True:
            await generate_audio()

async def midi_listener(synth):
    midi_handler = MidiHandler()
    try:
        while True:
            midi_events = midi_handler.read_midi_events()
            for status, note, velocity in midi_events:
                if status == 144 and velocity > 0:  # Note On
                    frequency = 440 * (2 ** ((note - 69) / 12))
                    synth.add_note(note, frequency, 1.0, velocity)
                elif status == 128 or (status == 144 and velocity == 0):  # Note Off
                    synth.remove_note(note)
            await asyncio.sleep(0.01)
    except KeyboardInterrupt:
        print("Exiting MIDI listener.")
    finally:
        midi_handler.close()

def main():
    try:
        print("Setting up environment for headless mode...")
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'
        os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-runner'
        os.environ['DISPLAY'] = ':0'

        print("Initializing QApplication...")
        app = QApplication(sys.argv)
        
        print("Creating Synth instance...")
        synth = Synth()
        
        print("Creating GUI...")
        try:
            gui = SynthGUI(synth)
            gui.show()
            print("GUI initialized successfully")
        except Exception as e:
            print(f"Warning: GUI initialization had issues: {e}")
            print("Continuing with command-line interface...")
        
        print("Setting up event loop...")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Start audio and MIDI processing in background
        print("Starting audio processing...")
        loop.create_task(audio_output_loop(synth))
        
        print("Starting MIDI listener...")
        loop.create_task(midi_listener(synth))
        
        print("Running Qt event loop...")
        # Run Qt event loop
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()
