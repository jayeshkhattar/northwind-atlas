import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["-m", "src.mcp_server"],   # how to launch YOUR server
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()          # the handshake
            tools = await session.list_tools()  # ask what tools exist
            print(tools)

            result = await session.call_tool("get_order_status", {"order_id": "NW-10001"})
            print(result)

if __name__ == "__main__":
    asyncio.run(main())