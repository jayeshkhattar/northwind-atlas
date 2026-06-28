import json
import random
from datetime import datetime, timedelta

PRODUCTS = [
    {"sku": "GR-100", "name": "Northwind Burr Grinder", "price": 149.00},
    {"sku": "ES-200", "name": "Northwind Espresso Machine", "price": 599.00},
    {"sku": "KT-050", "name": "Pour-Over Kettle", "price": 89.00},
    {"sku": "BN-010", "name": "House Blend Beans 1kg", "price": 24.00},
    {"sku": "BN-020", "name": "Single Origin Beans 1kg", "price": 32.00},
    {"sku": "FL-005", "name": "Replacement Water Filter", "price": 19.00},
]

def generate_customers(count):
    customers = []
    for i in range(count):
        customer = {
            "customer_id": f"CUST-{i:03d}",
            "name": f"Customer {i}",
            "email": f"customer{i}@example.com",
            "tier": random.choice(["standard", "premium"]),
            "joined": (datetime.now() - timedelta(days=random.randint(0, 730))).isoformat()
        }
        customers.append(customer)
    return customers

customers = generate_customers(15)
with open("data/customers.json", "w") as f:
    json.dump(customers, f, indent=2, default=str)
print(f"Wrote {len(customers)} customers")

def generate_orders(count, customers):
    orders = []
    for i in range(count):
        items = [ 
            {
                "product": random.choice(PRODUCTS),
                "qty": random.randint(1, 2)
            }
            for _ in range(random.randint(1, 3))
        ]

    for i in range(count):
        order = {
            "order_id" : f"NW-{10001 + i:05d}",
            "customer_id" : random.choice(customers)["customer_id"],
            "date" : (datetime.now() - timedelta(days=random.randint(0, 180))).isoformat(),
            "status" : random.choice(["processing", "shipped", "delivered", "cancelled", "returned"]),
            "items": items,
            "total": round(sum(item["product"]["price"] * item["qty"] for item in items), 2)
        }
        orders.append(order)
    return orders
orders = generate_orders(50, customers)
with open("data/orders.json", "w") as f:
    json.dump(orders, f, indent=2)
print(f"Wrote {len(orders)} orders")
