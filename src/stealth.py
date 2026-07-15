import asyncio
import random
import numpy as np
import logging
from typing import Tuple, List, Optional
from playwright.async_api import Page

logger = logging.getLogger("UltimateScraper.Stealth")

def calculate_bezier_point(p0: Tuple[float, float], p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], t: float) -> Tuple[int, int]:
    """Calculates a single coordinate along a cubic Bezier curve at step t (0 <= t <= 1)."""
    x = (1 - t)**3 * p0[0] + 3 * (1 - t)**2 * t * p1[0] + 3 * (1 - t) * t**2 * p2[0] + t**3 * p3[0]
    y = (1 - t)**3 * p0[1] + 3 * (1 - t)**2 * t * p1[1] + 3 * (1 - t) * t**2 * p2[1] + t**3 * p3[1]
    return int(x), int(y)

def generate_bezier_path(start: Tuple[int, int], end: Tuple[int, int], steps: int = 15) -> List[Tuple[int, int]]:
    """Generates a smooth curve between start and end coordinates."""
    p0 = (float(start[0]), float(start[1]))
    p3 = (float(end[0]), float(end[1]))
    
    # Generate random control points to add natural curvature
    distance = np.sqrt((p3[0] - p0[0])**2 + (p3[1] - p0[1])**2)
    offset_scale = distance * 0.2  # 20% deviation max
    
    p1 = (
        p0[0] + (p3[0] - p0[0]) * 0.25 + random.uniform(-offset_scale, offset_scale),
        p0[1] + (p3[1] - p0[1]) * 0.25 + random.uniform(-offset_scale, offset_scale)
    )
    p2 = (
        p0[0] + (p3[0] - p0[0]) * 0.75 + random.uniform(-offset_scale, offset_scale),
        p0[1] + (p3[1] - p0[1]) * 0.75 + random.uniform(-offset_scale, offset_scale)
    )
    
    path = []
    for i in range(steps + 1):
        t = i / steps
        # Optional: Add small velocity easing (slow start, fast middle, slow end)
        # Using a simple ease-in-out cubic function: t = 3*t^2 - 2*t^3
        t_eased = 3 * (t ** 2) - 2 * (t ** 3)
        path.append(calculate_bezier_point(p0, p1, p2, p3, t_eased))
        
    return path

async def human_delay(min_sec: float = 0.5, max_sec: float = 2.0):
    """Introduces a natural randomized pause with a Gaussian-like distribution."""
    mu = (min_sec + max_sec) / 2
    sigma = (max_sec - min_sec) / 6  # 99.7% of values fall within [min_sec, max_sec]
    delay = max(min_sec, min(random.gauss(mu, sigma), max_sec))
    await asyncio.sleep(delay)

async def human_move_mouse(page: Page, target_x: int, target_y: int, start_x: Optional[int] = None, start_y: Optional[int] = None):
    """Moves the mouse to a target coordinate using Bezier curves to look natural."""
    if start_x is None or start_y is None:
        # Default start from current viewport center if not specified
        viewport = page.viewport_size
        start_x = viewport["width"] // 2 if viewport else 960
        start_y = viewport["height"] // 2 if viewport else 540
        
    path = generate_bezier_path((start_x, start_y), (target_x, target_y))
    
    for x, y in path:
        # Small delay between movement steps to simulate speed limits
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.015))

async def human_click(page: Page, selector: str):
    """Clicks an element by moving the mouse to its location first and executing click with jitter."""
    element = await page.wait_for_selector(selector, state="visible", timeout=10000)
    if not element:
        raise ValueError(f"Element with selector {selector} not found or not visible.")
        
    box = await element.bounding_box()
    if not box:
        # Fallback to simple click if bounding box cannot be computed
        await page.click(selector)
        return
        
    # Pick a random point inside the bounding box (avoid exact center)
    x = int(box["x"] + box["width"] * random.uniform(0.2, 0.8))
    y = int(box["y"] + box["height"] * random.uniform(0.2, 0.8))
    
    await human_move_mouse(page, x, y)
    await human_delay(0.1, 0.3)
    
    # Click with slight random down/up duration
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.05, 0.15))
    await page.mouse.up()

async def human_type(page: Page, selector: str, text: str):
    """Types text into an element with randomized delay between key presses."""
    await human_click(page, selector)
    await human_delay(0.2, 0.5)
    
    for char in text:
        await page.type(selector, char, delay=random.randint(50, 180))
        # Occasional human-like typo correction (simple simulation)
        if random.random() < 0.03:  # 3% chance of typo
            typo_char = chr(ord(char) + random.choice([-1, 1]))
            await page.type(selector, typo_char, delay=random.randint(50, 150))
            await asyncio.sleep(random.uniform(0.2, 0.4))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.1, 0.3))

async def human_scroll(page: Page, scroll_depth_pixels: int = 500, direction: str = "down"):
    """Scrolls the page incrementally mimicking human scrolling speed and patterns."""
    current_scroll = 0
    sign = 1 if direction == "down" else -1
    
    while current_scroll < scroll_depth_pixels:
        # Generate random scrolling delta
        delta = random.randint(30, 80)
        current_scroll += delta
        
        # Scroll command execution
        await page.evaluate(f"window.scrollBy(0, {sign * delta})")
        
        # Small delay between scroll adjustments
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Occasional brief pauses
        if random.random() < 0.15:
            await human_delay(0.2, 0.6)

def get_evasion_script() -> str:
    """Returns a script designed to spoof fingerprints and pass bot tests (e.g. CreepJS)."""
    return """
    // 1. Overwrite navigator.webdriver to false
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // 2. Set languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });

    // 3. Fake WebGL vendor/renderer to prevent VM detection
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // UNMASKED_VENDOR_WEBGL
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        // UNMASKED_RENDERER_WEBGL
        if (parameter === 37446) {
            return 'Intel(R) Iris(R) Xe Graphics';
        }
        return getParameter.apply(this, arguments);
    };

    // 4. Overwrite plugins to look like standard Windows/Chrome installation
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const mockPlugin = {
                description: "Portable Document Format",
                filename: "internal-pdf-viewer",
                name: "Chrome PDF Viewer"
            };
            const pluginsList = [mockPlugin];
            pluginsList.item = function(index) { return pluginsList[index]; };
            pluginsList.namedItem = function(name) { 
                return pluginsList.find(p => p.name === name) || null; 
            };
            return pluginsList;
        }
    });

    // 5. Spoof hardware concurrency and device memory
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
    });
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
    });
    """
