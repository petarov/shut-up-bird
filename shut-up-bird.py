#!/usr/bin/env python
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
from time import strftime, strptime
import dateparser
import pytz
import pystache
import tweepy
from ebooklib import epub

CONFIG_FILE = '.shut-up-bird.conf'
ARCHIVES_DIR = './shut-up-bird.arch'

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

            print ("Opening url - {0} ...".format(redirect_url))
            webbrowser.open(redirect_url)

            verify_code = raw_input("Verification PIN code: ")
            auth.get_access_token(verify_code)

        except tweepy.TweepError as e:
            raise Exception("Failed to get request token!", e)

    return auth

def tweep_getAPI(auth):
    api = tweepy.API(auth)

    print ("Authenticated as: {0}".format(api.me().screen_name))

    limits = api.rate_limit_status()
    statuses = limits['resources']['statuses']

    print ("Rates left:")
    print ("\tUser timeline: {0} / {1}".format(
        statuses['/statuses/user_timeline']['remaining'],
        statuses['/statuses/user_timeline']['limit']))
    print ("\tLookup: {0} / {1}".format(
        statuses['/statuses/lookup']['remaining'],
        statuses['/statuses/lookup']['limit']))

    return api

def tweep_archive(api, max_id=None, max_date=None,
    skip_retweets=False, skip_replies=False,
    remove=False, ascending=False):

    archive = archive_open(ARCHIVES_DIR, api.me())
    statuses = []
    delete_statuses = []

    try:
        for page in tweepy.Cursor(api.user_timeline, max_id=max_id).pages():
            for status in page:
                if max_date and pytz.utc.localize(status.created_at) > pytz.utc.localize(max_date):
                    print ("Skipped tweet {0} on {1}".format(
                        status.id_str, status.created_at))
                    continue

                if status.retweeted:
                    print ("Skipped retweet {0} on {1}".format(
                        status.id_str, status.created_at))
                    continue

                if status.in_reply_to_status_id and skip_replies:
                    print ("Skipped a reply tweet {0} on {1}".format(
                        status.id_str, status.created_at))
                    continue

                ##print (status)
                if ascending:
                    statuses.append(status)
                else:
                    archive_add(status, archive)

                if remove:
                    delete_statuses.append(str(status.id_str))

        # reverse add posts from the temp array
        if ascending:
            for status in reversed(statuses):
                archive_add(status, archive)

        if remove:
            tweep_delete_all(delete_statuses)

    except tweepy.RateLimitError as e:
        # TODO: save current state and make it possible to continue later
        raise Exception("Twitter API rate limit reached! No tweets will be deleted.", e)
    except ValueError as e:
        raise Exception("Could not parse status create time! No tweets were deleted.", e)

    archive_close(archive)

def tweep_delete_all(status_list):
    print ("Removing {0} statuses ...".format(len(status_list)))
    # TODO this could be put in a fork

def tweep_delete(status_id):
    print ("TEST")
    # TODO delete a tweet

#############################################################################
# Archive routines

def archive_open(dest_path, user):
    if not os.path.exists(dest_path):
        os.mkdir(dest_path)

    dir_path = os.path.join(dest_path, strftime("%Y-%m-%d_%H%M"))
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)

    # ePub Stuff
    book = epub.EpubBook()
    book.set_identifier('id' + str(user.id))
    book.set_title("Tweets by @" + user.screen_name)
    book.set_language(user.lang or 'en')

    book.add_author(user.name or user.screen_name)
    book.spine = ['nav']

    return {'book': book, 'dest': dir_path}

def archive_add(status, archive):
    book = archive['book']

    c = epub.EpubHtml(title='Intro', \
        file_name='chap_' + str(status.id_str) + '.xhtml', \
        lang=status.lang or 'en')

    #c.content = '<h1>' + excerpt(status.text) + '</h1>'
    c.content = preprocess(status.text)
    c.content += '<h6 align="center">' + status.created_at.strftime("%A, %d %b %Y %H:%M") + '</h6>'

    book.add_item(c)
    book.spine.append(c)

def archive_close(archive):
    epub_dest = os.path.join(archive['dest'], 'tweets.epub')
    print ("Writing ePub to {0} ...".format(epub_dest))

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
    parser.add_argument('-id', '--max-id',
        help="""Archives all statuses with an ID less than
        (older than) or equal to the specified.""")
    parser.add_argument('-dt', '--max-date',
        help="""Archives all statuses with a post date less than
        (older than) or equal to the specified.""")
    parser.add_argument('-a', '--asc',
        help="""Adds tweets in ascending date order.""",
        action="store_true", default=False)
    parser.add_argument('-rt', '--no-retweet',
        help="""Skips retweet posts.""",
        action="store_true", default=False)
    parser.add_argument('-re', '--no-reply',
        help="""Skips reply tweets.""",
        action="store_true", default=False)
    parser.add_argument('--remove',
        help="""Removes all archived tweets.
        WARNING!!! This action is irreversable!""",
        action="store_true", default=False)

    return parser

#############################################################################
# Misc routines

def get_input(message):
    return raw_input(message)

def preprocess(text):
    # thx dude! - stackoverflow.com/a/7254397
    text = re.sub(r'(?<!"|>)(ht|f)tps?://.*?(?=\s|$)',
        r'<a href="\g<0>">\g<0></a>', text)
    # thx dude! x2 - gist.github.com/mahmoud/237eb20108b5805aed5f
    text = re.sub(r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)',
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

        g_max_date = None

        g_parser = conf_get_parser()
        args = g_parser.parse_args()
        if not args.max_id and not args.max_date:
            g_parser.print_help()
            sys.exit(-1)
        elif args.max_date:
            g_max_date = dateparser.parse(args.max_date)
            print ("Max date set to: {0}".format(g_max_date))

        tweep_archive(tweep_getAPI(g_auth), max_id=args.max_id,
            max_date=g_max_date, skip_replies=args.no_reply,
            skip_retweets=args.no_retweet, ascending=args.asc)

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print ("[ERROR] {0}".format(e))
