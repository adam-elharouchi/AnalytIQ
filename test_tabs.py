from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        
        # We need to mock auth because verifyAccess redirects if not logged in
        page.goto("http://localhost:5001/superadmin-dashboard.html")
        page.evaluate("""
            localStorage.setItem('token', 'faketoken');
            localStorage.setItem('user_role', 'superadmin');
            localStorage.setItem('user', JSON.stringify({name: 'Admin', role: 'superadmin'}));
        """)
        # Reload to apply tokens
        page.goto("http://localhost:5001/superadmin-dashboard.html")
        
        # Wait a bit
        page.wait_for_timeout(1000)
        
        # Check initial display
        overview_display = page.evaluate("document.getElementById('overview-section').style.display")
        users_display = page.evaluate("document.getElementById('users-section').style.display")
        print(f"Before click: overview={overview_display}, users={users_display}")
        
        # Click users tab
        print("Clicking Users tab...")
        page.click("a[data-target='users-section']")
        
        # Wait a bit
        page.wait_for_timeout(500)
        
        # Check display again
        overview_display = page.evaluate("document.getElementById('overview-section').style.display")
        users_display = page.evaluate("document.getElementById('users-section').style.display")
        print(f"After click: overview={overview_display}, users={users_display}")
        
        browser.close()

if __name__ == "__main__":
    run()
