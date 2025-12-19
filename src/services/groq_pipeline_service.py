import json
import logging
import math
from typing import AsyncGenerator, Dict, List, Any
import av
import io
from src.infrastructure.ai.groq_service import GroqService

logger = logging.getLogger(__name__)

class GroqPipelineService:
    def __init__(self):
        self.groq_service = GroqService()
        self.chunk_duration = 30  # seconds

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    async def _chunk_audio_generator(self, file_path: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yields chunks of audio as raw PCM bytes (16kHz, mono, s16le).
        """
        try:
            container = av.open(file_path)
            stream = container.streams.audio[0]
            resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)

            bytes_per_second = 16000 * 2  # 16k rate * 2 bytes (16-bit)
            chunk_size = bytes_per_second * self.chunk_duration
            
            current_chunk_data = bytearray()
            chunk_index = 0
            
            for frame in container.decode(stream):
                frame.pts = None
                resampled_frames = resampler.resample(frame)
                
                for r_frame in resampled_frames:
                    current_chunk_data.extend(r_frame.to_ndarray().tobytes())
                    
                    while len(current_chunk_data) >= chunk_size:
                        start_time = chunk_index * self.chunk_duration
                        end_time = start_time + self.chunk_duration
                        
                        yield {
                            "index": chunk_index,
                            "data": bytes(current_chunk_data[:chunk_size]),
                            "start_time": start_time,
                            "end_time": end_time
                        }
                        
                        current_chunk_data = current_chunk_data[chunk_size:]
                        chunk_index += 1
            
            if current_chunk_data:
                start_time = chunk_index * self.chunk_duration
                # Estimate end time based on remaining bytes
                duration = len(current_chunk_data) / bytes_per_second
                end_time = start_time + duration
                
                yield {
                    "index": chunk_index,
                    "data": bytes(current_chunk_data),
                    "start_time": start_time,
                    "end_time": end_time
                }
                
        except Exception as e:
            logger.error(f"Error chunking audio: {e}")
            raise

    async def process_stream(self, file_path: str) -> AsyncGenerator[str, None]:
        """
        Processes audio file in chunks and yields JSON results stringified.
        """
        accumulated_transcript = ""
        accumulated_summaries = []
        
        chunk_gen = self._chunk_audio_generator(file_path)
        
        async for chunk in chunk_gen:
            chunk_idx = chunk["index"]
            start_str = self._format_time(chunk["start_time"])
            end_str = self._format_time(chunk["end_time"])
            audio_data = chunk["data"]
            
            # 1. Transcribe
            # Add some context from previous transcript if needed (Whisper prompt limits apply)
            prompt = accumulated_transcript[-200:] if accumulated_transcript else ""
            transcript = await self.groq_service.transcribe(audio_data, prompt=prompt)
            
            if not transcript:
                transcript = "[Unintelligible]"
            
            accumulated_transcript += " " + transcript
            
            # 2. Summarize & Analyze
            # We do this in one LLM call to save time and tokens, or two if better.
            # User asked for "Summarization" then "Analytical Reasoning". 
            # Can be combined in one prompt requesting JSON output.
            
            system_prompt = (
                "You are an expert clinical and NLP analyst. "
                "Process the provided audio transcript chunk. "
                "Output valid JSON only."
            )
            
            user_prompt = f"""
            Analyze the following transcript chunk (Time: {start_str} to {end_str}):
            "{transcript}"
            
            Provide:
            1. A concise summary preserving clinical/technical details.
            2. Structured analysis including findings, reasoning chain, and keywords.
            
            Format as JSON:
            {{
                "summary": "...",
                "analysis": {{
                    "findings": "...",
                    "reasoning": "...",
                    "keywords": ["...", "..."]
                }}
            }}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            llm_response_str = await self.groq_service.chat(messages, json_mode=True)
            
            try:
                llm_data = json.loads(llm_response_str)
            except (json.JSONDecodeError, TypeError):
                llm_data = {
                    "summary": "Analysis failed",
                    "analysis": {
                        "findings": "N/A",
                        "reasoning": "N/A",
                        "keywords": []
                    }
                }
            
            result = {
                "chunk_index": chunk_idx,
                "start_time": start_str,
                "end_time": end_str,
                "transcript": transcript,
                "summary": llm_data.get("summary", ""),
                "analysis": llm_data.get("analysis", {})
            }
            
            accumulated_summaries.append(result["summary"])
            
            yield json.dumps(result) + "\n"
        
        # Final Report
        final_report_prompt = f"""
        Based on the following chunk summaries and full transcript, generate a Final Report.
        
        Full Transcript:
        {accumulated_transcript}
        
        Chunk Summaries:
        {" ".join(accumulated_summaries)}
        
        Return JSON:
        {{
            "full_summary": "Global coherent summary...",
            "insight_highlights": "Key analytical/clinical insights..."
        }}
        """
        
        messages = [
             {"role": "system", "content": "You are an expert creating a final clinical report."},
             {"role": "user", "content": final_report_prompt}
        ]
        
        final_resp_str = await self.groq_service.chat(messages, json_mode=True)
        try:
            final_data = json.loads(final_resp_str)
        except:
             final_data = {"full_summary": "Error generating report", "insight_highlights": "N/A"}
             
        final_output = {
            "type": "final_report",
            "data": final_data
        }
        
        yield json.dumps(final_output) + "\n"
