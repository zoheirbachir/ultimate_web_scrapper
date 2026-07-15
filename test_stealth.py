import asyncio
from src.scraper import BrowserClient
from src.stealth import human_move_mouse, human_scroll, human_type, human_click

async def test_spoofing():
    print("--- Testing Stealth Spoofing Integrity ---")
    client = BrowserClient(headless=True)
    try:
        await client.start()
        # Open a page
        page = await client.context.new_page()
        await page.goto("https://httpbin.org/html")
        
        # Evaluate spoofed parameters
        webdriver = await page.evaluate("navigator.webdriver")
        languages = await page.evaluate("navigator.languages")
        hardware_concurrency = await page.evaluate("navigator.hardwareConcurrency")
        device_memory = await page.evaluate("navigator.deviceMemory")
        plugins_len = await page.evaluate("navigator.plugins.length")
        
        print(f"navigator.webdriver: {webdriver} (Expected: None/undefined)")
        print(f"navigator.languages: {languages} (Expected: ['en-US', 'en'])")
        print(f"navigator.hardwareConcurrency: {hardware_concurrency} (Expected: 8)")
        print(f"navigator.deviceMemory: {device_memory} (Expected: 8)")
        print(f"navigator.plugins.length: {plugins_len} (Expected: 1 or more)")
        
        # Basic check
        assert webdriver is None, "Evasion failed: navigator.webdriver is not masked!"
        assert languages == ["en-US", "en"], "Evasion failed: navigator.languages is not spoofed!"
        assert hardware_concurrency == 8, "Evasion failed: hardwareConcurrency is not spoofed!"
        assert plugins_len > 0, "Evasion failed: plugins list is empty!"
        print("Stealth evasion checks PASSED!")
        
    finally:
        await client.stop()
    print()

async def test_human_interactions():
    print("--- Testing Human Interaction Emulation ---")
    # Launch browser in headed mode or headless, let's do headless to verify command execution
    client = BrowserClient(headless=True)
    try:
        await client.start()
        page = await client.context.new_page()
        
        # Navigate to a simple input/click page
        await page.goto("https://example.com")
        
        print("Simulating human mouse movements...")
        # Simulate moving mouse to random coordinates
        await human_move_mouse(page, 400, 300, start_x=100, start_y=100)
        
        print("Simulating human scroll...")
        # Simulate scrolling
        await human_scroll(page, scroll_depth_pixels=300, direction="down")
        
        # We can also mock a simple element clicking if one existed
        # E.g., clicking on 'More information...' link on example.com
        print("Simulating human element click...")
        await human_click(page, "a")
        
        print("Navigation after click url:", page.url)
        print("Human interactions PASSED!")
        
    finally:
        await client.stop()
    print()

async def main():
    await test_spoofing()
    await test_human_interactions()

if __name__ == "__main__":
    asyncio.run(main())
