# Practical 3 - Cross Browser Testing using Selenium
# Runs the same test script on Chrome, Edge and Firefox against the Gem Store demo web app
# and compares the results. Screenshots + a summary table are saved in the "results" folder.
import os, sys, json, time, threading, functools, argparse, http.server, socketserver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "demoapp")
OUT_DIR = os.path.join(HERE, "results")

# ---------- tiny local web server for the demo app ----------
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def start_server():
    handler = functools.partial(QuietHandler, directory=APP_DIR)
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]

# ---------- driver creation ----------
def make_driver(name, headless):
    if name == "chrome":
        o = webdriver.ChromeOptions()
        if headless: o.add_argument("--headless=new"); o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage")
        if os.environ.get("CHROME_BIN"): o.binary_location = os.environ["CHROME_BIN"]
        svc = None
        if os.environ.get("CHROMEDRIVER"):
            from selenium.webdriver.chrome.service import Service
            svc = Service(os.environ["CHROMEDRIVER"])
        d = webdriver.Chrome(options=o, service=svc) if svc else webdriver.Chrome(options=o)
    elif name == "edge":
        o = webdriver.EdgeOptions()
        if headless: o.add_argument("--headless=new")
        d = webdriver.Edge(options=o)
    elif name == "firefox":
        o = webdriver.FirefoxOptions()
        if headless: o.add_argument("-headless")
        d = webdriver.Firefox(options=o)
    else:
        raise ValueError(name)
    d.set_window_size(1100, 720)
    return d

# ---------- the test steps (same script for every browser) ----------
def run_steps(d, base, shots):
    results = []
    wait = WebDriverWait(d, 10)
    def step(label, fn, shot):
        try:
            fn(); status = "PASS"; note = ""
        except Exception as e:
            status = "FAIL"; note = str(e).splitlines()[0][:120]
        d.save_screenshot(os.path.join(shots, shot + ".png"))
        results.append((label, status, note))

    def s1():
        d.get(base + "/index.html")
        assert d.title == "Gem Store - Login", d.title
    def s2():
        d.find_element(By.ID, "username").send_keys("student")
        d.find_element(By.ID, "password").send_keys("wrongpass")
        d.find_element(By.ID, "loginBtn").click()
        assert d.find_element(By.ID, "message").text == "Invalid username or password"
    def s3():
        d.get(base + "/index.html")
        d.find_element(By.ID, "username").send_keys("student")
        d.find_element(By.ID, "password").send_keys("test123")
        d.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("shop.html"))
        assert "Welcome, student" in d.find_element(By.ID, "welcome").text
    def s4():
        d.find_element(By.LINK_TEXT, "Contact").click()
        wait.until(EC.title_is("Gem Store - Contact"))
    def s5():
        d.find_element(By.ID, "submitBtn").click()
        assert d.find_element(By.ID, "result").text == "All fields are required"
    def s6():
        d.find_element(By.ID, "name").send_keys("Manan")
        d.find_element(By.ID, "email").send_keys("manan@example.com")
        d.find_element(By.ID, "msg").send_keys("Please share the new ring catalogue.")
        d.find_element(By.ID, "submitBtn").click()
        assert d.find_element(By.ID, "result").text == "Thank you Manan, your message has been submitted."
    def s7():
        d.find_element(By.LINK_TEXT, "Logout").click()
        wait.until(EC.title_is("Gem Store - Login"))
        d.get(base + "/shop.html")
        wait.until(EC.title_is("Gem Store - Login"))

    step("Open login page, verify title", s1, "01_login_page")
    step("Invalid login shows error", s2, "02_invalid_login")
    step("Valid login opens catalogue", s3, "03_catalogue")
    step("Navigate to Contact page", s4, "04_contact_page")
    step("Empty form shows validation", s5, "05_form_validation")
    step("Form submission success message", s6, "06_form_submitted")
    step("Logout blocks protected page", s7, "07_after_logout")
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--browsers", default="chrome,edge,firefox")
    ap.add_argument("--headless", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    srv, port = start_server()
    base = f"http://127.0.0.1:{port}"
    print(f"Demo app served at {base}\n")
    summary = {}
    for name in a.browsers.split(","):
        name = name.strip()
        print(f"=== {name.upper()} ===")
        shots = os.path.join(OUT_DIR, name); os.makedirs(shots, exist_ok=True)
        try:
            d = make_driver(name, a.headless)
        except Exception as e:
            msg = str(e).splitlines()[0][:150]
            print("  could not start browser:", msg)
            summary[name] = {"started": False, "error": msg}
            continue
        ver = d.capabilities.get("browserVersion", "?")
        t0 = time.time()
        res = run_steps(d, base, shots)
        total = round(time.time() - t0, 2)
        # a few rendering details to compare between browsers
        d.get(base + "/index.html")
        btn = d.find_element(By.ID, "loginBtn")
        render = {"button_size": f"{btn.size['width']}x{btn.size['height']}",
                  "font": d.execute_script("return getComputedStyle(document.body).fontFamily"),
                  "window": f"{d.get_window_size()['width']}x{d.get_window_size()['height']}"}
        d.quit()
        for label, st, note in res:
            print(f"  [{st}] {label} {note}")
        passed = sum(1 for r in res if r[1] == "PASS")
        print(f"  -> {passed}/{len(res)} passed in {total}s (version {ver})\n")
        summary[name] = {"started": True, "version": ver, "passed": passed, "total": len(res),
                         "time_s": total, "render": render, "steps": res}
    json.dump(summary, open(os.path.join(OUT_DIR, "summary.json"), "w"), indent=2)
    print("---- COMPARISON ----")
    print(f"{'Browser':<10}{'Version':<18}{'Passed':<10}{'Time(s)':<9}Button size")
    for n, s in summary.items():
        if s["started"]:
            print(f"{n:<10}{s['version']:<18}{str(s['passed'])+'/'+str(s['total']):<10}{s['time_s']:<9}{s['render']['button_size']}")
        else:
            print(f"{n:<10}not available - {s['error']}")
    print("\nScreenshots saved in:", OUT_DIR)

if __name__ == "__main__":
    main()
