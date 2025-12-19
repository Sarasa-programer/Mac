import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_websocket_connect_and_disconnect(client: TestClient):
    with client.websocket_connect("/api/v1/realtime") as websocket:
        assert websocket is not None


def test_websocket_transcription_flow(client: TestClient):
    dummy_audio = b"\x00" * 32000

    with patch("src.api.v1.endpoints.realtime.BufferManager") as mock_buffer_cls, patch(
        "src.api.v1.endpoints.realtime.GroqService"
    ) as mock_groq_cls:
        mock_buffer = MagicMock()
        mock_buffer.add_audio.return_value = dummy_audio
        mock_buffer_cls.return_value = mock_buffer

        mock_groq = MagicMock()
        mock_groq.transcribe = AsyncMock(return_value="stub transcription")
        mock_groq_cls.return_value = mock_groq

        with client.websocket_connect("/api/v1/realtime") as websocket:
            websocket.send_bytes(dummy_audio)
            message = websocket.receive_json()

        assert message["type"] == "transcription"
        assert message["text"] == "stub transcription"
        assert message["partial"] is False
