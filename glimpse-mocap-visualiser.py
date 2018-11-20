#!/usr/bin/env python3
#
# Copyright (c) 2018 Glimp IP Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# This lets us inspect the distribution of different tags across our indexed
# mocap sequences.

import os
import sys
import ntpath
import argparse
import json
import pprint
import random

parser = argparse.ArgumentParser()

parser.add_argument("-s", "--start", type=int, default=0, help="Start range (negative values are relative to end of index)")
parser.add_argument("-e", "--end", type=int, default=0, help="End range (zero means to go to the end of the index, negative values are relative to end of index)")
parser.add_argument('--tags-whitelist', default='all', help='A set of tags for index entries that will be included in ratio calculation - needs to be comma separated (default \'all\')')
parser.add_argument('--tags-blacklist', default='blacklist', help='A set of tags for index entries that will NOT be included in ratio calculation - needs to be comma separated (default \'blacklist\')')
parser.add_argument('--skip-percentage', type=int, default=0, help='(random) percentage of frames to skip (default 0)')
parser.add_argument('--tags-skip', nargs='+', action='append', help='(random) tag-based percentage of frames to skip (default \'none\'). The tags and percentages need to be provided in a <tag>=<integer> space separated format.')   
parser.add_argument("--show-stats", action="store_true", help="Output statistics at the top")

args = parser.parse_args()

hbars = [u"\u0020", u"\u258f", u"\u258e", u"\u258d", u"\u258b", u"\u258a", u"\u2589"]
max_bar_width = 10
tags_skipped = {}

if args.skip_percentage < 0 or args.skip_percentage > 100:
    sys.exit("Skip percetange out of range [0,100]")

if args.tags_skip is not None:
    tags_skip = args.tags_skip[0]

    for skip_tag in tags_skip:
        tag_data = skip_tag.split("=")
        if int(tag_data[1]) > 100 or int(tag_data[1]) < 0:
            sys.exit("Skip percentage for '%s' tag out of range [0,100]" % tag_data[0])
        else:
            tags_skipped[tag_data[0]] = tag_data[1]

# check if any of the bvh tags are in blacklisted tags
def is_tags_blacklisted(tags_bvh, tags_blacklisted):
  return not set(tags_bvh).isdisjoint(tags_blacklisted)

# check if any of the bvh tags are in whitelisted tags
def is_tags_whitelisted(tags_bvh, tags_whitelisted):
  return not set(tags_bvh).isdisjoint(tags_whitelisted)

# check if any of the bvh tags are in 'skip percentage' tags
def is_tags_skipped(tags_bvh, tags_skipped):
  return not set(tags_bvh).isdisjoint(tags_skipped)

def get_skip_tag_percentage_frames(tag_percentage, bvh_frames):
    return int(int(tag_percentage) / 100 * bvh_frames)

# outputs the percentage bar (made from hbars) calculated from provided values
def get_percentage_bar(value, max_entries):
    bar_len = int(max_bar_width * 6 * value / max_entries)
    bar_output = ""
    for i in range(0, max_bar_width):
        if bar_len > 6:
            bar_output += hbars[6]
            bar_len -= 6
        else:
            bar_output += hbars[bar_len]
            bar_len = 0
    return bar_output

# we index bvh files using ntpath conventions
def ntpath_to_os(path):
    elems = path.split('\\')
    return os.path.join(*elems)
# we get the number of mocap frames directly from bvh
def get_bvh_frames(filename):
    bvh_text_file = open(ntpath_to_os(filename), 'r')
    bvh_f_lines = bvh_text_file.readlines()
    bvh_text_file.close()
    motion_params_started = False
    for line in bvh_f_lines:
        if line.strip() == "MOTION":
            motion_params_started = True
            continue
        if motion_params_started:
            try:
                (key, value) = line.split(":")
                if key == "Frames":
                    return int(value.strip())
            except:
                pass
    sys.exit("Failed to determine frame count for BVH file %s" % filename)

print("Calculating ratios...")

with open('index.json', 'r') as fp:
    
    json_data = json.load(fp)
    tags = []
    tags_frames = {}
  
    end = args.end
    start = args.start
          
    if end == 0:
        end = len(json_data)
    
    total_frames = 0
    total_frames_filtered = 0
    total_files = 0

    for bvh in json_data[args.start:end]:
        
        bvh_frames = get_bvh_frames(bvh['file'])
        tags_blacklist = args.tags_blacklist.split(",")
        tags_whitelist = args.tags_whitelist.split(",")
        
        if is_tags_blacklisted(bvh['tags'], tags_blacklist):
            print("Skipping blacklisted %s..." % bvh['name']) 
            continue
        if tags_whitelist[0] != 'all' and not is_tags_whitelisted(bvh['tags'], tags_whitelist):
            print("Skipping not whitelisted %s..." % bvh['name'])
            continue

        for tag in bvh['tags']:
           tags.append(tag)
           if tag not in tags_frames:
                tags_frames[tag] = 0

        for bvh_frame in range(0, bvh_frames):

            total_frames += 1

            if args.skip_percentage:
                if random.randrange(0, 100) < args.skip_percentage:
                    continue

            skip = False
            for skip_tag in tags_skipped:
                if skip_tag in bvh['tags'] and random.randrange(0, 100) < int(tags_skipped[skip_tag]):
                    skip = True
                    break

            if skip:
                continue

            for tag in bvh['tags']:
                tags_frames[tag] += 1
            total_frames_filtered += 1

            total_files += 1
               
    if total_files > 0:
        
        if total_frames_filtered == 0:
            total_frames_filtered = 1

        tags_accounted = {}

        for tag in tags:
            if tag not in tags_accounted:
                tags_accounted[tag] = tags.count(tag)
   
        dash = '-' * 85
        print(dash)
        print('{:^85}'.format("MOCAP INDEX TAGS RATIO"))
        print(dash)   

        if args.show_stats:
            print("Start: %s End: %s" % (args.start, end))
            print("Tags count: %s" % len(tags_accounted))
            print("Mocaps Total Files: %s" % total_files)
            print("Mocaps Total Frames: %s" % total_frames)
            print("Mocaps Total Frames (after filter): %s" % total_frames_filtered)
            if len(tags_skipped) > 0: 
                print("Skipped Frames by Tags:")
                for skip_tag, val in tags_skipped.items():
                    print('{:<15s}{:>3s}{:<1s}'.format(skip_tag, val, "%"))
 
            print(dash)

        print('{:<15s}{:<10s}{:<8s}{:<11s}{:<15s}{:<15s}'.format("NAME", "FRAMES", 
            "RATIO BVH(%)", " ", "RATIO FRA(%)", " "))    
        print(dash)
    
        for tag, val in sorted(tags_accounted.items(), key=lambda kv: (-kv[1], kv[0])):
            percentage = val / total_files * 100
            percentage_fra = tags_frames[tag] / total_frames_filtered * 100
            ratio = get_percentage_bar(val, total_files)
            ratio_fra = get_percentage_bar(tags_frames[tag], total_frames_filtered)

            print('{:<15s}{:<10d}{:<8.2f}{:<15s}{:<8.2f}{:<15s}'.format(tag,
                tags_frames[tag], percentage, ratio, percentage_fra, ratio_fra))

        print(dash)

    else:
        print("No files has been included in ratio calculation")
    
    


