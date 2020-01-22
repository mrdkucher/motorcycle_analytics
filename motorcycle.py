# pylint: disable=no-member
import feedparser, ssl

import argparse

import sqlite3

import re

from twisted.internet import reactor, defer
from twisted.application import service, internet

from datetime import datetime

def parse_feed(url):
    #if hasattr(ssl, '_create_unverified_context'):
    #    ssl._create_default_https_context = ssl._create_unverified_context
    
    feed = feedparser.parse(url)
    clean_feed(feed)
    return feed
    
def clean_feed(feed):
    for post in feed.entries:
        for item in post:
            if isinstance(post[item], str):
                # replace dollar sign code with '$'
                post[item] = post[item].replace("&#x0024;", "$")
                # replace ' with "
                post[item] = post[item].replace("'", "\"")

class MotorcycleAnalytics(object):
    db = None
    feed = None

    def get_db(self, name):
        self.db = sqlite3.connect(name)

    def get_feed(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--url',
            default='https://chicago.craigslist.org/search/mca?format=rss&max_price=1500&min_price=200')
        
        args = parser.parse_args()
        self.feed = parse_feed(args.url)

    def insertNewMotorcycles(self):
        c = self.db.cursor()
        if not self.checkTableExists('motorcycles'):
            # Create table

            c.execute('''CREATE TABLE motorcycles
                (title text, text text, link text,
                price integer, photo text, location text,
                region text, city text, date_posted text, date_updated text);''')

        # Insert new rows into table
        #print(self.feed.entries[0])
        # categories:
            # title(str):           post title
            # id(str):              link
            # summary(str):         post text
            # updated(str):         UTC time updated
            # published(str):       UTC time posted
            # enc_enclosure(dict):  reources/images
        #region = re.split('\\', self.feed.entries[-1].id)
        #print(region)

        for post in self.feed.entries:
            title, location, price, city, region = self.split_titles(post.title, post.id)

            # check for image:
            image = ''
            try:
                image = post.enc_enclosure['resource']
            except AttributeError:
                pass
            
            result = c.execute("SELECT 1 FROM motorcycles WHERE title = {};".format(repr(title)))
            if result.fetchone() is None:
                command = ('INSERT into motorcycles VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {});'
                    .format(repr(title), repr(post.summary), repr(post.id), price,
                    repr(image), repr(location), repr(region),
                    repr(city), repr(post.published), repr(post.updated)))
                try:
                    c.execute(command)
                except Exception as e:
                    print(e)
                    print(command)
        
        c.close
        
        # Save (commit) the changes
        self.db.commit()
        
        #self.db.close()

    def split_titles(self, post_title, post_id):
        #print(post.title, post.id)
        split_title = re.split('\(|\)| \$', post_title) # need to beef up this split for location
        try:
            price = int(split_title[-1])
            location = split_title[-3]
        except ValueError: # this case doesn't actually exist....
            price = int(split_title[-3])
            location = split_title[-1]
        except IndexError:
            location = ''
            
        # Remove Price and Location from title
        title = re.split('\$', post_title[::-1], maxsplit=1)[-1]
        split_title = re.split('\(', title, maxsplit=1)
        title = split_title[-1][:0:-1] # reverse back and take off extra space

        # https, '', city, region
        split_url = re.split('.craigslist.org\/|\/', post_id)
        city = split_url[2]
        region = split_url[3]
        return title, location, price, city, region


    def checkTableExists(self, name):
        res = self.db.execute('SELECT name FROM sqlite_master WHERE type=\'table\';')
        for table_name in res:
            if table_name[0] == name:
                return True
        return False
    
    def printAllRows(self):
        c = self.db.cursor()

        result = c.execute('SELECT * FROM motorcycles;')
        for row in result:
            print(row)
        
        c.close()
        


#@defer.inlineCallbacks
def main_twisted():
    m = MotorcycleAnalytics()
    m.get_db('motos.db')
    m.get_feed()
    m.insertNewMotorcycles()
    #m.printAllRows()
    
    m.db.close()
    
    #reactor.stop()

#reactor.callLater(0, main_twisted)
main_twisted()
