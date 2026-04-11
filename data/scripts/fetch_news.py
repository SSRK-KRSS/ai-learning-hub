#!/usr/bin/env python3
import json, feedparser, hashlib, os, re, requests, time
from datetime import datetime

RSS_SOURCES = [
    {"name": "BestBlogs", "url": "https://www.bestblogs.dev/rss", "type": "aggregator"},
    {"name": "RadarAI", "url": "https://radarai.tech/rss", "type": "aggregator"},
    {"name": "机器之心", "url": "https://rsshub.app/jiqizhixin/latest", "type": "news"},
    {"name": "新智元", "url": "https://rsshub.app/aixinzhiyuan/latest", "type": "news"},
    {"name": "arXiv cs.AI", "url": "https://rss.arxiv.org/rss/cs.AI", "type": "paper"},
]
LLM_API_URL = "https://api.deepseek.com/v1/chat/completions"
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
OUTPUT_FILE = "data/news.json"

def clean_html(s): return re.sub('<.*?>', '', s).strip()
def gen_id(t,u): return hashlib.md5(f"{t}{u}".encode()).hexdigest()

def fetch_feed(src):
    items = []
    try:
        feed = feedparser.parse(src["url"])
        for e in feed.entries[:5]:
            pub = e.get('published', '')
            try: pub = datetime(*e.published_parsed[:6]).strftime("%Y-%m-%d")
            except: pass
            summary = clean_html(e.get('summary', e.get('description', '')))[:300]
            items.append({"id":gen_id(e.title,e.link),"title":e.title,"url":e.link,"source":src["name"],"type":src["type"],"published":pub,"summary":summary,"ai_summary":""})
    except Exception as e: print(f"❌ {src['name']}: {e}")
    return items

def generate_summary(item):
    if not LLM_API_KEY: return item['summary'][:80]+'...'
    prompt = f"用一句中文总结AI新闻核心内容，不超过40字。标题：{item['title']} 内容：{item['summary'][:300]}"
    try:
        r = requests.post(LLM_API_URL, headers={"Authorization":f"Bearer {LLM_API_KEY}"}, json={"model":"deepseek-chat","messages":[{"role":"user","content":prompt}],"max_tokens":60}, timeout=15)
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return item['summary'][:80]+'...'

def main():
    all_items = []
    for s in RSS_SOURCES:
        print(f"📡 {s['name']}")
        all_items.extend(fetch_feed(s))
        time.sleep(0.5)
    seen = set()
    uniq = [i for i in all_items if i['id'] not in seen and not seen.add(i['id'])]
    uniq.sort(key=lambda x:x['published'], reverse=True)
    for i in uniq[:8]:
        print(f"🤖 摘要: {i['title'][:20]}")
        i['ai_summary'] = generate_summary(i)
        time.sleep(1)
    news = [i for i in uniq if i['type']!='paper'][:10]
    trend_kw = ["世界模型","多智能体","Agent","具身智能","约束工程","神经计算机"]
    trend = max(trend_kw, key=lambda k: sum(1 for n in news if k.lower() in (n['title']+n['summary']).lower())) if news else "世界模型"
    frontier = [{"concept":"约束工程","description":"为Agent套上流程管控、并发调度、验证纠错三层纪律框架","url":"#"}]
    out = {"updated_at":datetime.now().isoformat(),"daily_trend":{"keyword":trend,"source":"今日新闻高频词"},"news":news,"frontier_knowledge":frontier}
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False,indent=2)
    print("✅ 完成")

if __name__ == "__main__": main()
