# Shut Up Bird

Archives your tweets in an [EPUB](https://en.wikipedia.org/wiki/EPUB) book and then optionally deletes them.

Things you could do:

  * Get rid of your old _tweets_ or _likes_ but still have them nicely organized somewhere.
  * An annual archive of your twitter activty.
  * Setup a cron job to regularly clean up your status.
  * Archive someone else's tweets for your own viewing pleasure.
  * Read your own tweets in your favourite e-book reader app and cry. 

# Installation

Requires Python `2.7` or `3.x`.

## Packages

To install on **ArchLinux** from [AUR](https://aur.archlinux.org/packages/shut-up-bird) run:

    yaourt -S shut-up-bird

## Manual

Run `make` or `pip install -r requirements.txt`.

# Setup

Create a new [Twitter application](https://apps.twitter.com/). The name shouldn't matter.

Open the app's `Permissions` page and make sure `Read and Write` is selected, otherwise `shut-up-bird` will not be able to delete anything.

Run without any parameters to initialize:

    $ python shut-up-bird.py
    Please provide your Twitter app access keys

Enter the consumer API key:

    Consumer API Key: <25-chars>

Enter the consumer API secret:

    Consumer API Secret: <50-chars>

A Twitter authentication request page should automatically open in your browser. If not or if you're running this on a server, open the url generated below in your browser.

    Authenticating ...please wait
    Opening url - https://api.twitter.com/oauth/authorize?oauth_token=<token>

Accept the Twitter authorization request and enter the verification code back in the console:

    Verification PIN code: 7654321

All authorization parameters will now be saved to your home directory in `~/.shut-up-bird.conf`.

That's it. You're ready to go. :ok_hand:

# Usage

Show help :eyes:

    python shut-up-bird.py -h 
    
Archive all of your tweets until `Dec 31, 2014` and then delete them from Twitter. Tweets will be saved in ascending date order. Verbose logs will be displayed.

    python shut-up-bird.py -v --max-date "2014-12-31" --asc --remove 

Archive all of your likes until `Dec 31, 2014` and then delete them from Twitter. Likes will be saved in ascending date order. Verbose logs will be displayed.

    python shut-up-bird.py -v --likes --max-date "2014-12-31" --asc --remove

Archive all of your tweets posted before the tweet with id `123456789012345678`. Tweets will be saved in descending date order. No tweets will be deleted.

    python shut-up-bird.py -v -id 123456789012345678

The same as above but skips all replies and retweets.

    python shut-up-bird.py -v -id 123456789012345678 -rt -re

Generated `epub` files are found in the sub folder `./shut-up-bird.arch`, e.g., `./shut-up-bird.arch/2017-03-05_1000/tweets.epub`.

Note that you must explicitly specify the `--remove` parameter in order to delete tweets or likes. To prevent inconsistencies, tweets or likes will be deleted only after an `epub` file was successfully created first.

# License

[MIT License](LICENSE)

## Disclaimer

    Please note that I SHALL NOT be held liable in case you lose your data using this script! 
