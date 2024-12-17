import asyncio
import numpy as np  # Import numpy for array operations
import sounddevice as sd
from audio import Synth
from midi import MidiHandler

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

async def main():
    synth = Synth()
    await asyncio.gather(
        audio_output_loop(synth),
        midi_listener(synth)
    )

if __name__ == "__main__":
    asyncio.run(main())
