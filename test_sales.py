# test_sales.py
import sqlite3
from datetime import datetime

def test_sale():
    conn = sqlite3.connect('pharma.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Testing database connection and sales insertion...")
    
    # Check batches
    cursor.execute('SELECT id, batch_no, quantity FROM batches WHERE quantity > 0')
    batches = cursor.fetchall()
    print(f"\nAvailable batches:")
    for batch in batches:
        print(f"  Batch {batch['id']}: {batch['batch_no']} - {batch['quantity']} units")
    
    # Try to insert a sale
    test_data = {
        'batch_id': 1,  # Use your batch ID
        'quantity': 2,
        'price': 5.0,
        'customer': 'Test Customer',
        'phone': '1234567890'
    }
    
    print(f"\nTrying to insert sale for batch {test_data['batch_id']}...")
    
    try:
        # Check stock first
        cursor.execute('SELECT quantity FROM batches WHERE id = ?', (test_data['batch_id'],))
        stock = cursor.fetchone()
        if stock and stock['quantity'] >= test_data['quantity']:
            # Update stock
            cursor.execute('UPDATE batches SET quantity = quantity - ? WHERE id = ?',
                         (test_data['quantity'], test_data['batch_id']))
            
            # Insert sale
            cursor.execute('''
                INSERT INTO sales (batch_id, quantity_sold, selling_price, 
                                 customer_name, customer_phone, sold_on)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (test_data['batch_id'], test_data['quantity'], test_data['price'],
                  test_data['customer'], test_data['phone'], datetime.now()))
            
            conn.commit()
            
            # Get last sale
            cursor.execute('SELECT * FROM sales ORDER BY id DESC LIMIT 1')
            last_sale = cursor.fetchone()
            
            print(f"✅ Sale inserted successfully!")
            print(f"   Sale ID: {last_sale['id']}")
            print(f"   Batch ID: {last_sale['batch_id']}")
            print(f"   Quantity: {last_sale['quantity_sold']}")
            print(f"   Customer: {last_sale['customer_name']}")
            
            # Check updated stock
            cursor.execute('SELECT quantity FROM batches WHERE id = ?', (test_data['batch_id'],))
            new_stock = cursor.fetchone()
            print(f"   New stock for batch {test_data['batch_id']}: {new_stock['quantity']}")
        else:
            print(f"❌ Insufficient stock. Available: {stock['quantity'] if stock else 0}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    conn.close()

if __name__ == '__main__':
    test_sale()