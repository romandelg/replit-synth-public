
import asyncio
import numpy as np
import sounddevice as sd
from audio import Synth
from midi import MidiHandler
from PyQt5.QtWidgets import QApplication
from gui import SynthGUI
import sys

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

        # Check if there is enough audio data in the buffer
        available_frames = (buffer_end - buffer_start) % buffer_size
        if available_frames < frames:
            # Fill with silence if insufficient data
            outdata[:] = np.zeros((frames, 1))
            return

        # Extract the next chunk of audio from the buffer
        for i in range(frames):
            outdata[i] = waveform_buffer[(buffer_start + i) % buffer_size]

        # Update the buffer start position
        buffer_start = (buffer_start + frames) % buffer_size

    async def generate_audio():
        nonlocal buffer_end, waveform_buffer
        while True:
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

    # Start audio stream
    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, blocksize=2048, callback=audio_callback):
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
    app = QApplication(sys.argv)
    synth = Synth()
    gui = SynthGUI(synth)
    gui.show()
    
    # Create event loop
    loop = asyncio.get_event_loop()
    
    # Start audio and MIDI processing in background
    loop.create_task(audio_output_loop(synth))
    loop.create_task(midi_listener(synth))
    
    # Run Qt event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
