import json
from datetime import date
import logging
import feedparser
import html2text
import concurrent.futures
import requests

from app.gpt import get_answer_from_llama_web

with open("app/data/hot_news_rss.json", encoding="utf-8", mode='r') as f:
    rss_urls = json.load(f)

TODAY = today = date.today()
MAX_DESCRIPTION_LENGTH = 300
MAX_POSTS = 3

def cut_string(text):
    words = text.split()
    new_text = ""
    count = 0
    for word in words:
        if len(new_text + word) > MAX_DESCRIPTION_LENGTH:
            break
        new_text += word + " "
        count += 1

    return new_text.strip() + '...'

def get_summary_from_gpt_thread(url):
    news_summary_prompt = '请用中文简短概括这篇文章的内容。'
    return str(get_answer_from_llama_web([news_summary_prompt], [url]))

def get_summary_from_gpt(url):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(get_summary_from_gpt_thread, url)
        return future.result(timeout=600)

def get_description(entry):
    gpt_answer = None
    try:
        gpt_answer = get_summary_from_gpt(entry.get('link'))
    except Exception as e:
        logging.error(e)
    if gpt_answer is not None:
        summary = 'AI: ' + gpt_answer
    else:
        summary = cut_string(get_text_from_html(entry.get('description')))
    return summary

def get_text_from_html(html):
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    text_maker.ignore_tables = False
    text_maker.ignore_images = True
    return text_maker.handle(html)

def get_post_urls_with_title(rss_url):
    headers = {'Accept': 'application/json'}
    endpoint_url = f"https://rss-worker.thinkingincrowd.workers.dev/?url={rss_url}&max=1"
    logging.info(f"Getting rss from {rss_url}")
    response = requests.get(endpoint_url, headers=headers)
    if response.status_code == 200:
        try:
            feed = response.json()
            updated_posts = []
            for entry in feed.get('items'):
                updated_post = {}
                updated_post['title'] = entry.get('title')
                updated_post['summary'] = get_description(entry)
                updated_post['url'] = entry.get('link')
                updated_post['publish_date'] = entry.get('pubDate')
                updated_posts.append(updated_post)
                if len(updated_posts) >= MAX_POSTS:
                    break
            return updated_posts
        except Exception as error:
            logging.error("Error: Unable to get rss json content", error)
            return []
    else:
        logging.error(f"Error: {response.status_code} - {response.reason}")
        return []

# def get_post_urls_with_title(rss_url):
#     feed = feedparser.parse(rss_url)
#     updated_posts = []

#     for entry in feed.entries:
#         published_time = entry.published_parsed if 'published_parsed' in entry else None
#         # published_date = date(published_time.tm_year,
#         #                       published_time.tm_mon, published_time.tm_mday)
#         updated_post = {}
#         updated_post['title'] = entry.title
#         updated_post['summary'] = get_description(entry)
#         updated_post['url'] = entry.link
#         updated_post['publish_date'] = published_time
#         updated_posts.append(updated_post)
#         if len(updated_posts) >= MAX_POSTS:
#             break
        
#     return updated_posts

def build_slack_blocks(title, news):
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{title} # {TODAY.strftime('%Y-%m-%d')}"
            }
        }]
    for news_item in news:
        blocks.extend([{
            "type": "section",
            "text": {
				"text": f"*{news_item.get('title')}*",
				"type": "mrkdwn"
			},
        },{
            "type": "section",
            "text": {
				"text": f"{news_item.get('summary')}",
				"type": "plain_text"
			},
        },{
            "type": "section",
            "text": {
				"text": f"原文链接：<{news_item.get('url')}>",
				"type": "mrkdwn"
			},
        },{
            "type": "divider"
        }])
    return blocks

def build_hot_news_blocks(news_key):
    rss = rss_urls[news_key]['rss']['hot']
    hot_news = get_post_urls_with_title(rss['url'])
    logging.info(f"=====> {hot_news}")
    hot_news_blocks = build_slack_blocks(
        rss['name'], hot_news)
    return hot_news_blocks

def build_1point3acres_hot_news_blocks():
    return build_hot_news_blocks('1point3acres')

def build_reddit_news_hot_news_blocks():
    return build_hot_news_blocks('reddit-news')

def build_hackernews_news_hot_news_blocks():
    return build_hot_news_blocks('hackernews')

def build_producthunt_news_hot_news_blocks():
    return build_hot_news_blocks('producthunt')

def build_xueqiu_news_hot_news_blocks():
    return build_hot_news_blocks('xueqiu')

def build_jisilu_news_hot_news_blocks():
    return build_hot_news_blocks('jisilu')

def build_all_news_block():
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        onepoint3acres_news = executor.submit(build_1point3acres_hot_news_blocks)
        # reddit_news = executor.submit(build_reddit_news_hot_news_blocks)
        # hackernews_news = executor.submit(build_hackernews_news_hot_news_blocks)
        # producthunt_news = executor.submit(build_producthunt_news_hot_news_blocks)

        # onepoint3acres_news_block = onepoint3acres_news.result(timeout=600)
        # reddit_news_block = reddit_news.result(timeout=600)
        # hackernews_news_block = hackernews_news.result(timeout=600)
        # producthunt_news_block = producthunt_news.result(timeout=600)

        return [onepoint3acres_news_block]
