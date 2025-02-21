import os
import time
import json
import requests
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from src.config import Config
from src.utils.captcha import solve_captcha
from src.utils.excel import create_workbook, setup_worksheet_formatting
from src.email_sender import send_report

class LoyverseScraper:
    def __init__(self, account: Dict, config: Config, excel_sheet):
        """Initialize scraper with account details and configuration"""
        self.email = account['email']
        self.password = account['password']
        self.invalid_outlets = account['invalid_outlets']
        self.config = config
        self.outputxls = excel_sheet
        self.fail_list = []
        self.name_ids = []
        self.output_lists = [["Outlet", "Internet Problem", "Sales Start", "Waffle End", "Sales End",
                            "9am", "10am", "11am", "12pm", "1pm", "2pm", "3pm", "4pm", "5pm",
                            "6pm", "7pm", "8pm", "9pm", "10pm"]]
        self.setup_driver()

    def setup_driver(self):
        """Set up browser driver with appropriate options for both local and CI environments"""
        try:
            # Determine if running in GitHub Actions
            is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
            
            # Set up browser options
            options = self.config.chrome_options
            
            if is_github_actions:
                # Configure for Chromium in GitHub Actions environment
                options.binary_location = '/usr/bin/chromium-browser'
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                
                # Use system ChromeDriver
                service = Service('/usr/bin/chromedriver')
            else:
                # Use webdriver_manager for local development
                service = Service(ChromeDriverManager().install())
            
            print("Setting up browser driver...")
            self.driver = webdriver.Chrome(
                service=service,
                options=options
            )
            print("Browser driver setup completed successfully")
            
        except Exception as e:
            print(f"Error setting up browser driver: {str(e)}")
            raise

    def login(self):
        """Handle login process including captcha if needed"""
        try:
            print(f"Logging in with account: {self.email}")
            # Start with the sales report URL as in original script
            self.driver.get('https://r.loyverse.com/dashboard/#/report/sales?page=0&limit=10&group=day&periodLength=7d&from=2021-06-04%2000:00:00&to=2021-06-10%2023:59:59&fromHour=0&toHour=0&outletsIds=all&merchantsIds=all')
            time.sleep(10)  # Wait as in original script
            
            self.driver.implicitly_wait(5)  # Add implicit wait from original
            
            if self.driver.current_url == 'https://loyverse.com/en/login':
                print("Login page detected, entering credentials...")
                # Handle login form
                try:
                    email_input = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, '//input[@id="mat-input-0"]'))
                    )
                    email_input.send_keys(self.email)
                    
                    password_input = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, '//input[@id="mat-input-1"]'))
                    )
                    password_input.send_keys(self.password)
                    
                    submit_button = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '//span[@id="sforg-submit"]'))
                    )
                    submit_button.click()
                    time.sleep(2)
                    
                    self.driver.implicitly_wait(5)
                    
                    # Check if still on login page - might need captcha
                    if self.driver.current_url == "https://loyverse.com/en/login":
                        print("Captcha detected, attempting to solve...")
                        solve_captcha(self.driver, self.config.twocaptcha_api_key)
                        
                    # After captcha, redirect back to dashboard
                    self.driver.get('https://r.loyverse.com/dashboard/#/report/sales?page=0&limit=10&group=day&periodLength=7d&from=2021-06-04%2000:00:00&to=2021-06-10%2023:59:59&fromHour=0&toHour=0&outletsIds=all&merchantsIds=all')
                    
                    # Verify we're actually logged in
                    if self.driver.current_url.startswith('https://r.loyverse.com/dashboard'):
                        print("Login successful!")
                        return True
                    else:
                        print("Login failed - Could not access dashboard")
                        return False
                        
                except Exception as e:
                    print(f"Error during login process: {str(e)}")
                    return False
            elif self.driver.current_url.startswith('https://r.loyverse.com/dashboard'):
                print("Already logged in!")
                return True
            else:
                print(f"Unexpected URL after login attempt: {self.driver.current_url}")
                return False
                
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
        
    def collect_store_name_id(self):
        """Collect store names and IDs"""
        time.sleep(10)
        name_ids = []
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        allsoup = soup.find_all('div', {'class': 'listCheckbox'})
        
        for each_element in allsoup[2:]:
            try:
                if each_element.text.strip() in self.invalid_outlets or each_element['id'] in self.invalid_outlets:
                    continue
                name_ids.append((each_element.text.strip(), each_element['id']))
            except Exception:
                pass
                
        self.name_ids = name_ids
        if not self.name_ids:
            print('No stores found, re-running login process...')
            self.login()
            self.collect_store_name_id()
        
        print(f'Total Stores = {len(self.name_ids)}.')
        if len(self.name_ids) < 1:
            print('Re-run...')
            self.driver.refresh()
            self.login()
            self.collect_store_name_id()

    def request_earnings_receipt(self, startdate: str, enddate: str, outletID: Tuple[str, str]):
        """Get earnings receipt data"""
        headers = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://r.loyverse.com',
            'Referer': 'https://r.loyverse.com/dashboard/',
            'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
            'sec-ch-ua-platform': "Windows",
            'cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36'
        }
        
        payload = {
            "limit": "200",
            "offset": 0,
            "receiptType": None,
            "payType": None,
            "startDate": f"{startdate} 00:00:00",
            "endDate": f"{enddate} 23:59:59",
            "search": None,
            "tzOffset": 28800000,
            "tzName": "Asia/Kuala_Lumpur",
            "startTime": None,
            "endTime": None,
            "startWeek": 0,
            "receiptId": None,
            "predefinedPeriod": {"name": None, "period": None},
            "customPeriod": True,
            "merchantsIds": "all",
            "outletsIds": [outletID[1]],
            'payType': None
        }

        earnings_request = self.req.post('https://r.loyverse.com/data/ownercab/getreceiptsarchive', 
                                       headers=headers, data=json.dumps(payload))
        earnings_rows = json.loads(earnings_request.content).get('receipts', [])
        
        try:
            if earnings_rows:
                first_sale_timestamp = earnings_rows[-1]['dateTS']
                last_sale_timestamp = earnings_rows[0]['dateTS']
                first_sale = datetime.fromtimestamp(int(first_sale_timestamp) / 1000).strftime("%I:%M %p")
                last_sale = datetime.fromtimestamp(int(last_sale_timestamp) / 1000).strftime("%I:%M %p")
            else:
                first_sale = None
                last_sale = None
        except Exception as e:
            print(f"Error processing receipt timestamps: {e}")
            first_sale, last_sale = None, None

        earnings_rows.reverse()
        self.headers = headers
        return first_sale, last_sale

    def request_earnings_report(self, startdate: str, enddate: str, outletID: Tuple[str, str]):
        """Get earnings report data"""
        headers = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://r.loyverse.com',
            'Referer': 'https://r.loyverse.com/dashboard/',
            'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
            'sec-ch-ua-platform': "Windows",
            'cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36'
        }
        
        payload = {
            "merchantsIds": "all",
            "outletsIds": [outletID[1]],
            "startDate": f"{startdate} 00:00:00",
            "endDate": f"{enddate} 23:59:59",
            "startWeek": 0,
            "tzOffset": 28800000,
            "tzName": "Asia/Kuala_Lumpur",
            "startTime": None,
            "endTime": None,
            "customPeriod": True,
            "predefinedPeriod": {"name": None, "period": None},
            "divider": "hour",
            "limit": "10",
            "offset": 0
        }

        earnings_request = self.req.post('https://r.loyverse.com/data/ownercab/getearningsreport', 
                                       headers=headers, data=json.dumps(payload))
        print(f"Earnings request status for {outletID[0]}: {earnings_request.status_code}")
        
        if earnings_request.status_code != 200:
            self.fail_list.append(outletID)
            return None
            
        earnings_rows = json.loads(earnings_request.content).get('earningsRows', [])
        sales_list = [row['earningsSum'] / 100 for row in earnings_rows[9:23]]
        self.headers = headers
        return sales_list

    def collect_waffle_end_time(self, outletID):
        """Get waffle end time"""
        req = self.req
        headers = self.headers
        payload = {
            "startDate": f"{self.start_date} 00:00:00",
            "endDate": f"{self.end_date} 23:59:59",
            "startWeek": 0,
            "tzOffset": 28800000,
            "tzName": "Asia/Kuala_Lumpur",
            "startTime": None,
            "endTime": None,
            "divider": "hour",
            "offset": 0,
            "limit": "10",
            "merchantsIds": "all",
            "outletsIds": [outletID[1]],
            "predefinedPeriod": {"name": None, "period": None},
            "customPeriod": True
        }

        top_items_request = req.post('https://r.loyverse.com/data/ownercab/getwaresreport', 
                                   headers=headers, data=json.dumps(payload))
        top5_dict = json.loads(top_items_request.content)
        top5 = top5_dict.get('top5', [])
        
        waffle_end_time = None
        for each in top5:
            if each["name"] in ["C1 Original Waffle", "C001 Classic Waffle"]:
                waffle_id = each["id"]
                periodsByWare = top5_dict.get("periodsByWare", [])
                waffleInfoList = []
                for pbw in periodsByWare:
                    if pbw['wareId'] == waffle_id:
                        waffleInfoList = pbw.get("periodsByWare", [])
                        waffleInfoList.reverse()
                        break
                for info in waffleInfoList:
                    if info.get('netSales', 0) > 0:
                        waffleEndTime_dict = info
                        break
                to_time = waffleEndTime_dict.get("to")
                pre_add_time = datetime.fromtimestamp(int(to_time) / 1000)
                waffle_end_time = (pre_add_time + timedelta(seconds=1)).strftime("%I:%M %p")
                break
        
        return waffle_end_time

    def all_earnings_report(self, nameID):
        """Process all earnings data for a store"""
        print(f'Scraping {nameID[0]}...')
        sales_list = self.request_earnings_report(self.start_date, self.end_date, nameID)
        first_sale, last_sale = self.request_earnings_receipt(self.start_date, self.end_date, nameID)
        
        if sales_list is not None:
            waffle_end_time = self.collect_waffle_end_time(nameID)
            print(nameID[0], nameID[1], first_sale, waffle_end_time, last_sale, sales_list)
            self.file_writting_list_creation(nameID[0], first_sale, waffle_end_time, last_sale, sales_list)

    def file_writting_list_creation(self, storename, first_sale, waffle_end_time, last_sale, sales_list):
        """Create output list for Excel writing"""
        if len(set(sales_list)) == 1:
            output_list_single = [storename, "Alert", first_sale, waffle_end_time, last_sale]
        else:
            output_list_single = [storename, None, first_sale, waffle_end_time, last_sale]
        output_list_single.extend(sales_list)
        print("Output list for", storename, ":", output_list_single)
        self.output_lists.append(output_list_single)

    def file_writting(self):
        """Write data to Excel"""
        row, column = 0, 0
        for each_line in self.output_lists:
            for item in each_line:
                self.outputxls.write(row, column, item)
                column += 1
            row += 1
            column = 0

    def get_earnings_report(self):
        """Main method to get all earnings reports"""
        self.driver.get('https://r.loyverse.com/dashboard/#/report/sales?page=0&limit=10&group=day&periodLength=7d&from=2022-01-24%2000:00:00&to=2022-01-30%2023:59:59&fromHour=0&toHour=0&outletsIds=all&merchantsIds=all')
        
        # Setup request session
        cookies_chrome = self.driver.get_cookies()
        req = requests.session()
        for cookie in cookies_chrome:
            req.cookies.set(cookie['name'], cookie['value'])
        self.req = req
        
        time.sleep(5)
        
        # Get cookie for API requests
        for request in self.driver.requests:
            if request.response and request.url == 'https://r.loyverse.com/data/ownercab/getearningsreport':
                self.cookie = request.headers.get('cookie')
        
        # Process all stores with threading
        with ThreadPoolExecutor(max_workers=10) as executor:
            for nameID in self.name_ids:
                executor.submit(self.all_earnings_report, nameID)

    def main(self):
        """Main execution method"""
        self.login()
        self.collect_store_name_id()
        self.get_earnings_report()
        self.file_writting()
        self.driver.close()
        self.driver.quit()
        time.sleep(2)
        print("Fail List:", self.fail_list)

def main():
    """Main function to run the scraper"""
    try:
        config = Config()
        
        # Set up dates
        today = date.today()
        yesterday = today - timedelta(days=1)
        report_date = str(yesterday)
        
        # Create Excel workbook
        workbook_name = f"barHarian_{report_date}.xlsx"
        workbook = create_workbook(workbook_name)
        
        # Process each account
        for account in config.accounts:
            try:
                print(f"\nProcessing account: {account['email']}")
                
                # Create worksheet
                worksheet = workbook.add_worksheet(account['email'].split('@')[0])
                
                # Setup worksheet formatting
                setup_worksheet_formatting(workbook, worksheet)
                
                # Initialize scraper
                scraper = LoyverseScraper(account, config, worksheet)
                scraper.start_date = report_date
                scraper.end_date = report_date
                
                # Run scraper
                scraper.main()
                
            except Exception as e:
                print(f"Error processing account {account['email']}: {str(e)}")
                continue
        
        # Close workbook
        workbook.close()
        
        # Send report
        if os.path.isfile(workbook_name):
            send_report(workbook_name, config.email_config)
        else:
            print(f"Report file not found: {workbook_name}")
            
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    start_time = time.time()
    print(f"Start time {datetime.now()} ...")
    main()
    print("--- %s minutes ---" % ((time.time() - start_time) // 60))