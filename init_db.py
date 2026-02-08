# init_db.py
import sqlite3
from werkzeug.security import generate_password_hash

def init_database():
    conn = sqlite3.connect('pharma.db')
    cursor = conn.cursor()
    
    # Drop all existing tables (for clean start)
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS medicines')
    cursor.execute('DROP TABLE IF EXISTS batches')
    cursor.execute('DROP TABLE IF EXISTS sales')
    cursor.execute('DROP TABLE IF EXISTS alerts')
    cursor.execute('DROP TABLE IF EXISTS interactions')
    cursor.execute('DROP TABLE IF EXISTS audit_log')
    
    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'staff',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create medicines table
    cursor.execute('''
        CREATE TABLE medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            composition TEXT,
            uses TEXT,
            dosage TEXT,
            side_effects TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create batches table
    cursor.execute('''
        CREATE TABLE batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL,
            batch_no TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            mrp REAL NOT NULL,
            cost_price REAL NOT NULL,
            mfg_date DATE,
            expiry_date DATE NOT NULL,
            supplier TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines (id) ON DELETE CASCADE
        )
    ''')
    
    # Create sales table
    cursor.execute('''
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            quantity_sold INTEGER NOT NULL,
            selling_price REAL NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            customer_age INTEGER,
            prescription_number TEXT,
            doctor_name TEXT,
            diagnosis TEXT,
            payment_method TEXT DEFAULT 'cash',
            sold_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches (id)
        )
    ''')
    
    # Create alerts table - UPDATED WITH CORRECT COLUMNS
    cursor.execute('''
        CREATE TABLE alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            medicine_id INTEGER,
            batch_id INTEGER,
            priority TEXT DEFAULT 'medium',
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines (id),
            FOREIGN KEY (batch_id) REFERENCES batches (id)
        )
    ''')
    
    # Create interactions table
    cursor.execute('''
        CREATE TABLE interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_a TEXT NOT NULL,
            drug_b TEXT NOT NULL,
            interaction TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            recommendation TEXT
        )
    ''')
    
    # Create audit_log table
    cursor.execute('''
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            table_name TEXT,
            record_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX idx_medicines_name ON medicines(name)')
    cursor.execute('CREATE INDEX idx_batches_medicine ON batches(medicine_id)')
    cursor.execute('CREATE INDEX idx_batches_expiry ON batches(expiry_date)')
    cursor.execute('CREATE INDEX idx_sales_date ON sales(sold_on)')
    cursor.execute('CREATE INDEX idx_alerts_read ON alerts(is_read)')
    cursor.execute('CREATE INDEX idx_alerts_type ON alerts(alert_type)')
    
    # Insert default admin user
    admin_password = generate_password_hash('admin123')
    cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                  ('admin', admin_password, 'admin'))
    
    # Insert sample medicines
    sample_medicines = [
        ('Paracetamol', 'Acetaminophen 500mg', 'Fever, Pain relief', '500mg every 6 hours', 'Nausea, Liver damage', 'Analgesic'),
        ('Ibuprofen', 'Ibuprofen 400mg', 'Pain, Inflammation', '400mg every 8 hours', 'Stomach upset, Kidney issues', 'NSAID'),
        ('Amoxicillin', 'Amoxicillin 250mg', 'Bacterial infections', '250mg three times daily', 'Diarrhea, Rash', 'Antibiotic'),
        ('Cetirizine', 'Cetirizine 10mg', 'Allergies', '10mg once daily', 'Drowsiness, Dry mouth', 'Antihistamine'),
        ('Omeprazole', 'Omeprazole 20mg', 'Acidity, GERD', '20mg before breakfast', 'Headache, Nausea', 'PPI')
    ]
    
    cursor.executemany('''
        INSERT INTO medicines (name, composition, uses, dosage, side_effects, category)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_medicines)
    
    # Insert sample batches
    cursor.execute('SELECT id FROM medicines WHERE name = "Paracetamol"')
    paracetamol_id = cursor.fetchone()[0]
    
    cursor.execute('SELECT id FROM medicines WHERE name = "Ibuprofen"')
    ibuprofen_id = cursor.fetchone()[0]
    
    cursor.execute('SELECT id FROM medicines WHERE name = "Amoxicillin"')
    amoxicillin_id = cursor.fetchone()[0]
    
    sample_batches = [
        (paracetamol_id, 'BATCH001', 100, 5.0, 3.5, '2024-01-01', '2026-12-31', 'Sun Pharma'),
        (paracetamol_id, 'BATCH002', 50, 5.0, 3.5, '2024-02-01', '2025-06-30', 'Cipla'),
        (ibuprofen_id, 'BATCH003', 75, 8.0, 5.0, '2024-01-15', '2026-08-31', 'Mankind'),
        (amoxicillin_id, 'BATCH004', 60, 12.0, 8.0, '2024-03-01', '2025-03-31', 'Glaxo')
    ]
    
    cursor.executemany('''
        INSERT INTO batches (medicine_id, batch_no, quantity, mrp, cost_price, mfg_date, expiry_date, supplier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_batches)
    
    # Insert sample interactions
    sample_interactions = [
        ('Warfarin', 'Aspirin', 'Increased risk of bleeding', 'high', 'Monitor INR regularly if necessary.'),
        ('Warfarin', 'Ibuprofen', 'Increased risk of bleeding', 'high', 'Use paracetamol instead.'),
        ('Alcohol', 'Metronidazole', 'Disulfiram-like reaction', 'high', 'Avoid alcohol consumption.'),
        ('Aspirin', 'Ibuprofen', 'Reduced aspirin effectiveness', 'medium', 'Avoid NSAIDs.'),
        ('MAO Inhibitors', 'Tyramine-rich foods', 'Hypertensive crisis', 'high', 'Avoid aged meats, fermented foods.'),
        ('Lithium', 'Ibuprofen', 'Increased lithium levels', 'high', 'Monitor lithium levels.'),
        ('Clopidogrel', 'Omeprazole', 'Reduced clopidogrel effect', 'medium', 'Use alternative PPI like pantoprazole.'),
        ('ACE Inhibitors', 'Potassium supplements', 'Hyperkalemia', 'high', 'Monitor potassium.'),
        ('Simvastatin', 'Amiodarone', 'Increased myopathy risk', 'high', 'Use lower dose or alternative statin.'),
        ('Antibiotics', 'Oral contraceptives', 'Reduced contraceptive effect', 'medium', 'Use backup contraception during antibiotic course.'),
        ('Alcohol', 'Antihistamines', 'Increased drowsiness', 'medium', 'Avoid driving or operating machinery.'),
        ('Digoxin', 'Diuretics', 'Digoxin toxicity risk', 'high', 'Monitor for side effects.'),
        ('Tetracycline', 'Calcium supplements', 'Reduced absorption', 'medium', 'Take 2 hours before calcium.'),
        ('Heparin', 'Aspirin', 'Increased bleeding risk', 'high', 'Monitor for bleeding.')
    ]
    
    cursor.executemany('''
        INSERT INTO interactions (drug_a, drug_b, interaction, severity, recommendation)
        VALUES (?, ?, ?, ?, ?)
    ''', sample_interactions)
    
    # Create initial alerts
    cursor.execute('''
        INSERT INTO alerts (alert_type, message, medicine_id, priority, created_at)
        VALUES 
        ('low_stock', 'Paracetamol is running low (100 units left)', ?, 'medium', datetime('now', '-2 days')),
        ('expiry', 'Batch BATCH004 of Amoxicillin expires soon', ?, 'high', datetime('now', '-1 day'))
    ''', (paracetamol_id, amoxicillin_id))
    
    conn.commit()
    conn.close()
    
    print("✅ Database initialized successfully!")
    print("📋 Created tables: users, medicines, batches, sales, alerts, interactions, audit_log")
    print("👤 Default user: admin / admin123")
    print("💊 Sample data added")

if __name__ == '__main__':
    init_database()