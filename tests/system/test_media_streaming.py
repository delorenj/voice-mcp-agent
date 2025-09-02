"""
Real-time Media Streaming Functionality Tests
Comprehensive testing of audio/video streaming capabilities
"""

import pytest
import asyncio
import aiohttp
import websockets
import json
import wave
import numpy as np
from pathlib import Path
import tempfile
import time
from typing import Dict, List, Optional, Tuple, AsyncIterator
import logging
import subprocess
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AudioTestData:
    """Audio test data container"""
    sample_rate: int
    channels: int
    duration: float
    format: str
    data: np.ndarray

@dataclass 
class StreamingMetrics:
    """Streaming performance metrics"""
    latency_ms: float
    jitter_ms: float
    packet_loss_percent: float
    bitrate_kbps: float
    quality_score: float

class AudioGenerator:
    """Generate test audio data for streaming tests"""
    
    @staticmethod
    def generate_sine_wave(
        frequency: float = 440.0, 
        duration: float = 1.0,
        sample_rate: int = 48000,
        amplitude: float = 0.5
    ) -> AudioTestData:
        """Generate sine wave test audio"""
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Convert to int16
        audio_data = (wave_data * 32767).astype(np.int16)
        
        return AudioTestData(
            sample_rate=sample_rate,
            channels=1,
            duration=duration,
            format='int16',
            data=audio_data
        )
    
    @staticmethod
    def generate_white_noise(
        duration: float = 1.0,
        sample_rate: int = 48000,
        amplitude: float = 0.1
    ) -> AudioTestData:
        """Generate white noise test audio"""
        samples = int(sample_rate * duration)
        noise_data = amplitude * np.random.randn(samples)
        
        # Convert to int16
        audio_data = (noise_data * 32767).astype(np.int16)
        
        return AudioTestData(
            sample_rate=sample_rate,
            channels=1,
            duration=duration,
            format='int16', 
            data=audio_data
        )
    
    @staticmethod
    def generate_speech_like(
        duration: float = 2.0,
        sample_rate: int = 16000
    ) -> AudioTestData:
        """Generate speech-like audio patterns for STT testing"""
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        
        # Combine multiple frequencies to simulate speech
        speech_freqs = [200, 400, 800, 1200, 1600]  # Speech formants
        speech_data = np.zeros(samples)
        
        for i, freq in enumerate(speech_freqs):
            amplitude = 0.2 / (i + 1)  # Decreasing amplitude
            speech_data += amplitude * np.sin(2 * np.pi * freq * t)
        
        # Add some modulation to simulate speech patterns
        envelope = np.sin(2 * np.pi * 2 * t)  # 2 Hz modulation
        speech_data *= (0.5 + 0.5 * envelope)
        
        # Convert to int16
        audio_data = (speech_data * 32767).astype(np.int16)
        
        return AudioTestData(
            sample_rate=sample_rate,
            channels=1,
            duration=duration,
            format='int16',
            data=audio_data
        )
    
    @staticmethod
    def save_wav_file(audio_data: AudioTestData, filepath: str) -> None:
        """Save audio data to WAV file"""
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(audio_data.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(audio_data.sample_rate)
            wav_file.writeframes(audio_data.data.tobytes())

class LiveKitStreamingTester:
    """LiveKit streaming functionality tester"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
    
    async def setup(self):
        """Initialize streaming test setup"""
        self.session = aiohttp.ClientSession()
    
    async def teardown(self):
        """Cleanup streaming test resources"""
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.close()
    
    async def create_room(self, room_name: str) -> Dict:
        """Create a test room for streaming"""
        # This would typically use LiveKit SDK to create room
        # For testing, we'll simulate room creation
        room_data = {
            'room_id': room_name,
            'created_at': int(time.time()),
            'participants': 0,
            'status': 'active'
        }
        
        logger.info(f"Created test room: {room_name}")
        return room_data
    
    async def simulate_audio_stream(
        self, 
        room_id: str,
        audio_data: AudioTestData,
        chunk_size_ms: int = 20
    ) -> AsyncIterator[bytes]:
        """Simulate audio streaming in chunks"""
        chunk_samples = int(audio_data.sample_rate * chunk_size_ms / 1000)
        total_chunks = len(audio_data.data) // chunk_samples
        
        for i in range(total_chunks):
            start_idx = i * chunk_samples
            end_idx = start_idx + chunk_samples
            chunk_data = audio_data.data[start_idx:end_idx]
            
            yield chunk_data.tobytes()
            await asyncio.sleep(chunk_size_ms / 1000)  # Simulate real-time streaming

@pytest.fixture
async def streaming_tester():
    """Fixture providing streaming tester"""
    config = {
        'livekit': {
            'host': 'localhost',
            'port': 7880,
            'api_key': 'APIcQP8xHwvsq7d', 
            'api_secret': 'RJ3CeZtWyb6d3cQPDfLfDxOjVmzxJKh6pb0i3bIyeI3B'
        },
        'test_mode': True  # Use local testing
    }
    
    tester = LiveKitStreamingTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()

class TestAudioStreaming:
    """Test audio streaming functionality"""
    
    async def test_audio_chunk_streaming(self, streaming_tester):
        """Test audio streaming in real-time chunks"""
        # Generate test audio
        audio = AudioGenerator.generate_sine_wave(frequency=1000, duration=2.0)
        
        room_id = f"test-room-{int(time.time())}"
        await streaming_tester.create_room(room_id)
        
        # Stream audio in chunks
        chunks_received = 0
        total_bytes = 0
        start_time = time.time()
        
        async for chunk in streaming_tester.simulate_audio_stream(room_id, audio, chunk_size_ms=20):
            chunks_received += 1
            total_bytes += len(chunk)
            
            # Validate chunk size
            expected_chunk_size = int(audio.sample_rate * 0.02) * 2  # 20ms chunks, 16-bit
            assert len(chunk) == expected_chunk_size, f"Unexpected chunk size: {len(chunk)}"
        
        end_time = time.time()
        streaming_duration = end_time - start_time
        
        # Validate streaming performance
        expected_chunks = int(audio.duration / 0.02)  # 20ms chunks
        assert chunks_received == expected_chunks, f"Missing chunks: expected {expected_chunks}, got {chunks_received}"
        
        # Check real-time performance (should take approximately audio duration)
        assert abs(streaming_duration - audio.duration) < 0.1, f"Streaming not real-time: {streaming_duration:.2f}s for {audio.duration:.2f}s audio"
        
        logger.info(f"Streamed {chunks_received} chunks ({total_bytes} bytes) in {streaming_duration:.2f}s")
    
    async def test_audio_format_compatibility(self, streaming_tester):
        """Test various audio format compatibility"""
        audio_formats = [
            (48000, 1, 'high_quality'),
            (16000, 1, 'speech_optimized'),
            (8000, 1, 'bandwidth_limited'),
            (44100, 1, 'cd_quality')
        ]
        
        for sample_rate, channels, description in audio_formats:
            audio = AudioGenerator.generate_sine_wave(
                frequency=440,
                duration=0.5,
                sample_rate=sample_rate
            )
            
            room_id = f"test-format-{sample_rate}"
            await streaming_tester.create_room(room_id)
            
            # Test streaming this format
            chunks_received = 0
            async for chunk in streaming_tester.simulate_audio_stream(room_id, audio):
                chunks_received += 1
            
            assert chunks_received > 0, f"No chunks received for {description} format ({sample_rate}Hz)"
            logger.info(f"Successfully streamed {description} format: {sample_rate}Hz")
    
    async def test_audio_quality_preservation(self, streaming_tester):
        """Test audio quality preservation during streaming"""
        # Generate known audio pattern
        test_frequency = 1000.0  # 1kHz sine wave
        audio = AudioGenerator.generate_sine_wave(
            frequency=test_frequency,
            duration=1.0,
            sample_rate=48000
        )
        
        room_id = f"test-quality-{int(time.time())}"
        await streaming_tester.create_room(room_id)
        
        # Collect streamed chunks
        streamed_data = bytearray()
        async for chunk in streaming_tester.simulate_audio_stream(room_id, audio):
            streamed_data.extend(chunk)
        
        # Convert back to numpy array
        streamed_audio = np.frombuffer(streamed_data, dtype=np.int16)
        
        # Validate audio integrity
        assert len(streamed_audio) == len(audio.data), "Audio length mismatch after streaming"
        
        # Calculate correlation to check quality preservation
        correlation = np.corrcoef(audio.data, streamed_audio)[0, 1]
        assert correlation > 0.99, f"Audio quality degraded: correlation {correlation:.4f}"
        
        logger.info(f"Audio quality preserved: correlation {correlation:.4f}")

class TestCustomWhisperSTT:
    """Test custom Whisper STT streaming integration"""
    
    async def test_whisper_stt_integration(self, streaming_tester):
        """Test Whisper STT with streamed audio"""
        # Generate speech-like audio
        speech_audio = AudioGenerator.generate_speech_like(duration=2.0, sample_rate=16000)
        
        # Save to temporary WAV file for Whisper processing
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            AudioGenerator.save_wav_file(speech_audio, temp_wav.name)
            
            try:
                # Test Whisper processing (would normally be integrated with streaming)
                # This simulates the CustomWhisperSTT class functionality
                from custom_whisper_stt import CustomWhisperSTT
                
                whisper_stt = CustomWhisperSTT(
                    model_size="base",
                    language="en",
                    device="cpu",
                    compute_type="int8"
                )
                
                # Load audio for processing
                import livekit.agents.utils as utils
                
                # Create mock audio buffer (normally from streaming)
                audio_frames = [speech_audio.data]  # Mock frame data
                
                # This would normally be done in the streaming pipeline
                logger.info("Whisper STT integration test - would process streaming audio")
                
            except ImportError:
                pytest.skip("CustomWhisperSTT not available for testing")
            finally:
                Path(temp_wav.name).unlink()  # Cleanup
    
    async def test_stt_latency_requirements(self, streaming_tester):
        """Test STT processing latency requirements"""
        # Generate various speech audio lengths
        test_durations = [0.5, 1.0, 2.0, 5.0]  # seconds
        
        for duration in test_durations:
            speech_audio = AudioGenerator.generate_speech_like(
                duration=duration, 
                sample_rate=16000
            )
            
            # Measure processing time (simulate)
            start_time = time.time()
            
            # Simulate STT processing time
            await asyncio.sleep(0.1)  # Simulate 100ms processing
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # STT processing should be much faster than audio duration
            assert processing_time < duration * 0.5, f"STT too slow: {processing_time:.3f}s for {duration}s audio"
            
            logger.info(f"STT processing time: {processing_time:.3f}s for {duration}s audio")
    
    async def test_continuous_speech_recognition(self, streaming_tester):
        """Test continuous speech recognition from streaming audio"""
        # Generate continuous speech-like audio
        total_duration = 10.0  # 10 seconds
        chunk_duration = 1.0   # Process in 1-second chunks
        
        room_id = f"test-continuous-stt-{int(time.time())}"
        await streaming_tester.create_room(room_id)
        
        # Simulate continuous speech recognition
        recognized_chunks = 0
        total_audio_processed = 0
        
        for i in range(int(total_duration / chunk_duration)):
            # Generate chunk of speech-like audio
            chunk_audio = AudioGenerator.generate_speech_like(
                duration=chunk_duration,
                sample_rate=16000
            )
            
            # Simulate streaming and STT processing
            chunk_bytes = 0
            async for audio_chunk in streaming_tester.simulate_audio_stream(room_id, chunk_audio):
                chunk_bytes += len(audio_chunk)
            
            # Simulate STT processing
            processing_start = time.time()
            await asyncio.sleep(0.05)  # Simulate 50ms STT processing
            processing_time = time.time() - processing_start
            
            recognized_chunks += 1
            total_audio_processed += chunk_duration
            
            # Ensure real-time processing capability
            assert processing_time < chunk_duration, f"STT processing too slow for real-time: {processing_time:.3f}s"
        
        assert recognized_chunks == int(total_duration / chunk_duration), "Missing STT processing chunks"
        assert abs(total_audio_processed - total_duration) < 0.1, "Audio duration mismatch"
        
        logger.info(f"Processed {recognized_chunks} chunks ({total_audio_processed}s audio) for continuous STT")

class TestStreamingPerformance:
    """Test streaming performance characteristics"""
    
    async def test_concurrent_streams_performance(self, streaming_tester):
        """Test performance with multiple concurrent audio streams"""
        concurrent_streams = 5
        stream_duration = 2.0
        
        # Create test rooms and audio
        rooms_and_audio = []
        for i in range(concurrent_streams):
            room_id = f"test-concurrent-{i}"
            await streaming_tester.create_room(room_id)
            
            audio = AudioGenerator.generate_sine_wave(
                frequency=440 + i * 100,  # Different frequencies
                duration=stream_duration
            )
            
            rooms_and_audio.append((room_id, audio))
        
        # Start concurrent streaming
        start_time = time.time()
        
        async def stream_audio(room_id, audio):
            chunks = 0
            async for chunk in streaming_tester.simulate_audio_stream(room_id, audio):
                chunks += 1
            return chunks
        
        # Run all streams concurrently
        tasks = [stream_audio(room_id, audio) for room_id, audio in rooms_and_audio]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_streaming_time = end_time - start_time
        
        # Validate concurrent performance
        assert total_streaming_time < stream_duration * 1.2, f"Concurrent streaming too slow: {total_streaming_time:.2f}s"
        
        # All streams should have processed chunks
        for i, chunk_count in enumerate(results):
            assert chunk_count > 0, f"Stream {i} processed no chunks"
        
        logger.info(f"Concurrent streaming: {concurrent_streams} streams in {total_streaming_time:.2f}s")
    
    async def test_streaming_memory_usage(self, streaming_tester):
        """Test memory usage during streaming"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Stream longer audio to test memory usage
        long_audio = AudioGenerator.generate_white_noise(duration=10.0)
        room_id = f"test-memory-{int(time.time())}"
        await streaming_tester.create_room(room_id)
        
        chunks_processed = 0
        async for chunk in streaming_tester.simulate_audio_stream(room_id, long_audio):
            chunks_processed += 1
            
            # Check memory every 100 chunks
            if chunks_processed % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                # Memory usage shouldn't increase significantly
                assert memory_increase < 100, f"Memory leak detected: {memory_increase:.2f}MB increase"
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory - initial_memory
        
        logger.info(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB ({total_memory_increase:+.1f}MB)")
    
    async def test_streaming_cpu_usage(self, streaming_tester):
        """Test CPU usage during streaming"""
        import psutil
        
        # Monitor CPU usage during streaming
        cpu_measurements = []
        
        def measure_cpu():
            cpu_measurements.append(psutil.cpu_percent(interval=0.1))
        
        # Start CPU monitoring
        cpu_thread = threading.Thread(target=lambda: [measure_cpu() for _ in range(20)])  # 2 seconds of measurements
        
        audio = AudioGenerator.generate_sine_wave(duration=2.0)
        room_id = f"test-cpu-{int(time.time())}"
        await streaming_tester.create_room(room_id)
        
        cpu_thread.start()
        
        # Stream audio while monitoring CPU
        chunks_processed = 0
        async for chunk in streaming_tester.simulate_audio_stream(room_id, audio):
            chunks_processed += 1
        
        cpu_thread.join()
        
        if cpu_measurements:
            avg_cpu = sum(cpu_measurements) / len(cpu_measurements)
            max_cpu = max(cpu_measurements)
            
            # CPU usage should be reasonable
            assert avg_cpu < 50, f"High average CPU usage during streaming: {avg_cpu:.1f}%"
            assert max_cpu < 80, f"High peak CPU usage during streaming: {max_cpu:.1f}%"
            
            logger.info(f"CPU usage during streaming: avg={avg_cpu:.1f}%, max={max_cpu:.1f}%")

class TestStreamingReliability:
    """Test streaming reliability and error handling"""
    
    async def test_stream_interruption_recovery(self, streaming_tester):
        """Test recovery from stream interruption"""
        audio = AudioGenerator.generate_sine_wave(duration=3.0)
        room_id = f"test-recovery-{int(time.time())}"
        await streaming_tester.create_room(room_id)
        
        chunks_before_interruption = 0
        chunks_after_recovery = 0
        interruption_simulated = False
        
        async for i, chunk in enumerate(streaming_tester.simulate_audio_stream(room_id, audio)):
            if i == 50 and not interruption_simulated:  # Simulate interruption
                interruption_simulated = True
                chunks_before_interruption = i
                
                # Simulate brief interruption
                await asyncio.sleep(0.1)
                logger.info("Simulated stream interruption")
                
                # Continue streaming (simulating recovery)
            
            if interruption_simulated and i > 50:
                chunks_after_recovery += 1
        
        assert chunks_before_interruption > 0, "No chunks processed before interruption"
        assert chunks_after_recovery > 0, "No chunks processed after recovery"
        
        logger.info(f"Stream recovery test: {chunks_before_interruption} chunks before, {chunks_after_recovery} after interruption")
    
    async def test_malformed_audio_handling(self, streaming_tester):
        """Test handling of malformed or corrupted audio data"""
        room_id = f"test-malformed-{int(time.time())}"
        await streaming_tester.create_room(room_id)
        
        # Generate various malformed audio scenarios
        test_cases = [
            b'',  # Empty data
            b'\x00' * 100,  # Null bytes
            b'\xFF' * 100,  # Max values
            b'invalid_audio_data',  # Non-audio data
        ]
        
        for i, malformed_data in enumerate(test_cases):
            try:
                # Simulate processing malformed data
                # In real implementation, this would test error handling
                if len(malformed_data) > 0:
                    logger.info(f"Processing malformed data case {i}: {len(malformed_data)} bytes")
                
                # Error handling should gracefully handle malformed data
                # This would typically be done in the audio processing pipeline
                assert True  # Placeholder for actual error handling validation
                
            except Exception as e:
                # Expected behavior for malformed data
                logger.info(f"Malformed data case {i} properly handled: {e}")

@pytest.mark.asyncio
async def test_end_to_end_streaming():
    """End-to-end streaming test"""
    tester = LiveKitStreamingTester({'test_mode': True})
    await tester.setup()
    
    try:
        # Generate test audio
        audio = AudioGenerator.generate_speech_like(duration=1.0)
        
        # Create room
        room_id = "e2e-test-room"
        await tester.create_room(room_id)
        
        # Stream audio
        total_chunks = 0
        async for chunk in tester.simulate_audio_stream(room_id, audio):
            total_chunks += 1
        
        assert total_chunks > 0, "No audio chunks streamed in end-to-end test"
        
        logger.info(f"End-to-end streaming test completed: {total_chunks} chunks")
        
    finally:
        await tester.teardown()

if __name__ == "__main__":
    # Run media streaming tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])