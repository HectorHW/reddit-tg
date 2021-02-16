import os
import threading
from time import sleep
import praw
from typing import List, Dict


def make_reddit(token_filename='reddit.txt') -> praw.Reddit :
    with open(token_filename) as f:
        client_id, client_secret, user_agent = (s.strip() for s in f.readlines())

    reddit = praw.Reddit(client_id=client_id,
                         client_secret=client_secret,
                         user_agent=user_agent)
    return reddit

def pull_new(reddit_instance:praw.Reddit, subreddit_name='Sucrose'):
    subreddit = reddit_instance.subreddit(subreddit_name)
    return subreddit.new(limit=None)

def pull_dictupdate(reddit_instance:praw.Reddit, last_post_dict_record:Dict, subreddit_name='Sucrose') -> List[Dict]:
    puller = pull_new(reddit_instance, subreddit_name)
    from praw.models import Submission

    def filter_submissions(posts:List[Submission]) -> List[Dict]:
        res = []
        for r_post in posts:
            if r_post.is_video:
                continue
            try:
                res.append(

                    {
                        'img_url': r_post.preview['images'][-1]['source']['url'],
                        'title': r_post.title,
                        'url':r_post.shortlink
                    }
                    )
            except AttributeError:
                continue
        return res

    posts = []

    if subreddit_name.lower() in last_post_dict_record:
        last_pull = last_post_dict_record[subreddit_name.lower()]
        i = 0 #limit to 10 msgs
        while True:
            try:
                post = next(puller)
            except StopIteration:
                break
            if post.id==last_pull or i>10:
                break
            posts.append(post)
            i+=1
        if not posts: #no new posts
            return []

    else:
        i = 0
        while i<10:
            try:
                posts.append(next(puller))
                i+=1
            except StopIteration:
                break

    last_post_dict_record[subreddit_name.lower()] = posts[0].id
    return filter_submissions(posts)

def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    from itertools import cycle, islice
    pending = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = cycle(islice(nexts, pending))

def pull_multiple_subreddits(reddit_instance:praw.Reddit, last_post_dict:Dict, subreddit_list:List) -> List[Dict]:

    generators = []
    for name in subreddit_list:
        generators.append(pull_dictupdate(reddit_instance, last_post_dict, name))
        #print(name)
        sleep(0.1)

    return list(roundrobin(*generators))

def load_dict(filename) -> Dict:
    import json
    with open(filename) as f:
        return json.load(f)

def save_dict(d:Dict, filename):
    import json
    with open(filename, 'w') as f:
        json.dump(d, f)

class RedditPooler:
    def __init__(self, updater, chat_id, subreddits, subreddits_mutex):
        super(RedditPooler, self).__init__()
        self.updater = updater
        self.chat_id = chat_id
        self.subreddits = subreddits
        self.is_stopped = False
        self.subreddits_mutext = subreddits_mutex

    def run(self):
        if os.path.exists('last-upload.reddit'):
            last_post_dict = load_dict('last-upload.reddit')
        else:
            last_post_dict = {}

        reddit = make_reddit('reddit.txt')

        while not self.is_stopped:
            try:

                self.subreddits_mutext.acquire()
                res = pull_multiple_subreddits(reddit, last_post_dict, self.subreddits)

            except praw.errors.HTTPException as e:
                print(f"encountered HTTP error: {e.message}")
                self.updater.bot.send_message(chat_id=self.chat_id,
                                              text = f"encountered HTTP error: {e.message}")
                sleep(1)
                continue
            finally:
                self.subreddits_mutext.release()

            for record in res:

                photo_url = record['img_url']
                import telegram
                try: #TODO fix crashing when sending gifs
                    # example: https://external-preview.redd.it/IHWCiM6lozyhPd4L2M_2K3YkDYrc0pfqFHzoteGIAXE.gif?width=640&crop=smart&format=png8&s=b25717d8d4ebc804dc118378ab78125f87178b1c
                    self.updater.bot.send_photo(
                        chat_id=self.chat_id, photo=photo_url,
                        caption=f"{record['title']}\n{record['url']}")
                    sleep(0.06) # to prevent flood - limit is ~30 msgs/s
                except telegram.error.BadRequest as e:
                    self.updater.bot.send_message(chat_id=self.chat_id,
                                                  text=f"{e.message} {photo_url}")
                    print(e.message, photo_url)

            sleep(5)

        save_dict(last_post_dict, 'last-upload.reddit')

    def stop(self):
        self.is_stopped = True

if __name__ == '__main__':
    if os.path.exists('last-upload.reddit'):
        last_post_dict = load_dict('last-upload.reddit')
    else:
        last_post_dict = {}

    subreddits = [
        'Genshin_Impact'
    ]

    reddit = make_reddit('reddit.txt')

    res = pull_multiple_subreddits(reddit, last_post_dict, subreddits)
    print(res)

    save_dict(last_post_dict, 'last-upload.reddit')


