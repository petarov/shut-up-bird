#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import argparse
import json
import tweepy
import pystache
import webbrowser

CONFIG_FILE = '.shut-up-bird.conf'

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
    print("Authenticated as: {0}".format(api.me().screen_name))
    return api


def tweep_delete(api):
    print ("TEST")

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

def get_input(message):
    return raw_input(message)


###########################
# Main
#
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


    except Exception as e:
        print ("[ERROR] {0}".format(e))
