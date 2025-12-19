import asyncio
import httpx
import json

async def test_endpoints():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        print("\n--- Testing Existing Backend Route ---")
        try:
            # Current Backend: /api/pubmed with {"text": "..."}
            response = await client.post("/api/pubmed", json={"text": "asthma"})
            print(f"POST /api/pubmed: {response.status_code}")
            if response.status_code == 200:
                print("Success Response:", response.json()['result'].get('metadata', {}))
            else:
                print("Error:", response.text)
        except Exception as e:
            print(f"Connection Failed: {e}")

        print("\n--- Testing Frontend Expected Route ---")
        try:
            # Frontend Expectation: /api/v1/pubmed/search with {"query": "..."}
            response = await client.post("/api/v1/pubmed/search", json={"query": "asthma"})
            print(f"POST /api/v1/pubmed/search: {response.status_code}")
            print("Response:", response.text[:200])
        except Exception as e:
            print(f"Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())