import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.services.llm_service import UnifiedLLMService
from src.infrastructure.ai.groq_service import GroqService

async def test_app_service():
    print("Testing app.services.llm_service.UnifiedLLMService...")
    service = UnifiedLLMService()
    try:
        response = await service._call_groq(
            system_prompt="You are a helpful assistant.",
            user_text="Say 'Hello from App Service'",
            model="llama-3.3-70b-versatile"
        )
        print(f"App Service Response: {response}")
    except Exception as e:
        print(f"App Service Failed: {e}")

async def test_infra_service():
    print("\nTesting src.infrastructure.ai.groq_service.GroqService...")
    service = GroqService()
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from Infra Service'"}
        ]
        response = await service.chat(messages)
        print(f"Infra Service Response: {response}")
    except Exception as e:
        print(f"Infra Service Failed: {e}")

async def main():
    await test_app_service()
    await test_infra_service()

if __name__ == "__main__":
    asyncio.run(main())
