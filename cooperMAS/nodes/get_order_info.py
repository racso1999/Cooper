import sqlite3

from .config import _fired, DB_PATH
from .state import State

# This node performs an order lookup based on the extracted order ID and email from the user's query.
def get_order_info(state: State):
    if not _fired:
        print("\nI'm just gathering some more information for you, hold tight...\n", flush=True)
    _fired.append('[ORDER]')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT o.order_id, o.customer_name, o.order_date, o.status, o.total_amount,
               GROUP_CONCAT(i.product_id || ' - ' || i.product_name || ' (x' || i.quantity || ')', '; ') AS items
        FROM orders o
        JOIN order_items i ON i.order_id = o.order_id
        WHERE UPPER(o.order_id)       = UPPER(?)
          AND LOWER(o.customer_email) = LOWER(?)
        GROUP BY o.order_id
    """, (state.get('order_id', '').strip(), state.get('order_email', '').strip())).fetchone()
    conn.close()
    if not row:
        return {'order_info': "No order found matching that order ID and email. Please check both and try again."}
    return {'order_info': (
        f"Order ID: {row['order_id']}\n"
        f"Customer: {row['customer_name']}\n"
        f"Date:     {row['order_date']}\n"
        f"Status:   {row['status']}\n"
        f"Total:    ${row['total_amount']:.2f}\n"
        f"Items:    {row['items']}"
    )}
