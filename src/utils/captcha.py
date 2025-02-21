import time
import re
from bs4 import BeautifulSoup
from twocaptcha import TwoCaptcha
from selenium.webdriver.remote.webdriver import WebDriver

def solve_captcha(driver: WebDriver, api_key: str) -> bool:
    """
    Solve reCAPTCHA using 2captcha service
    
    Args:
        driver: Selenium WebDriver instance
        api_key: 2captcha API key
    
    Returns:
        bool: True if captcha solved successfully
    """
    try:
        print("Solving Captcha...")
        time.sleep(10)  # Wait for captcha to load
        
        solver = TwoCaptcha(api_key)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Find captcha iframe
        iframe = soup.find('iframe', {'title': 'recaptcha challenge expires in two minutes'})
        if not iframe:
            print("Captcha iframe not found!")
            return False
            
        recaptcha_url = iframe.get('src')
        print("Recaptcha iframe src:", recaptcha_url)
        
        # Extract site key
        key_match = re.search("&k=([^&]+)", recaptcha_url)
        if not key_match:
            print("Site key not found in captcha iframe!")
            return False
            
        site_key = key_match.group(1)
        
        # Solve captcha
        result = solver.recaptcha(
            sitekey=site_key,
            url=driver.current_url,
            invisible=1,
            enterprise=0
        )
        
        captcha_response = result.get('code')
        if not captcha_response:
            print("No captcha solution received!")
            return False
            
        print("Captcha solved, injecting solution...")
        
        # Inject solution
        set_token_js = """
        var recaptchaResponse = document.getElementById("g-recaptcha-response");
        if (recaptchaResponse) {
            recaptchaResponse.innerHTML = arguments[0];
            recaptchaResponse.value = arguments[0];
            var event = new Event('change', { bubbles: true });
            recaptchaResponse.dispatchEvent(event);
        }
        """
        driver.execute_script(set_token_js, captcha_response)
        time.sleep(5)
        
        # Find and execute callback
        find_clients_js = """
        function findRecaptchaClients() {
            if (typeof (___grecaptcha_cfg) !== 'undefined') {
                return Object.entries(___grecaptcha_cfg.clients).map(([cid, client]) => {
                    const data = { id: cid, version: cid >= 10000 ? 'V3' : 'V2' };
                    const objects = Object.entries(client).filter(([_, value]) => value && typeof value === 'object');
                    objects.forEach(([toplevelKey, toplevel]) => {
                        const found = Object.entries(toplevel).find(([_, value]) => (
                            value && typeof value === 'object' && 'sitekey' in value && 'size' in value
                        ));
                        if (typeof toplevel === 'object' && toplevel instanceof HTMLElement && toplevel['tagName'] === 'DIV'){
                            data.pageurl = toplevel.baseURI;
                        }
                        if (found) {
                            const [sublevelKey, sublevel] = found;
                            data.sitekey = sublevel.sitekey;
                            const callbackKey = data.version === 'V2' ? 'callback' : 'promise-callback';
                            const callback = sublevel[callbackKey];
                            if (!callback) {
                                data.callback = null;
                                data.function = null;
                            } else {
                                data.function = callback;
                                const keys = [cid, toplevelKey, sublevelKey, callbackKey].map((key) => "['" + key + "']").join('');
                                data.callback = "___grecaptcha_cfg.clients" + keys;
                            }
                        }
                    });
                    return data;
                });
            }
            return [];
        }
        return findRecaptchaClients();
        """
        clients = driver.execute_script(find_clients_js)
        
        callback = None
        for client in clients:
            if client.get("sitekey") == site_key and client.get("callback"):
                callback = client.get("callback")
                break
                
        if callback:
            driver.execute_script(f"{callback}('{captcha_response}');")
            time.sleep(4)
            return True
        else:
            print("No matching callback found")
            return False
            
    except Exception as e:
        print(f"Error solving captcha: {str(e)}")
        return False