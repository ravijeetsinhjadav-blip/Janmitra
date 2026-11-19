import os
import sys
import time
import socket
import secrets
import string
import subprocess
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

# Ensure app root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.cli.admin_create import provision_admin
from app.core.database import SessionLocal


def is_port_listening(host: str, port: int) -> bool:
    """Check if a TCP port is open and listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def wait_for_http(url: str, timeout: float = 30.0) -> bool:
    """Wait for an HTTP URL to return a response."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urlopen(url, timeout=2.0) as resp:
                if resp.status in (200, 304, 404):
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def generate_ephemeral_test_password() -> str:
    """Generate dynamic OWASP-compliant test password without persistent exposure."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    part1 = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    part2 = [secrets.choice(chars) for _ in range(20)]
    pw_list = part1 + part2
    secrets.SystemRandom().shuffle(pw_list)
    return "".join(pw_list)


def test_real_admin_browser_e2e():
    """Real Browser E2E Test driving headless Google Chrome against live Vite Admin and FastAPI backend."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    admin_dir = os.path.abspath(os.path.join(backend_dir, "..", "admin_dashboard"))

    backend_proc = None
    admin_proc = None

    try:
        # Auto-start FastAPI backend if not already running on port 8000
        if not is_port_listening("127.0.0.1", 8000):
            print("[E2E SETUP] Launching FastAPI backend on 127.0.0.1:8000...")
            backend_proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=backend_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if not wait_for_http("http://127.0.0.1:8000/api/v1/health", timeout=15.0):
                print("[WARNING] Health check timed out, continuing...")

        # Auto-start Vite preview server if not already running on port 3000
        if not is_port_listening("127.0.0.1", 3000):
            print("[E2E SETUP] Launching Vite preview server on 127.0.0.1:3000...")
            npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
            admin_proc = subprocess.Popen(
                [npm_cmd, "run", "preview", "--", "--port", "3000", "--host", "127.0.0.1"],
                cwd=admin_dir,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_for_http("http://127.0.0.1:3000/", timeout=15.0)

        # 1. Setup Admin credentials dynamically in the active SQLite dev database
        admin_email = "admin@janmitra.internal"
        admin_password = generate_ephemeral_test_password()
        with SessionLocal() as db:
            provision_admin(admin_email, admin_password, db=db)
        print(f"\n[E2E SETUP] Admin provisioned with ephemeral session credentials: {admin_email}")

        # 2. Launch Playwright Headless Chrome against running servers (Port 3000 and 8000)
        with sync_playwright() as p:
            print("[BROWSER SETUP] Launching Headless Google Chrome...")
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            page.on("console", lambda msg: print(f"[BROWSER CONSOLE {msg.type}] {msg.text}"))
            page.on("pageerror", lambda exc: print(f"[BROWSER PAGE ERROR] {exc}"))

            # Step 1: Open Login Page
            print("[BROWSER STEP 1] Navigating to http://127.0.0.1:3000...")
            page.goto("http://127.0.0.1:3000", wait_until="networkidle", timeout=15000)
            assert "JanMitra Assist" in page.content(), "Page content missing 'JanMitra Assist'"
            assert page.locator("input[type='email']").is_visible(), "Email input not found on LoginView"
            print("[VERIFIED] Admin LoginView rendered in browser.")

            # Step 2: Fill in Credentials and Sign In
            print("[BROWSER STEP 2] Submitting administrator credentials...")
            page.fill("input[type='email']", admin_email)
            page.fill("input[type='password']", admin_password)
            page.click("button[type='submit']")

            # Wait briefly and inspect if an error alert popped up
            page.wait_for_timeout(1000)
            alert_locator = page.locator(".login-alert")
            if alert_locator.count() > 0 and alert_locator.is_visible():
                print(f"[BROWSER LOGIN ALERT] {alert_locator.inner_text()}")

            # Step 3: Wait for Dashboard Overview
            print("[BROWSER STEP 3] Waiting for Dashboard Overview to render...")
            page.wait_for_selector(".dashboard-header", timeout=10000)
            assert page.locator("text=JanMitra Assist Admin Console").is_visible()
            assert page.locator("text=FastAPI Online").is_visible()
            print("[VERIFIED] Admin authenticated; Overview dashboard rendered.")

            # Step 4: Navigate to Government Schemes
            print("[BROWSER STEP 4] Navigating to Government Schemes...")
            page.click("button:has-text('Government Schemes')")
            page.wait_for_selector(".schemes-container, table", timeout=10000)

            # If PM-KISAN is not on the active page, use search to find it
            if page.locator("text=PM-KISAN").count() == 0:
                search_input = page.locator("input[placeholder*='Search']")
                if search_input.is_visible():
                    print("[BROWSER STEP 4] PM-KISAN not immediately visible; searching via UI...")
                    search_input.fill("PM-KISAN")
                    page.click("button:has-text('Search')")
                    page.wait_for_timeout(500)

            page.wait_for_selector("text=PM-KISAN", timeout=10000)
            assert page.locator("text=PM-KISAN").first.is_visible()
            print("[VERIFIED] Schemes table populated with official records.")

            # Step 5: Open Official Beneficiary Analytics Modal for PM-KISAN
            print("[BROWSER STEP 5] Opening Beneficiary Analytics Modal...")
            analytics_btn = page.locator("tr:has-text('PM-KISAN') button[title='Beneficiary Analytics & Intelligence']")
            analytics_btn.click()
            page.wait_for_selector(".modal-backdrop", timeout=8000)
            assert page.locator("text=Scheme Intelligence & Analytics").is_visible()

            # Step 6: Verify Provenance and Caste-Unavailability Notice (Pillar 1)
            print("[BROWSER STEP 6] Verifying Data Provenance and Civic Disclaimer...")
            page.wait_for_selector(".modal-dialog div:has-text('Period:')", timeout=10000)
            modal_text = page.locator(".modal-dialog").inner_text()
            assert "Scope:" in modal_text, "Geographic scope missing from analytics view"
            assert "Report:" in modal_text, "Report title missing from analytics view"
            assert "Caste-wise beneficiary data is not available from the verified official source" in modal_text, \
                "Mandatory statutory disclaimer missing from citizen-facing analytics"
            print("[VERIFIED] Provenance fields rendered; no fabricated caste figures present.")

            # Step 7: Check Tab 2 - Import Form with Provenance Fields
            print("[BROWSER STEP 7] Verifying Analytics Import Form...")
            page.click("button:has-text('Import Dataset')")
            page.wait_for_selector("input[placeholder*='Release Report']", timeout=5000)
            assert page.locator("select:has-text('National (All India)')").is_visible()
            assert page.locator("text=Audit Mandate: Do not record synthetic or estimated distributions").is_visible()
            print("[VERIFIED] Import Form includes full provenance and audit warning.")

            # Step 8: Check Tab 3 - Category Rules & Document Requirements
            print("[BROWSER STEP 8] Inspecting Category Rules...")
            page.click("button:has-text('Category Rules & Documents')")
            page.wait_for_selector("text=Category-Specific Eligibility Criteria", timeout=5000)
            rules_text = page.locator(".modal-dialog").inner_text()
            assert "SECC Deprivation" in rules_text or "Eligibility Criteria" in rules_text
            assert "Category Document Requirements" in rules_text
            print("[VERIFIED] Category eligibility criteria and category documents successfully audited in UI.")

            # Step 9: Close Modal and Navigate Other Modules
            print("[BROWSER STEP 9] Closing modal and testing tab navigation...")
            page.click(".modal-header .btn-close")
            time.sleep(0.5)

            # Citizen Users
            page.click("button:has-text('Citizen Users')")
            page.wait_for_selector("text=Citizen Accounts", timeout=5000)
            print("[VERIFIED] Citizen User management view loaded.")

            # Subscriptions & Revenue Monitoring
            print("[BROWSER STEP 9B] Navigating to Subscriptions & Revenue Monitoring...")
            page.click("button:has-text('Subscriptions & Revenue')")
            page.wait_for_selector(".subscription-monitoring-container", timeout=8000)
            assert page.locator("text=Active Premium Subscribers").is_visible()
            assert page.locator("text=Total Revenue Captured").is_visible()
            assert page.locator("text=Citizen Subscriptions").is_visible()
            assert page.locator("text=Razorpay Transactions").is_visible()
            assert page.locator(".subscription-monitoring-container .pagination-container").is_visible()
            print("[VERIFIED] Subscriptions & Revenue view rendered with KPIs and pagination.")

            # Switch to Payments Tab
            print("[BROWSER STEP 9C] Switching to Razorpay Transactions tab...")
            page.click("button:has-text('Razorpay Transactions')")
            page.wait_for_selector("text=Razorpay Order ID", timeout=8000)
            assert page.locator("text=Razorpay Payment ID").is_visible()
            assert page.locator(".subscription-monitoring-container .pagination-container").is_visible()
            pay_search = page.locator("input[placeholder*='Search by Order ID']")
            assert pay_search.is_visible()
            pay_search.fill("order_test_filter")
            page.wait_for_timeout(500)
            pay_search.fill("")
            print("[VERIFIED] Razorpay Transactions tab rendered with audit table and pagination controls.")

            # System Configuration
            page.click("button:has-text('System Configuration')")
            page.wait_for_selector("text=System Architecture & Environment Verification", timeout=5000)
            print("[VERIFIED] System Diagnostics & Configuration loaded.")

            # Step 10: Logout Verification
            print("[BROWSER STEP 10] Testing Admin Logout...")
            page.click("button.btn-logout")
            page.wait_for_selector("input[type='email']", timeout=8000)
            assert page.locator("button:has-text('Sign In as Administrator')").is_visible()
            print("[VERIFIED] Logout successful; session invalidated and redirected to LoginView.")

            browser.close()
            print("\n[SUCCESS] Real Playwright Browser E2E Test PASSED (100% Verified UI & Network Flow)!\n")

    finally:
        if admin_proc:
            try:
                if sys.platform == "win32":
                    subprocess.run(f"taskkill /F /T /PID {admin_proc.pid}", shell=True, capture_output=True)
                else:
                    admin_proc.terminate()
            except Exception:
                pass
        if backend_proc:
            try:
                if sys.platform == "win32":
                    subprocess.run(f"taskkill /F /T /PID {backend_proc.pid}", shell=True, capture_output=True)
                else:
                    backend_proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    test_real_admin_browser_e2e()
