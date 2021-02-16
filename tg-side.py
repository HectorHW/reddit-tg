import os
import string
import warnings

import telegram
from telegram.ext import Updater, Dispatcher, CallbackContext

if __name__ == '__main__':
    with open('token.txt') as f:
        token = f.read().strip()

    updater = Updater(token=token, use_context=True)

    dispatcher:Dispatcher = updater.dispatcher

    import logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    def start(update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text="booba")

    from telegram.ext import CommandHandler

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)


    def bruh_callback(update, context:CallbackContext):
        photo_link = "https://steamuserimages-a.akamaihd.net/ugc/785237465823382315/23C44FA9648B9C5D7564D6F122EC226D4659F204/"
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_link)

    dispatcher.add_handler(CommandHandler('bruh', bruh_callback))

    def got_message(update, context):

        if update.channel_post is not None: # post in channel

            check_key(update.channel_post)
            if update.channel_post.text is not None:
                print(f"{update.channel_post.sender_chat.title}: {update.channel_post.text}")

        elif update.message is not None: # message
            check_key(update.message)
            print(f"{update.message.from_user.username}: {update.message.text}")

    from telegram.ext import MessageHandler, Filters

    msg_handler = MessageHandler(Filters.text & (~Filters.command), got_message)

    dispatcher.add_handler(msg_handler)

    updater.start_polling()

    CHAT_ID = None
    AWAIT_SALT = False
    KEY = ''

    if os.path.exists('last_chat.txt'):
        with open('last_chat.txt') as f:
            try:
                CHAT_ID = int(f.read().strip())
                print("loaded CHAT_ID from file")
            except ValueError:
                pass


    def command_verify():
        import random
        base = string.ascii_lowercase+string.digits
        global KEY
        KEY = ''.join(random.choice(base) for _ in range(8))
        global CHAT_ID


        print(f"generated key: {KEY}")
        global AWAIT_SALT

        while True:
            print("press ENTER to continue or type cancel to cancel verification")
            s = input()
            if s.lower()=='cancel':
                print('cancelled verification, set AWAIT_SALT to False')
                AWAIT_SALT = False
                return
            elif s=='':
                AWAIT_SALT = True
                print("set AWAIT_SALT to True")
                print("salt confirmed, now just type key in desired chat")
                return

    def check_key(msg:telegram.Message):

        global AWAIT_SALT

        if not AWAIT_SALT:
            return

        global CHAT_ID

        if msg.text is not None and msg.text==KEY:
            print(f'verified chat: {msg.chat.title or msg.chat.username}')
            CHAT_ID = msg.chat.id
            print("set AWAIT_SALT to False")
            AWAIT_SALT = False
            with open('last_chat.txt', 'w') as f:
                f.write(str(CHAT_ID))
            print("overwritten last_chat.txt")


    def command_say(s:str):
        if CHAT_ID is None:
            warnings.warn("CHAT_ID is not set, provide it with  last_chat.txt file or /verify")
        else:
            updater.bot.send_message(chat_id=CHAT_ID, text=s)


    def load_subreddits(filename):
        with open(filename) as f:
            return [s.strip() for s in f.readlines()]

    def save_subreddits(filename, l):
        with open(filename, 'w') as f:
            f.write('\n'.join(l))

    from reddit_pooler import RedditPooler

    if os.path.exists('subreddits.txt'):
        SUBREDDITS = load_subreddits('subreddits.txt')
        print('loaded subreddits from file')
    else:

        SUBREDDITS = [
            'Genshin_Impact', 'megane', 'wholesomeanimemes'
        ]
        print(f'no subreddits.txt found, using standart list {SUBREDDITS}')
    from threading import Thread, Lock
    subreddits_mutex = Lock()
    pooler = RedditPooler(updater, CHAT_ID, SUBREDDITS, subreddits_mutex)

    def list_callback(update, context:CallbackContext):
        if CHAT_ID is None or CHAT_ID!=update.effective_chat.id:
            return
        subreddits_mutex.acquire()
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(pooler.subreddits))
        subreddits_mutex.release()

    dispatcher.add_handler(CommandHandler('list', list_callback))

    def add_callback(update, context:CallbackContext):
        if CHAT_ID is None or CHAT_ID!=update.effective_chat.id:
            return
        subreddit = 'megane'
        if update.channel_post is not None: # post in channel
            if update.channel_post.text is not None:
                print(f"{update.channel_post.sender_chat.title}: {update.channel_post.text}")
                subreddit = update.channel_post.text.split(" ")[-1]

        elif update.message is not None: # message
            print(f"{update.message.from_user.username}: {update.message.text}")
            subreddit = update.message.text.split(" ")[-1]


        subreddits_mutex.acquire()
        pooler.subreddits = list( set(pooler.subreddits).union([subreddit]))
        subreddits_mutex.release()
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'added {subreddit}')

    dispatcher.add_handler(CommandHandler('add', add_callback))

    def remove_callback(update, context:CallbackContext):
        if CHAT_ID is None or CHAT_ID!=update.effective_chat.id:
            return

        subreddit = 'megane'
        if update.channel_post is not None: # post in channel
            if update.channel_post.text is not None:
                print(f"{update.channel_post.sender_chat.title}: {update.channel_post.text}")
                subreddit = update.channel_post.text.split(" ")[-1]

        elif update.message is not None: # message
            print(f"{update.message.from_user.username}: {update.message.text}")
            subreddit = update.message.text.split(" ")[-1]


        subreddits_mutex.acquire()
        pooler.subreddits = list( set(pooler.subreddits).difference([subreddit]))
        subreddits_mutex.release()
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'removed {subreddit}')

    dispatcher.add_handler(CommandHandler('remove', remove_callback))

    def save_callback(update, context:CallbackContext):
        if CHAT_ID is None or CHAT_ID!=update.effective_chat.id:
            return

        subreddits_mutex.acquire()
        save_subreddits('subreddits.txt', pooler.subreddits)
        subreddits_mutex.release()
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'saved to file')

    dispatcher.add_handler(CommandHandler('save', save_callback))

    def load_callback(update, context:CallbackContext):
        if CHAT_ID is None or CHAT_ID!=update.effective_chat.id:
            return

        subreddits_mutex.acquire()
        pooler.subreddits = load_subreddits('subreddits.txt')
        subreddits_mutex.release()
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'loaded from file')

    dispatcher.add_handler(CommandHandler('save', save_callback))


    thread = Thread(target=pooler.run)

    help_msg = """
    
    say to type to saved chat
    
    verify to verify channel
    
    stop to stop the bot
    
    """
    print(help_msg)

    thread_is_running = False

    while True:

        if CHAT_ID is not None and not thread_is_running:
            thread_is_running = True
            pooler.chat_id = CHAT_ID
            thread.start()

        s = input()

        if s=="stop":
            break
        if s.startswith("say"):
            command_say(s.split(' ', 1)[-1])

        elif s.startswith("verify"):
            command_verify()
        else:
            print(help_msg)

    #TODO fix stopping

    pooler.stop()
    thread.join()

    updater.stop()






