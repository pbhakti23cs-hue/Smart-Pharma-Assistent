import sqlite3
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from typing import List, Dict, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('expiry_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PharmaAlertSystem:
    """Pharmaceutical expiry and stock alert system"""
    
    def __init__(self, db_path='pharma.db'):
        self.db_path = db_path
        self.config = self.load_config()
        
    def load_config(self):
        """Load configuration from file or environment"""
        config_path = 'alert_config.json'
        default_config = {
            'low_stock_threshold': 20,
            'near_expiry_days': 15,
            'expiring_soon_days': 90,
            'email_alerts': False,
            'email_settings': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'sender_email': '',
                'sender_password': '',
                'recipient_emails': []
            }
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                try:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
                except json.JSONDecodeError:
                    logger.warning("Invalid config file, using defaults")
        
        return default_config
    
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def check_expired_batches(self) -> List[Dict]:
        """Check for expired batches"""
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        today = datetime.now().date()
        
        cur.execute('''
            SELECT b.id, b.batch_no, b.expiry_date, b.quantity, b.mrp,
                   m.name as medicine_name, m.category,
                   DATEDIFF(b.expiry_date, DATE('now')) as days_expired
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.id
            WHERE b.expiry_date < DATE('now')
            AND b.id NOT IN (
                SELECT batch_id FROM alerts 
                WHERE alert_type = 'expiry' 
                AND severity = 'danger'
                AND DATE(created_at) = DATE('now')
            )
            ORDER BY b.expiry_date DESC
        ''')
        
        expired_batches = [dict(row) for row in cur.fetchall()]
        conn.close()
        
        logger.info(f"Found {len(expired_batches)} expired batches")
        return expired_batches
    
    def check_near_expiry_batches(self) -> List[Dict]:
        """Check for batches expiring soon"""
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        near_threshold = (datetime.now() + 
                         timedelta(days=self.config['near_expiry_days'])).date()
        today = datetime.now().date()
        
        cur.execute('''
            SELECT b.id, b.batch_no, b.expiry_date, b.quantity, b.mrp,
                   m.name as medicine_name, m.category,
                   DATEDIFF(b.expiry_date, DATE('now')) as days_until_expiry
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.id
            WHERE b.expiry_date <= ? AND b.expiry_date >= ?
            AND b.id NOT IN (
                SELECT batch_id FROM alerts 
                WHERE alert_type = 'expiry' 
                AND severity = 'warning'
                AND DATE(created_at) = DATE('now')
            )
            ORDER BY b.expiry_date
        ''', (near_threshold.isoformat(), today.isoformat()))
        
        near_expiry_batches = [dict(row) for row in cur.fetchall()]
        conn.close()
        
        logger.info(f"Found {len(near_expiry_batches)} near-expiry batches")
        return near_expiry_batches
    
    def check_expiring_soon_batches(self) -> List[Dict]:
        """Check for batches expiring in 90 days"""
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        soon_threshold = (datetime.now() + 
                         timedelta(days=self.config['expiring_soon_days'])).date()
        
        cur.execute('''
            SELECT b.id, b.batch_no, b.expiry_date, b.quantity, b.mrp,
                   m.name as medicine_name, m.category,
                   DATEDIFF(b.expiry_date, DATE('now')) as days_until_expiry
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.id
            WHERE b.expiry_date <= ? AND b.expiry_date > DATE('now', '+15 days')
            AND b.id NOT IN (
                SELECT batch_id FROM alerts 
                WHERE alert_type = 'expiry' 
                AND severity = 'info'
                AND DATE(created_at) = DATE('now')
            )
            ORDER BY b.expiry_date
        ''', (soon_threshold.isoformat(),))
        
        expiring_soon_batches = [dict(row) for row in cur.fetchall()]
        conn.close()
        
        logger.info(f"Found {len(expiring_soon_batches)} batches expiring soon")
        return expiring_soon_batches
    
    def check_low_stock_batches(self) -> List[Dict]:
        """Check for low stock batches"""
        conn = self.get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT b.id, b.batch_no, b.quantity, b.mrp,
                   m.name as medicine_name, m.category,
                   (SELECT SUM(quantity) FROM batches b2 
                    WHERE b2.medicine_id = b.medicine_id) as total_stock
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.id
            WHERE b.quantity < ?
            AND b.id NOT IN (
                SELECT batch_id FROM alerts 
                WHERE alert_type = 'low_stock'
                AND DATE(created_at) = DATE('now')
            )
            ORDER BY b.quantity
        ''', (self.config['low_stock_threshold'],))
        
        low_stock_batches = [dict(row) for row in cur.fetchall()]
        conn.close()
        
        logger.info(f"Found {len(low_stock_batches)} low stock batches")
        return low_stock_batches
    
    def create_alerts(self, batch_type: str, batches: List[Dict], severity: str):
        """Create alerts in database"""
        if not batches:
            return 0
        
        conn = self.get_db_connection()
        cur = conn.cursor()
        alerts_created = 0
        
        for batch in batches:
            if batch_type == 'expired':
                message = f'🚨 EXPIRED: {batch["medicine_name"]} (Batch: {batch["batch_no"]}) - Expired {abs(batch["days_expired"])} days ago'
                alert_type = 'expiry'
            elif batch_type == 'near_expiry':
                message = f'⚠️  Near expiry: {batch["medicine_name"]} (Batch: {batch["batch_no"]}) expires in {batch["days_until_expiry"]} days'
                alert_type = 'expiry'
            elif batch_type == 'expiring_soon':
                message = f'ℹ️  Expiring soon: {batch["medicine_name"]} (Batch: {batch["batch_no"]}) expires in {batch["days_until_expiry"]} days'
                alert_type = 'expiry'
                severity = 'info'
            elif batch_type == 'low_stock':
                message = f'📉 Low stock: {batch["medicine_name"]} (Batch: {batch["batch_no"]}) - Only {batch["quantity"]} units left (Total: {batch["total_stock"]})'
                alert_type = 'low_stock'
            else:
                continue
            
            try:
                cur.execute('''
                    INSERT INTO alerts (batch_id, alert_type, message, severity)
                    VALUES (?, ?, ?, ?)
                ''', (batch['id'], alert_type, message, severity))
                alerts_created += 1
                
                logger.debug(f"Created alert: {message}")
                
            except sqlite3.IntegrityError:
                # Alert might already exist
                continue
        
        conn.commit()
        conn.close()
        
        return alerts_created
    
    def send_email_alerts(self, alerts_summary: Dict):
        """Send email alerts if configured"""
        if not self.config['email_alerts']:
            return
        
        email_settings = self.config['email_settings']
        if not all([email_settings['sender_email'], 
                   email_settings['sender_password'], 
                   email_settings['recipient_emails']]):
            logger.warning("Email settings incomplete, skipping email alerts")
            return
        
        try:
            # Create email content
            subject = f"Pharma Alert Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .header {{ background: #1565C0; color: white; padding: 20px; border-radius: 5px; }}
                    .alert-box {{ margin: 10px 0; padding: 15px; border-radius: 5px; }}
                    .danger {{ background: #FFEBEE; border-left: 5px solid #F44336; }}
                    .warning {{ background: #FFF3CD; border-left: 5px solid #FFC107; }}
                    .info {{ background: #E3F2FD; border-left: 5px solid #2196F3; }}
                    .summary {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>📊 Smart Pharma Assistant - Daily Alert Report</h2>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="summary">
                    <h3>📈 Summary</h3>
                    <p>• Expired batches: {alerts_summary['expired']}</p>
                    <p>• Near expiry batches (≤{self.config['near_expiry_days']} days): {alerts_summary['near_expiry']}</p>
                    <p>• Low stock batches (<{self.config['low_stock_threshold']} units): {alerts_summary['low_stock']}</p>
                    <p>• Total alerts created: {alerts_summary['total']}</p>
                </div>
                
                <h3>🚨 Action Required</h3>
                <p>Please review the following alerts and take appropriate action:</p>
                
                <h4>Expired Batches (Require Immediate Disposal):</h4>
                {"".join([f'<div class="alert-box danger">{alert}</div>' 
                         for alert in alerts_summary.get('expired_alerts', [])])}
                
                <h4>Near Expiry Batches (Review Required):</h4>
                {"".join([f'<div class="alert-box warning">{alert}</div>' 
                         for alert in alerts_summary.get('near_expiry_alerts', [])])}
                
                <h4>Low Stock Batches (Restock Required):</h4>
                {"".join([f'<div class="alert-box info">{alert}</div>' 
                         for alert in alerts_summary.get('low_stock_alerts', [])])}
                
                <br>
                <p><strong>Note:</strong> This is an automated alert system. 
                Please log into the Smart Pharma Assistant for detailed reports.</p>
                <p>Login: <a href="http://127.0.0.1:5000">http://127.0.0.1:5000</a></p>
            </body>
            </html>
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = email_settings['sender_email']
            msg['To'] = ', '.join(email_settings['recipient_emails'])
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(email_settings['smtp_server'], 
                            email_settings['smtp_port']) as server:
                server.starttls()
                server.login(email_settings['sender_email'], 
                           email_settings['sender_password'])
                server.send_message(msg)
            
            logger.info("Email alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def generate_report(self, alerts_summary: Dict) -> str:
        """Generate a detailed report"""
        report_lines = [
            "=" * 60,
            "📊 SMART PHARMA ASSISTANT - ALERT REPORT",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "📈 SUMMARY",
            "-" * 40,
            f"• Expired batches: {alerts_summary['expired']}",
            f"• Near expiry batches (≤{self.config['near_expiry_days']} days): {alerts_summary['near_expiry']}",
            f"• Expiring soon batches (≤{self.config['expiring_soon_days']} days): {alerts_summary['expiring_soon']}",
            f"• Low stock batches (<{self.config['low_stock_threshold']} units): {alerts_summary['low_stock']}",
            f"• Total alerts created: {alerts_summary['total']}",
            "",
            "🚨 DETAILED ALERTS",
            "=" * 60,
        ]
        
        # Add expired batches
        if alerts_summary['expired_alerts']:
            report_lines.append("\n🔴 EXPIRED BATCHES (IMMEDIATE ACTION REQUIRED):")
            report_lines.append("-" * 50)
            for alert in alerts_summary['expired_alerts']:
                report_lines.append(f"  • {alert}")
        
        # Add near expiry batches
        if alerts_summary['near_expiry_alerts']:
            report_lines.append("\n🟡 NEAR EXPIRY BATCHES (REVIEW REQUIRED):")
            report_lines.append("-" * 50)
            for alert in alerts_summary['near_expiry_alerts']:
                report_lines.append(f"  • {alert}")
        
        # Add low stock batches
        if alerts_summary['low_stock_alerts']:
            report_lines.append("\n🔵 LOW STOCK BATCHES (RESTOCK RECOMMENDED):")
            report_lines.append("-" * 50)
            for alert in alerts_summary['low_stock_alerts']:
                report_lines.append(f"  • {alert}")
        
        report_lines.extend([
            "",
            "=" * 60,
            "💡 RECOMMENDED ACTIONS:",
            "-" * 60,
            "1. Dispose expired batches immediately following safety guidelines",
            "2. Prioritize sale of near-expiry batches",
            "3. Create restock orders for low stock items",
            "4. Review expiring soon batches in weekly planning",
            "",
            "📱 For detailed reports and management, log into the system:",
            "   http://127.0.0.1:5000",
            "=" * 60,
        ])
        
        return "\n".join(report_lines)
    
    def run_checks(self):
        """Run all checks and generate alerts"""
        logger.info("🔄 Running automated expiry and stock checks...")
        print("=" * 60)
        
        # Run checks
        expired_batches = self.check_expired_batches()
        near_expiry_batches = self.check_near_expiry_batches()
        expiring_soon_batches = self.check_expiring_soon_batches()
        low_stock_batches = self.check_low_stock_batches()
        
        # Create alerts
        expired_alerts = self.create_alerts('expired', expired_batches, 'danger')
        near_expiry_alerts = self.create_alerts('near_expiry', near_expiry_batches, 'warning')
        expiring_soon_alerts = self.create_alerts('expiring_soon', expiring_soon_batches, 'info')
        low_stock_alerts = self.create_alerts('low_stock', low_stock_batches, 'warning')
        
        total_alerts = (expired_alerts + near_expiry_alerts + 
                       expiring_soon_alerts + low_stock_alerts)
        
        # Prepare summary
        alerts_summary = {
            'expired': len(expired_batches),
            'near_expiry': len(near_expiry_batches),
            'expiring_soon': len(expiring_soon_batches),
            'low_stock': len(low_stock_batches),
            'total': total_alerts,
            'expired_alerts': [f'{b["medicine_name"]} (Batch: {b["batch_no"]}) - Expired {abs(b["days_expired"])} days ago' 
                             for b in expired_batches],
            'near_expiry_alerts': [f'{b["medicine_name"]} (Batch: {b["batch_no"]}) - Expires in {b["days_until_expiry"]} days' 
                                 for b in near_expiry_batches],
            'low_stock_alerts': [f'{b["medicine_name"]} (Batch: {b["batch_no"]}) - {b["quantity"]} units left' 
                               for b in low_stock_batches]
        }
        
        # Print report
        report = self.generate_report(alerts_summary)
        print(report)
        
        # Save report to file
        report_filename = f"alert_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to: {report_filename}")
        
        # Send email alerts if configured
        if self.config['email_alerts'] and total_alerts > 0:
            self.send_email_alerts(alerts_summary)
        
        return alerts_summary

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "low_stock_threshold": 20,
        "near_expiry_days": 15,
        "expiring_soon_days": 90,
        "email_alerts": False,
        "email_settings": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "your-email@gmail.com",
            "sender_password": "your-app-password",
            "recipient_emails": ["pharmacist@yourpharmacy.com", "manager@yourpharmacy.com"]
        }
    }
    
    with open('alert_config.json', 'w') as f:
        json.dump(sample_config, f, indent=4)
    
    print("✅ Created sample configuration file: alert_config.json")
    print("⚠️  Please update the email settings before enabling email alerts")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Pharmaceutical Expiry and Stock Alert System')
    parser.add_argument('--config', action='store_true', 
                       help='Create sample configuration file')
    parser.add_argument('--db', default='pharma.db', 
                       help='Database file path (default: pharma.db)')
    
    args = parser.parse_args()
    
    if args.config:
        create_sample_config()
    else:
        try:
            if not os.path.exists(args.db):
                print(f"❌ Database file '{args.db}' not found!")
                print("   Please run init_db.py first to create the database.")
                exit(1)
            
            alert_system = PharmaAlertSystem(db_path=args.db)
            alert_system.run_checks()
            
            print("\n" + "=" * 60)
            print("💡 SCHEDULING TIPS:")
            print("=" * 60)
            print("Windows Task Scheduler:")
            print("  1. Open Task Scheduler")
            print("  2. Create Basic Task")
            print("  3. Set trigger to 'Daily'")
            print("  4. Set time (e.g., 8:00 AM)")
            print("  5. Action: Start a program")
            print("  6. Program: python.exe")
            print("  7. Arguments: expiry_check.py")
            print("  8. Start in: [path to your project]")
            print("\nLinux/Mac Cron Job:")
            print("  Add to crontab (crontab -e):")
            print("  0 8 * * * cd /path/to/project && python expiry_check.py")
            print("\nHeroku Scheduler (for cloud):")
            print("  1. Install Heroku Scheduler addon")
            print("  2. Add job: python expiry_check.py")
            print("  3. Set frequency to 'Daily'")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Check interrupted by user.")
        except Exception as e:
            logger.error(f"Error running checks: {e}")
            print(f"\n❌ Error: {e}")
            print("\n🔧 Troubleshooting:")
            print("  1. Ensure database exists: python init_db.py")
            print("  2. Check file permissions")
            print("  3. Verify database schema")