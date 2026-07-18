from mcp.server.fastmcp import FastMCP
from .tools import get_order_status, get_customer_orders

mcp = FastMCP("northwind")

mcp.tool()(get_order_status)
mcp.tool()(get_customer_orders)

if __name__ == "__main__":
    mcp.run()