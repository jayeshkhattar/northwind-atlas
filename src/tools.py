import json

GET_ORDER_STATUS_SCHEMA = {
    "name": "get_order_status",
    "description": "Look up the current status and details of a customer's order — including its status (processing, shipped, delivered, etc.), items, and total. Use this whenever a customer asks about a specific order, such as where their order is, its delivery status, or what it contained.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "unique order id to find order details starts with NW. Example NW-10001",
            }
        },
        "required": ["order_id"],
    },
}


def get_order_status(order_id):
    with open("data/orders.json") as f:
        orders = json.load(f)
    for order in orders:
        if order_id == order["order_id"]:
            return order
    return {"error": f"No order found with id {order_id}"}

# print(get_order_status("NW-10001"))
# print(get_order_status("NW-10301"))