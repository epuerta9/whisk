from openai import AsyncOpenAI
import asyncio

async def test_command_mode():
    client = AsyncOpenAI(
        base_url="http://localhost:8000/v1",
        api_key="not-needed"
    )

    # 1. Enter command mode with :command
    print("\n1. Entering command mode:")
    response = await client.chat.completions.create(
        model="@stream-example/chat.completions",
        messages=[{"role": "user", "content": ":command"}]
    )
    print(response.choices[0].message.content)

    # 2. Test a command
    print("\n2. Testing a command:")
    response = await client.chat.completions.create(
        model="@stream-example/chat.completions",
        messages=[{"role": "user", "content": "/help"}]
    )
    print(response.choices[0].message.content)

    # 3. Exit command mode with :exit
    print("\n3. Exiting command mode:")
    response = await client.chat.completions.create(
        model="@stream-example/chat.completions",
        messages=[{"role": "user", "content": ":exit"}]
    )
    print(response.choices[0].message.content)

    # 4. Test regular chat mode
    print("\n4. Testing regular chat:")
    response = await client.chat.completions.create(
        model="@stream-example/chat.completions",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)

    # 5. Verify command mode is off
    print("\n5. Verify commands don't work:")
    response = await client.chat.completions.create(
        model="@stream-example/chat.completions",
        messages=[{"role": "user", "content": "/help"}]
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(test_command_mode()) 