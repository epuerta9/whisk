from openai import AsyncOpenAI
import asyncio

async def test_commands():
    client = AsyncOpenAI(
        base_url="http://localhost:8000/v1",
        api_key="not-needed"
    )

    # Test some commands
    commands = ["/help", "/capabilities", "/chat", "/exit"]
    
    for cmd in commands:
        print(f"\nSending command: {cmd}")
        response = await client.chat.completions.create(
            model="@stream-example/chat.completions",
            messages=[{"role": "user", "content": cmd}],
            headers={"X-Command-Mode": "true"}  # Enable command mode
        )
        print(response.choices[0].message.content)

    # After exiting command mode, test normal chat
    print("\nTesting normal chat after exiting command mode:")
    response = await client.chat.completions.create(
        model="@stream-example/chat.completions",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(test_commands()) 