import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict

def send_report(file_path: str, email_config: Dict) -> bool:
    """Send Excel report via email"""
    try:
        if not os.path.isfile(file_path):
            print(f"Cannot read the file {file_path}!")
            return False

        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_config['username']
        msg['To'] = ', '.join(email_config['recipients'])
        msg['Subject'] = f"Loyverse Daily Report - {os.path.basename(file_path)}"

        # Add body
        body = "Please find attached the daily Loyverse report."
        msg.attach(MIMEText(body, 'plain'))

        # Attach file
        with open(file_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype='xlsx')
            attachment.add_header('Content-Disposition', 'attachment', 
                                filename=os.path.basename(file_path))
            msg.attach(attachment)

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)

        print(f"Report {os.path.basename(file_path)} sent successfully")
        return True

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False