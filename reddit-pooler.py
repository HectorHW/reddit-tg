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
                        'img_url': r_post.preview['images'][-1]['resolutions'][-1]['url'],
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
        while True:
            post = next(puller)
            if post.id==last_pull:
                break
            posts.append(post)
        if not posts: #no new posts
            return []

    else:
        i = 0
        while i<10:
            posts.append(next(puller))
            i+=1
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
        print(name)
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


if __name__ == '__main__':
    if os.path.exists('last-upload.reddit'):
        last_post_dict = load_dict('last-upload.reddit')
    else:
        last_post_dict = {}

    subreddits = [
        'Genshin_Impact', 'GenshinImpactHentai'
    ]

    reddit = make_reddit('reddit.txt')

    res = pull_multiple_subreddits(reddit, last_post_dict, subreddits)
    print(res)

    save_dict(last_post_dict, 'last-upload.reddit')

