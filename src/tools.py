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

GET_CUSTOMER_ORDERS_SCHEMA = {
    "name": "get_customer_orders",
    "description": "Retrieve ALL orders belonging to a customer, given their customer ID. Use this when a customer wants their full order history or asks to see all of their orders — not when they ask about one specific order by its order ID (use get_order_status for that).",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "description": "unique customer id to find customer starts with CUST. Example CUST-007",
            }
        },
        "required": ["customer_id"],
    },
}


def get_customer_orders(customer_id):
    with open("data/orders.json") as f:
        orders = json.load(f)
        customer_dict = []
        for order in orders:
            if order["customer_id"] == customer_id:
                customer_dict.append(order)
        if not customer_dict:
            return {"message" : f"No order found for customer with id {customer_id}"}
        return customer_dict

def get_order_status(order_id):
    with open("data/orders.json") as f:
        orders = json.load(f)
    for order in orders:
        if order_id == order["order_id"]:
            return order
    return {"error": f"No order found with id {order_id}"}

# print(get_order_status("NW-10001"))
# print(get_order_status("NW-10301"))

