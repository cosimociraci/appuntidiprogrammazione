import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content("<h1>Playwright funziona su Ubuntu 24.04!</h1><p>Test PDF generato correttamente.</p>")
        await page.pdf(path="test_funzionamento.pdf")
        await browser.close()
        print("✅ PDF generato con successo! La strada è quella giusta.")

asyncio.run(test())