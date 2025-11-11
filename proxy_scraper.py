#!/usr/bin/env python3
"""
proxy_scraper.py
📦 Lấy proxy từ nhiều trang web, kiểm tra hoạt động, lưu ra Proxy.txt
"""

import asyncio
import aiohttp
import async_timeout
import requests
from bs4 import BeautifulSoup
import time

# ===== DANH SÁCH NGUỒN =====
SOURCES = {
    "https://free-proxy-list.net/": "html",
    "https://www.sslproxies.org/": "html",
    "https://www.socks-proxy.net/": "html",
    "https://www.us-proxy.org/": "html",
    "https://spys.me/proxy.txt": "txt",
    "https://www.proxy-list.download/api/v1/get?type=http": "txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all": "txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=https&timeout=10000&country=all": "txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt": "txt",
    "https://openproxylist.xyz/http.txt": "txt",
    "https://openproxylist.xyz/https.txt": "txt",
}

TEST_URL = "https://httpbin.org/ip"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 8
CONCURRENCY = 100


# ===== HÀM LẤY PROXY =====
def scrape_html_table(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", id="proxylisttable")
        proxies = []
        if not table:
            return proxies
        for row in table.find("tbody").find_all("tr"):
            cols = [td.text.strip() for td in row.find_all("td")]
            if len(cols) >= 2:
                proxies.append(f"{cols[0]}:{cols[1]}")
        print(f"  [+] {url}: {len(proxies)} proxies scraped")
        return proxies
    except Exception as e:
        print(f"  [!] Error scraping {url}: {e}")
        return []


def scrape_txt_api(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        lines = r.text.strip().splitlines()
        proxies = [ln.strip() for ln in lines if ":" in ln and "." in ln and len(ln.strip()) < 30]
        print(f"  [+] {url}: {len(proxies)} proxies scraped")
        return proxies
    except Exception as e:
        print(f"  [!] Error scraping {url}: {e}")
        return []


# ===== HÀM KIỂM TRA PROXY =====
async def check_proxy(session, proxy, sem):
    async with sem:
        proxy_url = f"http://{proxy}"
        try:
            with async_timeout.timeout(TIMEOUT):
                start = time.time()
                async with session.get(TEST_URL, proxy=proxy_url, timeout=TIMEOUT) as resp:
                    if resp.status == 200:
                        ping = round(time.time() - start, 2)
                        return proxy, ping
        except:
            return None
    return None


async def validate_all(proxies):
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY, ssl=False)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT + 2)
    sem = asyncio.Semaphore(CONCURRENCY)
    working = []

    async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=HEADERS) as session:
        tasks = [check_proxy(session, p, sem) for p in proxies]
        for fut in asyncio.as_completed(tasks):
            res = await fut
            if res:
                working.append(res)
    return working


# ===== MAIN =====
def main():
    print("🚀 Đang lấy proxy từ nhiều nguồn...")
    all_proxies = []

    for url, mode in SOURCES.items():
        if mode == "html":
            all_proxies.extend(scrape_html_table(url))
        elif mode == "txt":
            all_proxies.extend(scrape_txt_api(url))

    all_proxies = list(set(all_proxies))  # loại trùng
    print(f"\n📦 Tổng cộng thu được: {len(all_proxies)} proxies")

    # Kiểm tra hoạt động
    print("🔍 Đang kiểm tra proxy hoạt động (sẽ mất vài phút)...\n")
    loop = asyncio.get_event_loop()
    working = loop.run_until_complete(validate_all(all_proxies))

    working.sort(key=lambda x: x[1])  # sắp theo ping
    alive = [p for p, _ in working]

    print(f"\n✅ Số proxy hoạt động: {len(alive)}")

    # Lưu ra file Proxy.txt
    with open("Proxy.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(alive))
    print("💾 Đã lưu proxy hoạt động vào: Proxy.txt\n")

    # In thử vài dòng đầu
    if alive:
        print("🧩 Một vài proxy hoạt động:")
        for p in alive[:10]:
            print("  ", p)


if __name__ == "__main__":
    main()
