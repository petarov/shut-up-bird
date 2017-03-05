# Shut Up Bird

Archive and delete your Twitter posts.

Do you want to get rid of your old tweets but still have them nicely packed somewhere?

This tool creates an [ePub](https://en.wikipedia.org/wiki/EPUB) format e-book for all your selected tweets and then (optionally) deletes them from Twitter. 

# Installation

Requires Python 2.7.

Run `make` or `pip install -r requirements.txt`.

# Setup

Create a new [Twitter application](https://apps.twitter.com/). The name doesn't matter.

Open the new Twitter app's `Permissions` page and make sure `Read, Write and Access direct messages` 
is selected, otherwise the tool will not be able to delete any tweets.

Run without any parameters to initialize the tool:

    $ python2 shut-up-bird.py
    Please provide your Twitter app access keys

Enter the consumer API key:

    Consumer API Key: <25-chars>

Enter the consumer API secret:

    Consumer API Secret: <50-chars>

A Twitter authentication request page should automatically open in your browser. 
If not, or if you're running this on a server somewhere, open the url generated below in a browser yourself.

    Authenticating ...please wait
    Opening url - https://api.twitter.com/oauth/authorize?oauth_token=<token>

Accept the Twitter authorization request and copy the verification code back to the console:

    Verification PIN code: 7654321

All authorization parameters will be saved to your home directory, i.e., `~/.shut-up-bird.conf`.

That's it. You're ready to go.

# Usage

Show help

    python2 shut-up-bird.py -h 

Archive all tweets older than the tweet with id `123456789012345678`. 
Tweets will be saved in descending date order. No tweets will be deleted.

    python2 shut-up-bird.py -v -id 123456789012345678

The same as above but skips all replies and retweets.

    python2 shut-up-bird.py -v -id 123456789012345678 -rt -re

Archive all tweets up to `Dec 31, 2014` and then delete them from Twitter. 
Tweets will be saved in ascending date order. Verbose messages will be displayed.

    python2 shut-up-bird.py -v --max-date "2014-12-31" --asc --remove 

Archive all likes up to `Dec 31, 2014` and then delete them from Twitter. 
Likes will be saved in ascending date order. Verbose messages will be displayed.

    python2 shut-up-bird.py -v --likes --max-date "2014-12-31" --asc --remove

Generated ePub files can be found in the sub folder `./shut-up-bird.arch`, e.g., `./shut-up-bird.arch/2017-03-05_1000/tweets.epub`.

Note that you must explicitly specify the `-remove` option in order to delete tweets or likes.
Tweets or likes will be deleted only after an ePub e-book was successfully created.

# License

[MIT License](LICENSE)

## Disclaimer

    Please note that I SHALL NOT be held liable in case you lose your data using this script! 
