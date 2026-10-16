import requests
from bs4 import BeautifulSoup
import json
import os
import time

ACCOUNTS = [
    {"name": "南京招聘汇", "query": "南京招聘汇"},
    {"name": "南京招聘中心", "query": "南京招聘中心"},
    {"name": "国岗通", "query": "国岗通"},
    {"name": "江苏省招就中心", "query": "江苏省招就中心"},
]
SEEN_FILE = "seen.json"

def load_seen():
    return json.load(open(SEEN_FILE, encoding="utf-8")) if os.path.exists(SEEN_FILE) else {}

def save_seen(seen):
    json.dump(seen, open(SEEN_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def fetch_latest(query):
    url = f"https://weixin.sogou.com/weixin?type=1&query={query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    item = soup.select_one(".news-list li")
    if not item:
        return None
    title = item.select_one("h3 a").text.strip()
    link = item.select_one("h3 a")["href"]
    return {"title": title, "link": link}

def push_wechat(title, link, source):
    PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未配置 PUSHPLUS_TOKEN，跳过推送")
        return
    
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"📢 {source} 新文章",
        "content": f"<h3>{title}</h3><p>来源：{source}</p><p>链接：<a href='{link}'>{link}</a></p><p><small>复制链接到浏览器打开，内容可直接搬运到你的公众号</small></p>",
        "template": "html",
    }
    r = requests.post(url, json=data, timeout=10)
    result = r.json()
    if result.get("code") == 200:
        print(f"✅ 推送成功: {title}")
    else:
        print(f"❌ 推送失败: {result}")

def main():
    seen = load_seen()
    new_found = False

    for acc in ACCOUNTS:
        try:
            article = fetch_latest(acc["query"])
            if not article:
                print(f"⏳ {acc['name']}: 未获取到文章")
                continue

            cache_key = acc["name"]
            if seen.get(cache_key) == article["title"]:
                print(f"⏳ {acc['name']}: 无更新")
                continue

            print(f"📢 {acc['name']} 新文章: {article['title']}")
            push_wechat(article["title"], article["link"], acc["name"])
            seen[cache_key] = article["title"]
            new_found = True

        except Exception as e:
            print(f"❌ {acc['name']} 出错: {e}")

        time.sleep(3)

    save_seen(seen)
    if not new_found:
        print("✅ 本次检查无新文章")

if __name__ == "__main__":
    main()
