import numpy as np
import pyaudio
import wave
from circ_buffer import CircularBuffer
from audio_feature_extractor import MFCCFeatureExtractor, NormalizationMethod

class AudioController:
    def __init__(self, filepath, audio_features, queue, buffer_size=10):
        self.audio_features = audio_features  # Shared array for audio features
        self.audio_features_queue = queue    # Shared queue for communication

        # Initialize audio stream
        self.wav_file = wave.open(filepath, 'rb')
        self.sr = self.wav_file.getframerate()
        self.channels = self.wav_file.getnchannels()
        self.sample_width = self.wav_file.getsampwidth()
        self.playback_chunk_size = 1024

        # Initialize circular buffer
        self.circular_buffer = CircularBuffer(buffer_size)

        # Initialize feature extractor
        self.feature_extractor = MFCCFeatureExtractor(
            self.circular_buffer,
            self.sr,
            self.channels,
            self.feature_extraction_callback,
            NormalizationMethod.MIN_MAX
        )

        # Start feature extraction thread
        self.feature_extractor.start()

        # Initialize audio playback
        self.format = pyaudio.paInt16
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.p.get_format_from_width(self.sample_width),
            channels=self.channels,
            rate=self.sr,
            output=True,
            frames_per_buffer=self.playback_chunk_size
        )

        self.running = True

    def feature_extraction_callback(self, features):
        """Callback invoked when new audio features are extracted."""
        np.copyto(self.audio_features, features)  # Update shared array
        if self.audio_features_queue is not None:
            self.audio_features_queue.put(features)

    def play_and_extract_features(self):
        """Main loop to play audio and extract features."""
        while self.running:
            frames = self.wav_file.readframes(self.playback_chunk_size)

            # Check if we've reached the end of the file
            if not frames:
                self.wav_file.rewind()  # Rewind for continuous loop
                frames = self.wav_file.readframes(self.playback_chunk_size)

            self.stream.write(frames)

            # Convert raw bytes to float32 audio data
            audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / (2**15)
            if self.channels > 1:
                audio_data = np.mean(audio_data.reshape(-1, self.channels), axis=1)

            self.circular_buffer.append(audio_data)

    def stop(self):
        """Stop audio playback and feature extraction."""
        self.running = False  # Set the flag to False to stop the loop

        # Wait for feature extractor thread to stop
        self.feature_extractor.stop()
        self.feature_extractor.join()

        # Close the PyAudio stream and terminate PyAudio
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
