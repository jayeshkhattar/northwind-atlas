from mcp.server.fastmcp import FastMCP
from .tools import get_order_status, get_customer_orders

mcp = FastMCP("northwind")

mcp.tool()(get_order_status)
mcp.tool()(get_customer_orders)

@mcp.resource("kb://refunds")
def refunds_article() -> str: 
    """The northwind atlas returns and refunds policy"""
    with open ("data/kb/Returns and refunds.md") as f:
        return f.read()

@mcp.prompt()
def refund_process_inquiry_prompt():
    "Refund Process Inquiry Prompt"
    return """What is the refund process"""

@mcp.prompt()
def order_status_prompt(order_id : str):
    "Order Status Prompt"
    return f"""What is the order status for {order_id}"""


if __name__ == "__main__":
    mcp.run()