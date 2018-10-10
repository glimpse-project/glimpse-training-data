#!/usr/bin/env python3

import csv
import fnmatch
import re


# Nabbed from:
# https://stackoverflow.com/questions/29916065/how-to-do-camelcase-split-in-python
def camel_and_dromedary_case_split(identifier):
    RE_WORDS = re.compile(r'''
        # Find words in a string. Order matters!
        [A-Z]+(?=[A-Z][a-z]) |  # All upper case before a capitalized word
        [A-Z]?[a-z]+ |  # Capitalized words / all lower case
        [A-Z]+ |  # All upper case
        \d+  # Numbers
    ''', re.VERBOSE)
    return RE_WORDS.findall(identifier)


with open('cmu-mocap-index.csv', 'r') as fp:
    csv_reader = csv.reader(fp)
    for row in csv_reader:
        blacklist_note = None

        name = row[0]

        if not fnmatch.fnmatch(name, '??_??'):
            continue

        desc = row[1]

        # Non-trivial composites to tag...
        # XXX: we should probably blacklist these
        if 'vignettes' in desc or ',' in desc:
            blacklist_note = "Composite"

        desc_words = []
        for word in re.findall(r"[\w']+", desc):
            if word == 'bck':
                desc_words += [ "back" ]
            elif word == 'flp':
                desc_words += [ "flip" ]
            elif word == 'twst':
                desc_words += [ "twist" ]
            elif word.lower() == "cleanedgrs":
                desc_words += [ "cleaned_grs" ]
            elif re.match(r"^[A-Za-z]+$", word) and re.match(r".*[A-Z].*", word):
                desc_words += [x.lower() for x in camel_and_dromedary_case_split(word)]
            else:
                desc_words += [ word ]

        i=0
        while i < len(desc_words) - 1:
            if desc_words[i] == "back" and desc_words[i+1] == "flip":
                desc_words = desc_words[:i] + [ "backflip" ] + desc_words[i+2:]
            elif desc_words[i] == "t" and desc_words[i+1] == "pose":
                desc_words = desc_words[:i] + [ "t_pose" ] + desc_words[i+2:]
            i+=1

        subject = row[2]
        subject_words = [x.lower() for x in re.findall(r"[\w']+", subject)]

        tags = []

        if blacklist_note == None:
            if 'walk' in desc_words:
                tags += [ 'walk' ]
            if 'run' in desc_words:
                tags += [ 'run' ]
            if 'march' in desc_words:
                tags += [ 'march' ]
            if 'basketball' in desc_words:
                tags += [ 'basketball' ]
            if 'soccer' in desc_words:
                tags += [ 'soccer', 'football' ]
            if 'boxing' in desc_words:
                tags += [ 'boxing' ]
            if 'kick' in desc_words:
                tags += [ 'kick' ]
            if 'jump' in desc_words or 'jumping' in desc_words:
                tags += [ 'jump' ]
            if 'climb' in desc_words:
                tags += [ 'climb' ]
            if 'backflip' in desc_words:
                tags += [ 'backflip' ]
            if 'cartwheel' in desc_words:
                tags += [ 'cartwheel' ]
            if 'dance' in desc_words:
                tags += [ 'dance' ]
                if 'salsa' in desc_words:
                    tags += [ 'dance_salsa' ]
            if 'golf' in subject_words:
                tags += [ 'golf' ]
                if 'swing' in desc_words:
                    tags += [ 'golf_swing' ]
                if 'putt' in desc_words:
                    tags += [ 'golf_putt' ]

        if blacklist_note:
            #print("%s: Desc: %-60s Subject: %-58s BLACKLIST - %s" % (name, '"' + desc + '"', '"' + subject[8:] + '"', blacklist_note))
            print('../glimpse-mocap-indexer.py -m %s --blacklist ./index.json' % name)
        else:
            #print("%s: Desc: %-60s Words: %-60s Subject: %-50s Tags: %s" % (name, '"' + desc + '"', desc_words, '"' + subject[8:] + '"', ', '.join(tags)))
            if len(tags):
                print('../glimpse-mocap-indexer.py -m %s --untag unknown -t auto_tag -t cmu -t %s ./index.json' % (name, ' -t '.join(tags)))

