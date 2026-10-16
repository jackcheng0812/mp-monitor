import requests
from bs4 import BeautifulSoup
import json
import os
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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
    """通过 QQ 邮箱发送通知"""
    sender = os.environ.get("QQ_EMAIL", "")
    auth_code = os.environ.get("QQ_AUTH_CODE", "")
    receiver = os.environ.get("QQ_EMAIL", "")  # 发给自己
    
    if not sender or not auth_code:
        print("⚠️ 未配置 QQ_EMAIL 或 QQ_AUTH_CODE，跳过推送")
        return
    
    # 构造邮件
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📢 {source} 新文章：{title}"
    msg["From"] = sender
    msg["To"] = receiver
    
    # 纯文本版
    text = f"来源：{source}\n标题：{title}\n链接：{link}\n\n复制链接到浏览器打开，内容可直接搬运到你的公众号。"
    
    # HTML版
    html = f"""
    <html>
    <body>
        <h2>📢 {source} 发了新文章</h2>
        <p><b>标题：</b>{title}</p>
        <p><b>来源：</b>{source}</p>
        <p><a href="{link}">👉 点击查看原文</a></p>
        <hr>
        <p style="color:#999;font-size:12px;">复制链接到浏览器打开，内容可直接搬运到你的公众号</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    
    # 发送
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context) as server:
            server.login(sender, auth_code)
            server.sendmail(sender, receiver, msg.as_string())
        print(f"✅ 邮件推送成功: {title}")
    except Exception as e:
        print(f"❌ 邮件推送失败: {e}")

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
