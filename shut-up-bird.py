#!/usr/bin/env python
# coding: utf-8
# pylint: disable=C0111
# pylint: disable=C0103
# pylint: disable=C0330

from __future__ import print_function
import os
import sys
import argparse
import traceback
import webbrowser
import re
import json
import multiprocessing
from multiprocessing.pool import ThreadPool
from time import strftime
import dateparser
import pytz
import tweepy
from ebooklib import epub

VERSION = '1.0'
CONFIG_FILE = '.shut-up-bird.conf'
ARCHIVES_DIR = './shut-up-bird.arch'
TWEETS_EPUB = 'tweets.epub'
LIKES_EPUB = 'likes.epub'

PAR_TWEET = u'<blockquote class="ieverse"><p style="text-align:center;">\
    <span style="text-align:left;display:inline-block;">{0}</span></p>\
    </blockquote>'

#############################################################################
# Tweepy routines

def tweep_login(consumer_key, consumer_secret, token='', secret=''):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)

    if token and secret:
        auth.set_access_token(token, secret)
    else:
        try:
            print ("Authenticating ...please wait")
            redirect_url = auth.get_authorization_url()

            print ("Opening url - {0}".format(redirect_url))
            webbrowser.open(redirect_url)

            verify_code = get_input("Verification PIN code: ")
            auth.get_access_token(verify_code)

        except tweepy.TweepError as e:
            raise Exception("Failed to get request token!", e)

    return auth

def tweep_getAPI(auth):
    api = tweepy.API(auth)

    verbose("Authenticated as: {0}".format(api.me().screen_name))

    limits = api.rate_limit_status()
    statuses = limits['resources']['statuses']

    verbose("Rates left:")
    verbose("\tUser timeline: {0} / {1}".format(
        statuses['/statuses/user_timeline']['remaining'],
        statuses['/statuses/user_timeline']['limit']))
    verbose("\tLookup: {0} / {1}".format(
        statuses['/statuses/lookup']['remaining'],
        statuses['/statuses/lookup']['limit']))
    # verbose("\tMentions timeline: {0} / {1}".format(
    #     statuses['/statuses/mentions_timeline']['remaining'],
    #     statuses['/statuses/mentions_timeline']['limit']))
    # verbose("\tRetweets: {0} / {1}".format(
    #     statuses['/statuses/retweets/:id']['remaining'],
    #     statuses['/statuses/retweets/:id']['limit']))

    return api

def tweep_archive_tweets(api, max_id=None, max_date=None,
    skip_retweets=False, skip_replies=False,
    remove=False, ascending=False):

    archive = archive_open(ARCHIVES_DIR, api.me())
    statuses = []
    delete_statuses = []

    print ("Archiving {0} tweets ...".format(api.me().screen_name))

    try:
        for page in tweepy.Cursor(api.user_timeline, max_id=max_id).pages():
            for status in page:
                if max_date and pytz.utc.localize(status.created_at) > pytz.utc.localize(max_date):
                    verbose("Skipped tweet {0} on {1}".format(
                        status.id_str, status.created_at))
                    continue

                if status.retweeted and skip_retweets:
                    verbose("Skipped retweet {0} on {1}".format(
                        status.id_str, status.created_at))
                    continue

                if status.in_reply_to_status_id and skip_replies:
                    verbose("Skipped a reply tweet {0} on {1}".format(
                        status.id_str, status.created_at))
                    continue

                if ascending:
                    statuses.append(status)
                else:
                    archive_add(archive, status)

                if remove:
                    delete_statuses.append(status.id)

        # reverse add posts from the temp array
        if ascending:
            for status in reversed(statuses):
                archive_add(archive, status)

        archive_close(archive)

        if remove:
            tweep_delete_all(api, delete_statuses, tweep_delete_tweet)

    except tweepy.RateLimitError as e:
        raise Exception("Twitter API rate limit reached!", e)
    except ValueError as e:
        raise Exception("Could not parse status create time!", e)

def tweep_archive_likes(api, max_date=None, remove=False, ascending=False):
    archive = archive_open(ARCHIVES_DIR, api.me(), isLikes=True)
    likes = []
    delete_likes = []

    print ("Archiving {0} likes ...".format(api.me().screen_name))

    try:
        for page in tweepy.Cursor(api.favorites).pages():
            for like in page:
                if max_date and pytz.utc.localize(like.created_at) > pytz.utc.localize(max_date):
                    verbose("Skipped like {0} on {1}".format(
                        like.id_str, like.created_at))
                    continue

                if ascending:
                    likes.append(like)
                else:
                    archive_add(archive, like, addAuthor=True)

                if remove:
                    delete_likes.append(like.id)

        # reverse add likes from the temp array
        if ascending:
            for like in reversed(likes):
                archive_add(archive, like, addAuthor=True)

        archive_close(archive)

        if remove:
            tweep_delete_all(api, delete_likes, tweep_delete_like)

    except tweepy.RateLimitError as e:
        raise Exception("Twitter API rate limit reached!", e)
    except ValueError as e:
        raise Exception("Could not parse like create time!", e)

def tweep_delete_all(api, posts, func):
    try:
        cpus = multiprocessing.cpu_count()
    except NotImplementedError:
        cpus = 2    # default

    print ("Removing {0} entries in {1} parallel threads ...".format(
        len(posts), cpus))

    pool = ThreadPool(processes=cpus)
    for status_id in posts:
        pool.apply_async(func, args=(api, status_id,))

    pool.close()
    pool.join()

def tweep_delete_tweet(api, status_id):
    verbose("Deleting status {0}".format(status_id))
    try:
        api.destroy_status(status_id)
    except Exception as e:
        print ("[ERROR] {0}".format(e))

def tweep_delete_like(api, like_id):
    verbose("Removing like {0}".format(like_id))
    try:
        api.destroy_favorite(like_id)
    except Exception as e:
        print ("[ERROR] {0}".format(e))

#############################################################################
# Archive routines

def archive_open(dest_path, user, isLikes=False):
    if not os.path.exists(dest_path):
        os.mkdir(dest_path)

    dir_path = os.path.join(dest_path, strftime("%Y-%m-%d_%H%M"))
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)

    # ePub Stuff
    book = epub.EpubBook()
    book.set_identifier('id' + str(user.id))
    book.set_title(("Tweets by" if not isLikes else "Twitter Likes of") + " @" + user.screen_name)
    book.set_language(user.lang or 'en')

    book.add_author(user.name or user.screen_name)
    book.spine = ['nav']

    return {'book': book, 'dest': dir_path,
        'filename': LIKES_EPUB if isLikes else TWEETS_EPUB}

def archive_add(archive, status, addAuthor=False):
    book = archive['book']

    c = epub.EpubHtml(title='Intro', \
        file_name='chap_' + str(status.id_str) + '.xhtml', \
        lang=status.lang or 'en')

    c.content = ''

    if addAuthor and status.author:
        screen_name = preprocess('@' + str(status.author._json['screen_name'].encode('utf8')))
        c.content = "<h5 align='center'>{0}</h5>".format(screen_name)

    c.content += preprocess(status.text)
    c.content += '<h6 align="center">' + status.created_at.strftime("%A, %d %b %Y %H:%M") + '</h6>'

    book.add_item(c)
    book.spine.append(c)

def archive_close(archive):
    epub_dest = os.path.join(archive['dest'], archive['filename'])
    print ("Saving ePub to {0} ...".format(epub_dest))

    # add navigation files
    archive['book'].add_item(epub.EpubNcx())
    archive['book'].add_item(epub.EpubNav())

    epub.write_epub(epub_dest, archive['book'], {})
    return epub_dest

#############################################################################
# Config routines

def config_load(config_path):
    if not os.path.exists(config_path):
        return False

    with open(config_path, 'r') as infile:
        return json.load(infile)

def config_save(config_path, consumer_key, consumer_secret, token, secret):
    data = {'ck': consumer_key, 'cs': consumer_secret, \
        't': token, 's': secret}

    with open(config_path, 'w') as outfile:
        json.dump(data, outfile, indent=2, ensure_ascii=False)

def conf_get_parser():
    parser = argparse.ArgumentParser(add_help=True,
        description="So you're stuck, eh? Here're some hints.")
    parser.add_argument('-V', '--version',
        help="""prints how old Smeagol is""",
        action="store_true", default=False)
    parser.add_argument('-v', '--verbose',
        help="""verbose (See what's happening)""",
        action="store_true", default=False)
    parser.add_argument('-id', '--max-id',
        help="""archives all statuses with an ID less than
        (older than) or equal to the specified""")
    parser.add_argument('-l', '--likes',
        help="""archives likes only""",
        action="store_true", default=False)
    parser.add_argument('-dt', '--max-date',
        help="""archives all statuses or likes with a post date earlier than
        or equal to the specified. Sample format: 2016-11-01 23:00:00+02:00""")
    parser.add_argument('-a', '--asc',
        help="""adds tweets in ascending date order""",
        action="store_true", default=False)
    parser.add_argument('-rt', '--no-retweet',
        help="""skips retweets""",
        action="store_true", default=False)
    parser.add_argument('-re', '--no-reply',
        help="""skips reply tweets""",
        action="store_true", default=False)
    parser.add_argument('--remove',
        help="""removes all archived tweets.
        *** WARNING!!! This action is irreversible! ***""",
        action="store_true", default=False)

    return parser

#############################################################################
# Misc routines

def verbose(message):
    if g_verbose:
        print (message)

def get_input(message):
    try:
        return raw_input(message)
    except NameError:
        return input(message)

def preprocess(text):
    # thx dude! - stackoverflow.com/a/7254397
    text = re.sub(r'(?<!"|>)(ht|f)tps?://.*?(?=\s|$)',
        r'<a href="\g<0>">\g<0></a>', text)
    # thx dude! x2 - gist.github.com/mahmoud/237eb20108b5805aed5f
    text = re.sub(r'(?:^|\s)[@]{1}([^\s#<>[\]|{}]+)',
        r'<a href="https://twitter.com/\1">@\1</a>', text)
    text = re.sub(r'(?:^|\s)[#]{1}(\w+)',
        r' <a href="https://twitter.com/hashtag/\1">#\1</a>', text)
    return PAR_TWEET.format(text)

def excerpt(text):
    text = re.sub(r'@(.*?)\S*', '', text)
    return text[0:15] + ' ...'

#############################################################################
# Main
if __name__ == "__main__":
    try:
        home_dir = os.path.expanduser('~')
        config = config_load(os.path.join(home_dir, CONFIG_FILE))

        if config and config['t'] and config['s']:
            g_auth = tweep_login(config['ck'], config['cs'], config['t'], config['s'])
        else:
            print ("Please provide your Twitter app access keys\n")
            g_consumer_key = get_input("Consumer API Key: ")
            g_consumer_secret = get_input("Consumer API Secret: ")

            g_auth = tweep_login(g_consumer_key, g_consumer_secret)

            config_save(os.path.join(home_dir, CONFIG_FILE), g_consumer_key, \
                g_consumer_secret, g_auth.access_token, g_auth.access_token_secret)

        g_parser = conf_get_parser()
        args = g_parser.parse_args()
        g_verbose = args.verbose
        g_max_date = None

        if args.version:
            print ('{} {}'.format(
                os.path.basename(__file__).rstrip('.py'), VERSION))
            sys.exit(-1)
        elif not args.max_id and not args.max_date and not args.likes:
            g_parser.print_help()
            sys.exit(-1)
        elif args.max_date:
            g_max_date = dateparser.parse(args.max_date)
            verbose("** All entries till: {0}".format(g_max_date))

        if args.remove:
            print ("** WARNING: Archvied statuses will be removed from your Twitter account!")

        if args.likes:
            tweep_archive_likes(tweep_getAPI(g_auth),
                max_date=g_max_date, ascending=args.asc, remove=args.remove)
        else:
            tweep_archive_tweets(tweep_getAPI(g_auth), max_id=args.max_id,
                max_date=g_max_date, skip_replies=args.no_reply,
                skip_retweets=args.no_retweet, ascending=args.asc,
                remove=args.remove)

    except tweepy.TweepError as e:
        traceback.print_exc(file=sys.stdout)
        print ("[ERROR] {0}".format(e))
        if e.response.status_code == 429:
            print ("""The maximum number of requests that are allowed is based on a time interval, some specified period or window of time. The most common request limit interval is fifteen minutes. If an endpoint has a rate limit of 900 requests/15-minutes, then up to 900 requests over any 15-minute interval is allowed.""")
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print ("[ERROR] {0}".format(e))
