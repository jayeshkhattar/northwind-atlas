import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .agent import run_agent, extract_reply

server_params = StdioServerParameters(command="python", args=["-m", "src.mcp_server"])

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            #result = await run_agent(session, [], "What's the status of order NW-10001?")
            result = await run_agent(session, [], "What are the orders for customer: CUST-001?")
            print("---")
            print(extract_reply(result))

if __name__ == "__main__":
    asyncio.run(main())
