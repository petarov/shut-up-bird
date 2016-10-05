#!/usr/bin/env python

from __future__ import print_function
import os
import sys, traceback
from time import gmtime, strftime
import argparse
import json
import tweepy
import pystache
import webbrowser
import re
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

            verify_code = raw_input("Verification PIN code: ".format(redirect_url))
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
    print ("\tUser timeline: {0} / {1}".format(statuses['/statuses/user_timeline']['remaining'], statuses['/statuses/user_timeline']['limit']))
    print ("\tLookup: {0} / {1}".format(statuses['/statuses/lookup']['remaining'], statuses['/statuses/lookup']['limit']))

    return api

def tweep_archive(api):
    archive = archive_open(ARCHIVES_DIR, api.me())

    try:
        for status in tweepy.Cursor(api.user_timeline).items(10):
            archive_add(status, archive)
    except tweepy.RateLimitError as e:
        # TODO proper reaction?
        raise Exception("Rate limit reached!", e)

    archive_close(archive)

def tweep_delete(status):
    print ("TEST")
    # TODO this could be put in a fork

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
    book.set_title('Tweets by @' + user.screen_name)
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

#############################################################################
# Config routines

def config_load(config_path):
    if not os.path.exists(config_path):
        return False

    with open(config_path, 'r') as infile:
        return json.load(infile)

def config_save(config_path, consumer_key, consumer_secret, token, secret):
    data = {'ck': consumer_key, 'cs': consumer_secret, \
        't': token, 's': secret }

    with open(config_path, 'w') as outfile:
        json.dump(data, outfile, indent=2, ensure_ascii=False)

#############################################################################
# Misc routines

def get_input(message):
    return raw_input(message)

def preprocess(text):
    # thx SO dude - http://stackoverflow.com/a/7254397
    text = re.sub('(?<!"|>)(ht|f)tps?://.*?(?=\s|$)', '<a href="\g<0>">\g<0></a>', text)
    text = re.sub('@(.*?)\S*', '<a href="https://twitter.com/\g<0>">\g<0></a>', text) # TODO remove the @
    return PAR_TWEET.format(text)

def excerpt(text):
    text = re.sub('@(.*?)\S*', '', text)
    return text[0:15] + ' ...'


#############################################################################
# Main
if __name__ == "__main__":
    try:
        home_dir = os.path.expanduser('~')
        config = config_load(os.path.join(home_dir, CONFIG_FILE))

        if (config and config['t'] and config['s']):
            auth = tweep_login(config['ck'], config['cs'], config['t'], config['s'])
        else:
            print ("Please provide your Twitter app access keys\n")
            consumer_key = get_input("Consumer Key (API Key): ")
            consumer_secret = get_input("Consumer Secret (API Secret): ")

            auth = tweep_login(consumer_key, consumer_secret)

            config_save(os.path.join(home_dir, CONFIG_FILE), consumer_key, \
                consumer_secret, auth.access_token, auth.access_token_secret)

        api = tweep_getAPI(auth)

        # TODO get input!?

        tweep_archive(api)

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print ("[ERROR] {0}".format(e))
