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
# training data.

import os
import sys
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument('--training-data',
                    default=os.path.dirname(os.path.realpath(__file__)),
                    help="Path to training data")

parser.add_argument("index_filename",
                    help="Filename of index (create with glimpse-data-indexer) to parse")

args = parser.parse_args()

hbars = [u"\u0020", u"\u258f", u"\u258e", u"\u258d", u"\u258b", u"\u258a", u"\u2589"]
max_bar_width = 10


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


print("Training Data Dir: %s" % args.training_data)

mocaps_dir = os.path.join(args.training_data, 'mocap')
print("MoCaps Dir: %s" % mocaps_dir)

mocap_name_map = {}

index_filename = os.path.join(mocaps_dir, "index.json")
with open(index_filename, 'r') as fp:
    mocap_index = json.load(fp)

    for bvh in mocap_index:
        mocap_name_map[bvh['name']] = bvh

if not len(mocap_name_map):
    sys.exit("Empty mocap index")

data_dir = os.path.dirname(args.index_filename)
print("Data Dir: %s" % data_dir)
with open(args.index_filename, 'r') as fp:
    index = fp.readlines()

    tag_counts = {}

    total_frames = len(index)
    if not total_frames:
        sys.exit("Empty index")

    for frame in index:
        filename = os.path.join(data_dir, 'labels', frame.strip()[1:] + ".json")
        with open(filename, 'r') as fp:
            meta = json.load(fp)

            bvh = mocap_name_map[meta['bvh']]
            if 'tags' in bvh:
                for tag in bvh['tags']:
                    if tag not in tag_counts:
                        tag_counts[tag] = 1
                    else:
                        tag_counts[tag] += 1

    dash = '-' * 80
    print(dash)
    print("N Frames:      %s" % total_frames)
    print("N Tags:        %s" % len(tag_counts))

    print(dash)
    print('{:<15s}{:<10s}{:<10s} |{:<10s}|'.format("NAME",
                                                   "FRAMES",
                                                   "FRAMES(%)",
                                                   " "))

    print(dash)
    for tag, val in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        percentage = val / total_frames * 100
        bar = get_percentage_bar(val, total_frames)

        print('{:<15s}{:<10d}{:<10f} |{:<10s}|'.format(tag,
                                                       tag_counts[tag],
                                                       percentage,
                                                       bar))

    print(dash)
