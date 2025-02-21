import os
import json
from typing import List, Dict
from dotenv import load_dotenv
from selenium.webdriver.chrome.options import Options

# Load environment variables from .env file
load_dotenv()

class Config:
    def __init__(self):
        self.accounts = self._load_accounts()
        self.twocaptcha_api_key = os.getenv('TWOCAPTCHA_API_KEY')
        self.email_config = {
            'username': os.getenv('EMAIL_USERNAME'),
            'password': os.getenv('EMAIL_PASSWORD'),
            'recipients': os.getenv('EMAIL_RECIPIENTS', '').split(',')
        }
        self.chrome_options = self._get_chrome_options()
        
        # Validate configuration
        self._validate_config()

    def _load_accounts(self) -> List[Dict]:
        """Load account information from environment variables"""
        accounts_json = os.getenv('LOYVERSE_ACCOUNTS')
        if not accounts_json:
            print("WARNING: No LOYVERSE_ACCOUNTS found in environment variables!")
            return []
            
        try:
            accounts = json.loads(accounts_json)
            print(f"Successfully loaded {len(accounts)} account(s)")
            return accounts
        except json.JSONDecodeError as e:
            print(f"Error parsing LOYVERSE_ACCOUNTS: {str(e)}")
            print(f"Raw LOYVERSE_ACCOUNTS value: {accounts_json[:100]}...")  # Print first 100 chars for debugging
            return []

    def _get_chrome_options(self) -> Options:
        """Configure Chrome options for both local and CI environments"""
        options = Options()
        
        # Basic options for both environments
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Chrome/97.0.4692.71')
        
        # Configure headless mode
        if os.environ.get("HEADLESS", "false").lower() == "true":
            options.add_argument('--headless=new')
            print("Running in headless mode")
        else:
            print("Running in visible mode")
            
        return options

    def _validate_config(self):
        """Validate configuration and print status"""
        print("\nConfiguration Status:")
        print("-" * 50)
        
        # Check accounts
        if not self.accounts:
            print("❌ No accounts configured")
        else:
            print(f"✓ {len(self.accounts)} account(s) configured")
            for account in self.accounts:
                print(f"  - {account.get('email', 'NO_EMAIL')}")
        
        # Check 2captcha
        if not self.twocaptcha_api_key:
            print("❌ No 2captcha API key configured")
        else:
            print("✓ 2captcha API key configured")
        
        # Check email configuration
        email_status = []
        if not self.email_config['username']:
            email_status.append("❌ No email username configured")
        if not self.email_config['password']:
            email_status.append("❌ No email password configured")
        if not self.email_config['recipients']:
            email_status.append("❌ No email recipients configured")
        
        if not email_status:
            print("✓ Email configuration complete")
        else:
            for status in email_status:
                print(status)
        
        print("-" * 50)