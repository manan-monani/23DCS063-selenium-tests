# Practical 2 - UI automation using Selenium WebDriver (Python)
# Application under test: Gem Store demo web app (login -> catalogue -> contact form)
import unittest, time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:8000/index.html"
SHOTS = "screens"
os.makedirs(SHOTS, exist_ok=True)

class GemStoreTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        opts = Options()
        opts.add_argument("--window-size=1100,650")
        # (headless flags only needed because this machine has no display)
        for a in CHROME_FLAGS: opts.add_argument(a)
        if CHROME_BIN: opts.binary_location = CHROME_BIN
        cls.driver = webdriver.Chrome(service=Service(DRIVER_PATH) if DRIVER_PATH else None, options=opts)
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def snap(self, name):
        self.driver.save_screenshot(f"{SHOTS}/{name}.png")

    def test_1_login_page_opens(self):
        d = self.driver
        d.get(BASE_URL)
        self.assertEqual(d.title, "Gem Store - Login")
        self.snap("01_login_page")

    def test_2_invalid_login_shows_error(self):
        d = self.driver
        d.get(BASE_URL)
        d.find_element(By.ID, "username").send_keys("student")
        d.find_element(By.ID, "password").send_keys("wrongpass")
        d.find_element(By.ID, "loginBtn").click()
        msg = d.find_element(By.ID, "message").text
        self.assertEqual(msg, "Invalid username or password")
        self.snap("02_invalid_login")

    def test_3_valid_login_and_navigation(self):
        d = self.driver
        d.get(BASE_URL)
        d.find_element(By.ID, "username").send_keys("student")
        d.find_element(By.ID, "password").send_keys("test123")
        d.find_element(By.ID, "loginBtn").click()
        self.wait.until(EC.url_contains("shop.html"))
        self.assertIn("Welcome, student", d.find_element(By.ID, "welcome").text)
        self.snap("03_catalogue_after_login")
        # navigate to the contact page using the menu link
        d.find_element(By.LINK_TEXT, "Contact").click()
        self.wait.until(EC.title_is("Gem Store - Contact"))
        self.assertTrue(d.current_url.endswith("contact.html"))

    def test_4_empty_form_validation(self):
        d = self.driver
        d.get(d.current_url)
        d.find_element(By.ID, "submitBtn").click()
        self.assertEqual(d.find_element(By.ID, "result").text, "All fields are required")
        self.snap("04_form_validation")

    def test_5_form_submission(self):
        d = self.driver
        d.get(d.current_url)
        d.find_element(By.ID, "name").send_keys("Manan")
        d.find_element(By.ID, "email").send_keys("manan@example.com")
        d.find_element(By.ID, "msg").send_keys("Please share the new ring catalogue.")
        self.snap("05_form_filled")
        d.find_element(By.ID, "submitBtn").click()
        text = d.find_element(By.ID, "result").text
        self.assertEqual(text, "Thank you Manan, your message has been submitted.")
        self.snap("06_form_submitted")

    def test_6_logout_blocks_catalogue(self):
        d = self.driver
        d.find_element(By.LINK_TEXT, "Logout").click()
        self.wait.until(EC.title_is("Gem Store - Login"))
        d.get("http://localhost:8000/shop.html")      # try to open protected page directly
        self.wait.until(EC.title_is("Gem Store - Login"))
        self.snap("07_after_logout")

# ---- browser settings for this run ----
CHROME_FLAGS = ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage"]
CHROME_BIN = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
DRIVER_PATH = "/usr/local/lib/python3.13/dist-packages/chromedriver_py/chromedriver_linux64"

if __name__ == "__main__":
    unittest.main(verbosity=2)
