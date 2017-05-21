#!/usr/bin/env python

from configparser import SafeConfigParser
from configparser import NoSectionError, NoOptionError
from markdown import markdown
import os, sys
from wordpress_xmlrpc import WordPressPost, Client
from wordpress_xmlrpc.methods.posts import NewPost
from wordpress_xmlrpc.exceptions import InvalidCredentialsError, ServerConnectionError
import argparse
import re

def read_config(configuration_parser):
    cparser = configuration_parser
    siteurl =  "%s/%s" % (cparser.get('wordpress_site','site'),"xmlrpc.php")
    username = cparser.get('wordpress_site','username')
    password = cparser.get('wordpress_site','password')
    return (siteurl, username, password)


def presser():
    parser = argparse.ArgumentParser(description='presser - to push wordpress posts from the commandline')
    parser.add_argument('--config', action='store', dest='configfile',default=None)
    parser.add_argument('--title', action='store', dest='title', default='A new post' )
    parser.add_argument('--posts', help='a space seperated list of post names', default=[], dest='posts_to_process',nargs='+')
    parser.add_argument('--status', choices=('draft', 'publish','private'),help='post status defaults to %(default)s', default='draft', dest='status')
    parser.add_argument('--no-parse', action="store_true", dest = 'no_parse', default=False, help = "defaults to False, if True the markup won't be parsed to html but uploaded as-is")
    parser.add_argument('--dry-run',action="store_true", dest = 'dry_run', default=False) 
    ## need to implent a fuller Usage description
    options = parser.parse_args()

    exit_msg = "Presser would exit now. run presser --help for commandline options"
    #parse configfile to wordpress
    #TODO: add an option to use commandline args instead of config file
    cparser = SafeConfigParser()
    try: #if there is a config option in commandline options or can be found walking the folders
        configfile = options.configfile
        if not configfile:
            configfile = find_config_file()
        cparser.read(configfile)
        siteurl, username, password = read_config(cparser)
    except (NoSectionError, NoOptionError) as e:
        print (e.message)
        print("missing configuration information or file, please input them now:")
        import getpass
        siteurl = '%s/%s' % (input("Full site url: "),"xmlrpc.php")
        username = input("Wordpress site username: ")
        password = getpass.getpass("Enter wordpress site password: ")
    
    #very basic, checking for http:// in the beginning, since this fails wordpress_xmprpc
    valid_url = re.match(r"^http://", siteurl)
    
    if not valid_url:
        siteurl = "".join(["http://", siteurl])
    # TODO: check for missing configs

    print ('connection settings:',"Site url: %s" % siteurl, "User name: %s" % username, sep="\n")
    
    #create a connection
    try:
        wp = Client(siteurl,username, password)
    except (IOError, ServerConnectionError) as e:
        print("Either a invalid wordpress site address or your site doesn't have the XML-RPC protocol turned on.", 
        exit_msg, sep="\n")
        sys.exit()
    
    if options.dry_run:
        print("Running a dry run, won't save any posts.")

    #send the parsed html to wordpress
    if len(options.posts_to_process) == 0:
        print("No posts to post",exit_msg ,sep="\n")
        sys.exit()

    for p in options.posts_to_process:
        with open(p,"r") as f:
            #TODO: add try block to check for encoded strings or files and then use codecs to open
            if not options.no_parse:
                text = markdown(f.read())
            else:
                text = f.read()
            f.close()

        post = WordPressPost()
        post.title =options.title
        post.content = text
        post.post_status = options.status
        if options.dry_run:
            print("Dry run mode:")
            print("Post name: %s.\n Post content:%s\n Post status:%s" % (post.title, post.content, post.post_status))
            print("If you really want to post try running not in 'dry run' mode")
            continue
        try:
            wp.call(NewPost(post))
            print ('Done uploading: %s' % p)
        except InvalidCredentialsError as e:
            print(e.message, exit_msg, sep="\n")
            sys.exit()

def find_config_file():
    #for root, dirs, files in os.walk(os.path.dirname(os.path.abspath("__file__"))):
    for root, dirs, files in os.walk(os.path.dirname(os.path.abspath("__file__"))):
        
        for f in files:
            if os.path.splitext(f)[1] == ".ini":
                print("Found and using config file: %s in %s" % (f,root)) #debug
                return os.path.join(root, f)

if __name__ == '__main__':
   presser()