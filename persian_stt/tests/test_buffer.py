import pytest
from app.services.buffer_manager import BufferManager
from app.core.config import get_settings

settings = get_settings()

def test_buffer_accumulation():
    manager = BufferManager()
    
    # Create 1 second of dummy audio (16000 * 2 bytes)
    one_sec_audio = b'\x00' * 32000
    
    # Settings: Window=4s, Overlap=1s
    # Add 3 seconds -> Should return None
    result = manager.add_audio(one_sec_audio * 3)
    assert result is None
    assert len(manager.buffer) == 32000 * 3
    
    # Add 2 more seconds (Total 5s) -> Should trigger window
    # Window size is 4s (128000 bytes)
    result = manager.add_audio(one_sec_audio * 2)
    assert result is not None
    assert len(result) == 128000 # Exactly 4 seconds (no overlap yet)
    
    # Now buffer should have reduced. 
    # Logic: Consumed (Window - Overlap) = 4s - 1s = 3s.
    # Total input was 5s. Remaining should be 2s?
    # Let's trace:
    # Buffer was 5s. 
    # Extracted 4s. 
    # Consumed 3s (leaving 1s overlap + 1s excess = 2s).
    expected_remaining = (5 * 32000) - (3 * 32000)
    assert len(manager.buffer) == expected_remaining

def test_overlap_logic():
    manager = BufferManager()
    # 1 byte per sample for simpler math? No, code uses 2.
    # Window=4s (128k), Overlap=1s (32k)
    
    chunk_4s = b'\x01' * 128000
    
    # First batch
    res1 = manager.add_audio(chunk_4s)
    assert res1 == chunk_4s # First one has no overlap prefix
    
    # Internal state:
    # Overlap buffer should now be last 1s of chunk_4s (b'\x01' * 32000)
    # Main buffer should have remaining (4s - 3s consumed = 1s remaining)?
    # Wait, my logic: buffer = buffer[consume_size:]
    # consume_size = 3s.
    # So 1s of b'\x01' remains in main buffer.
    
    # Add another 3s of b'\x02'
    chunk_3s = b'\x02' * 96000
    res2 = manager.add_audio(chunk_3s)
    
    # Total buffer now: 1s(x01) + 3s(x02) = 4s. Triggers window.
    # Payload should be: Overlap(x01) + CurrentBuffer(1s(x01) + 3s(x02))
    # Wait, logic: `full_payload = self.overlap_buffer + current_window`
    # overlap_buffer is 1s(x01).
    # current_window is 1s(x01) + 3s(x02).
    # Total payload = 1s(x01) + 1s(x01) + 3s(x02) = 5s.
    # This is correct. The prompt overlap + current window.
    
    assert res2 is not None
    assert len(res2) == 32000 + 128000 # Overlap + Window
    assert res2[0:32000] == b'\x01' * 32000 # The overlap from previous
