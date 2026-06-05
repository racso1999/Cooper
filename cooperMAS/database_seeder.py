import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'orders.db'


# This file seeds the SQLite database with sample orders data for testing and development.
SCHEMA = """ 
CREATE TABLE IF NOT EXISTS orders (
    order_id        TEXT PRIMARY KEY,
    customer_email  TEXT NOT NULL,
    customer_name   TEXT NOT NULL,
    order_date      TEXT NOT NULL,
    status          TEXT NOT NULL,
    total_amount    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id              INTEGER PRIMARY KEY,
    order_id        TEXT NOT NULL REFERENCES orders(order_id),
    product_id      TEXT NOT NULL,
    product_type    TEXT NOT NULL CHECK(product_type IN ('part', 'model')),
    product_name    TEXT NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1,
    unit_price      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
"""

ORDERS = [
    {
        "order_id":       "ORD-10041",
        "customer_email": "margaret.hill@gmail.com",
        "customer_name":  "Margaret Hill",
        "order_date":     "2026-05-03",
        "status":         "delivered",
        "items": [
            ("WPW10348269", "part",  "Dishwasher Drain Pump",           1, 89.99),
            ("W10872845",   "part",  "Dishwasher Filter",               1, 14.50),
        ],
    },
    {
        "order_id":       "ORD-10042",
        "customer_email": "jones.oscar@hotmail.com",
        "customer_name":  "Oscar Jones",
        "order_date":     "2026-05-11",
        "status":         "shipped",
        "items": [
            ("WPW10195039", "part",  "Dishwasher Overfill Control Switch", 1, 34.75),
            ("WP285655",    "part",  "Hose Clamp",                         2,  6.99),
        ],
    },
    {
        "order_id":       "ORD-10043",
        "customer_email": "r.nakamura@outlook.com",
        "customer_name":  "Ryo Nakamura",
        "order_date":     "2026-05-14",
        "status":         "processing",
        "items": [
            ("WDT780SAEM1",  "model", "Whirlpool Dishwasher WDT780SAEM1", 1, 649.00),
        ],
    },
    {
        "order_id":       "ORD-10044",
        "customer_email": "patricia.oduya@yahoo.com",
        "customer_name":  "Patricia Oduya",
        "order_date":     "2026-05-17",
        "status":         "delivered",
        "items": [
            ("WR55X10025",  "part",  "Refrigerator Temperature Sensor",  1, 27.49),
            ("WR30X10093",  "part",  "Refrigerator Ice Maker Assembly",  1, 112.00),
            ("PS11752778",  "part",  "Refrigerator Water Filter",        2, 18.95),
        ],
    },
    {
        "order_id":       "ORD-10045",
        "customer_email": "tom.bevan@gmail.com",
        "customer_name":  "Tom Bevan",
        "order_date":     "2026-05-20",
        "status":         "cancelled",
        "items": [
            ("WPW10545278", "part",  "Dishwasher Drain Hose",            1, 22.30),
        ],
    },
    {
        "order_id":       "ORD-10046",
        "customer_email": "margaret.hill@gmail.com",
        "customer_name":  "Margaret Hill",
        "order_date":     "2026-05-28",
        "status":         "shipped",
        "items": [
            ("WPW10463906", "part",  "Dishwasher Filter Screen",         1, 11.20),
            ("WPW10348269", "part",  "Dishwasher Drain Pump",            1, 89.99),
        ],
    },
    {
        "order_id":       "ORD-10047",
        "customer_email": "jones.oscar@hotmail.com",
        "customer_name":  "Oscar Jones",
        "order_date":     "2026-06-01",
        "status":         "processing",
        "items": [
            ("WRS325SDHZ",  "model", "Whirlpool Refrigerator WRS325SDHZ", 1, 1099.00),
            ("PS16218028",  "part",  "Refrigerator Door Shelf Bin",       2,  31.40),
        ],
    },
    {
        "order_id":       "ORD-10048",
        "customer_email": "c.fernandez@icloud.com",
        "customer_name":  "Carmen Fernandez",
        "order_date":     "2026-06-03",
        "status":         "processing",
        "items": [
            ("WP8194001",   "part",  "Dishwasher Door Latch",            1, 19.85),
            ("W10872845",   "part",  "Dishwasher Filter",                1, 14.50),
            ("8269144A",    "part",  "Drain Hose",                       1, 17.60),
        ],
    },
]


#Fill the database with the above sample orders data.
def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    for order in ORDERS:
        total = sum(qty * price for _, _, _, qty, price in order["items"])
        conn.execute(
            "INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?)",
            (order["order_id"], order["customer_email"], order["customer_name"],
             order["order_date"], order["status"], round(total, 2)),
        )
        for product_id, product_type, product_name, qty, price in order["items"]:
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, product_type, product_name, quantity, unit_price)"
                " VALUES (?,?,?,?,?,?)",
                (order["order_id"], product_id, product_type, product_name, qty, price),
            )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed()
