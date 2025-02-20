from openai import AsyncOpenAI
import asyncio

async def test_streaming():
    client = AsyncOpenAI(
        base_url="http://localhost:8000/v1",
        api_key="not-needed"
    )

    stream = await client.chat.completions.create(
        model="@stream-example/chat.interactive",
        messages=[{"role": "user", "content": "Hello world! How are you?"}],
        stream=True
    )

    async for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(test_streaming()) 