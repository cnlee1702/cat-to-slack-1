import collections
import json
import logging
import os
import random
import requests
import schedule
import sys
import time


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)


# errors


class CatShortageError(RuntimeError):
    pass


# fetching cats

CAT_URL = "https://www.reddit.com/r/CatGifs/hot.json"
CAT_PARAMS = {"sort": "top", "t": "day", "limit": "100"}
CAT_HEADERS = {"user-agent": "Cat to Slack 1.1"}

cat_collection = collections.deque([], 100)
posted_cats = collections.deque([], 14)


def get_new_cat():
    try:
        if len(cat_collection) < 1:
            logging.info(f"Importing new cats from {CAT_URL}")
            response = requests.get(CAT_URL, params=CAT_PARAMS, headers=CAT_HEADERS)
            posts = response.json()["data"]["children"]
            for post in posts:
                url = post["data"]["url"]
                title = post["data"]["title"]
                cat = {"url": url, "title": title}
                if ".gif" in url:
                    if url not in posted_cats:
                        cat_collection.append(cat)

        cat = cat_collection.popleft()
        return cat

    except:
        raise CatShortageError


# posting cats
INCOMING_WEBHOOK_URL = os.environ.get("INCOMING_WEBHOOK_URL")
CAT_EMOJIS = [
    ":smiley_cat:",
    ":smile_cat:",
    ":joy_cat:",
    ":heart_eyes_cat:",
    ":smirk_cat:",
    ":kissing_cat:",
    ":scream_cat:",
    ":crying_cat_face:",
    ":pouting_cat:",
    ":cat:",
    ":cat2:",
]

PAYLOAD_PARAMS = {
    "channel": os.environ.get("CAT_CHANNEL"),
    "username": "daily_cats",
    "unfurl_media": True,
    "unfurl_links": True,
}


def post_cat(cat):
    emoji = random.choice(CAT_EMOJIS)
    payload = PAYLOAD_PARAMS.copy()
    payload["blocks"] = [
        {
            "type": "image",
            "title": {"type": "plain_text", "text": f"{cat['title']} {emoji}"},
            "image_url": cat["url"],
            "alt_text": cat["title"],
        }
    ]
    return requests.post(INCOMING_WEBHOOK_URL, data={"payload": json.dumps(payload)})


# the job


def post_new_cat():
    try:
        cat = get_new_cat()
    except CatShortageError:
        logging.warning("No new cats available!")
        return
    except Exception as exc:
        logging.exception(f"Failed to get cat :( {exc}", exc_info=True)
        return
    else:
        logging.info(f"Have cat: {cat}")

    try:
        response = post_cat(cat)
        response.raise_for_status()
        posted_cats.append(cat["url"])
    except:
        try:
            logging.error(f"Failed to post cat :{response}")
        except:
            logging.error(f"Failed to post cat due to internal error")
        return
    else:
        logging.info(f"Posted cat: {response}")


# the schedule

CAT_TIMES = os.environ.get("CAT_TIMES", "10:00").split(",")

if __name__=="__main__":
    for cat_time in CAT_TIMES:
        logging.info(f"Adding daily schedule at {cat_time}")
        schedule.every().day.at(cat_time).do(post_new_cat)
    
    while True:
        schedule.run_pending()
        time.sleep(1)