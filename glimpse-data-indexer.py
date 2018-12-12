#!/usr/bin/env python3
#
# Copyright (c) 2017 Glimp IP Ltd
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

import os
import sys
import argparse
import textwrap
import random
import json

full_index = []

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent("""\
        This script builds an index of all available rendered frames in a given
        directory and can then create further index files based on a random
        sampling from the full index (with optional exclusions). For example you
        could create three index files of 300k random frames out of 1 million
        for training three separate decision trees.
        """),
    epilog=textwrap.dedent("""\
        Firstly if no index.full file can be loaded listing all available
        frames then one will be created by traversing all the files under the
        <data> directory looking for frames. --full can be used to override
        which index is loaded here.

        Secondly the full index is filtered according to any white/blacklists
        for tags (via --tags-blacklist and --tags-whitelist); to optionally
        remove flipped frames (via --no-flipped) or exclude files listed in
        another index (via --exclude).

        Finally for each -i <name> <N> argument sequence given it will create a
        data/index.<name> file with <N> randomly sampled frames taken from the
        full index.

        Sampling for each index is done with replacment by default, such that
        you may get duplicates within an index. Use the -w,--without-replacment
        options to sample without replacment.  Replacement always happens after
        creating each index, so you should run the tool multiple times and use
        -e,--exclude to avoid any overlapping samples between separate index
        files if required.

        The sampling is pseudo random and reproducible for a given directory of
        data. The seed can be explicitly given via --seed= and the value is
        passed as a string to random.seed() which will calculate a hash of the
        string to use as an RNG seed. The default seed is the name of the current
        index being created.

        Note: Even if the exclusions from passing -e have no effect the act of
        passing -e options can change the random sampling compared to running
        with no exclusion due to how the set difference calculations may affect
        the sorting of the index internally.
        """))
parser.add_argument("data", nargs=1, help="Data Directory")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Display verbose debug information")
parser.add_argument("-s", "--seed", help="Seed for random sampling")
parser.add_argument("-f", "--full", nargs=1, default=['full'],
                    help="An alternative index.<FULL> extension for the full "
                         "index (default 'full')")

# Filters...
parser.add_argument('--no-flipped', action="store_true",
                    help="Don't consider flipped frames")
parser.add_argument('--only-flipped', action="store_true",
                    help="Only consider flipped frames")
parser.add_argument('--tags-blacklist', default='none',
                    help="Don't consider frames with any of these tags")
# XXX: Do we have consistent whitelist semantics? Should we only consider
# frames matching _all_ whitelist tags or consider frames that match _at least
# one_ whitelist tag?
parser.add_argument('--tags-whitelist', default='all',
                    help="Only consider frames with at least one of these tags")
parser.add_argument("--body", action="append", nargs=1, metavar=('BODY_NAME'),
                    help="Only consider frames including specific body models")
parser.add_argument("--bvh", action="append", nargs=1, metavar=('BVH_NAME'),
                    help="Only consider frames part of specific mocap sequences")
parser.add_argument("-e", "--exclude", action="append", nargs=1, metavar=('NAME'),
                    help="Load index.<NAME> frames to be excluded from sampling")

# Sampling methods...
parser.add_argument("-w", "--without-replacement", action="store_true",
                    help="Sample each index without replacement (use -e if you "
                         "need to avoid replacement between index files)")
parser.add_argument("-a", "--all", action="store_true",
                    help="Simply keep everything (in-order) after applying "
                         "filters and exclusions")

parser.add_argument("-i", "--index", action="append", nargs=2, metavar=('NAME','N'),
                    help="Create an index.<NAME> file with N frames")



args = parser.parse_args()

data_dir = args.data[0]
full_filename = os.path.join(data_dir, "index.%s" % args.full[0])


# 1. Load the full index
try:
    with open(full_filename, 'r') as fp:
        full_index = fp.readlines()
except FileNotFoundError as e:
    for root, dirs, files in os.walk(data_dir):
        for filename in files:
            if filename.startswith("Image") and filename.endswith(".json"):
                frame_name = filename[5:-5]
                (mocap_path, section) = os.path.split(root)
                (top_path,mocap) = os.path.split(mocap_path)

                full_index.append("/%s/%s/Image%s\n" % (mocap, section, frame_name))

                if args.verbose:
                    print("mocap = %s, section = %s, frame = %s" %
                            (mocap, section, frame_name))

    with open(full_filename, 'w+') as fp:
        full_index.sort()
        for frame in full_index:
            fp.write(frame)

n_frames = len(full_index)
print("index.%s: %u frames\n" % (args.full[0], n_frames))

full_index_modified = False


# Apply filters that don't depend on parsing frame's .json meta data...
if (args.bvh or
        args.no_flipped or
        args.only_flipped):

    full_index_modified = True
    filtered_index = []
    for frame in full_index:
        (bvh_name, section, frame_name) = frame.strip()[1:].split('/')

        if args.no_flipped and frame_name.endswith('flipped'):
            continue

        if args.only_flipped and not frame_name.endswith('flipped'):
            continue

        if args.bvh and bvh_name not in args.bvh:
            continue

        filtered_index.append(frame)
    full_index = filtered_index


# Apply (slower) filters that depend on parsing frame's .json meta data...
if (args.body or
        (args.tags_whitelist and args.tags_whitelist != 'all') or
        (args.tags_blacklist and args.tags_blacklist != 'none')):

    if args.tags_blacklist and args.tags_blacklist != 'none':
        tags_blacklist = set(args.tags_blacklist.split(","))
    else:
        tags_blacklist = set()
    if args.tags_whitelist and args.tags_whitelist != 'all':
        tags_whitelist = set(args.tags_whitelist.split(","))
    else:
        tags_whitelist = set()

    full_index_modified = True
    filtered_index = []
    for frame in full_index:
        frame = frame.strip()

        meta_filename = os.path.join(data_dir, 'labels', frame[1:] + ".json")
        keep = True
        with open(meta_filename, 'r') as fp:
            meta = json.load(fp)

            # We add a while loop here just for the sake of being able
            # to break from the block early if any of the filters
            # match this frame...
            while True:
                if args.body and meta['body'] not in args.body:
                    keep = False
                    break
                bvh_tags = set(meta.get('tags', {}))
                if tags_whitelist and not tags_whitelist & bvh_tags:
                    keep = False
                    break
                if tags_blacklist & bvh_tags:
                    keep = False
                    break
                break  # We don't actually want to loop

        if keep:
            filtered_index.append(frame)
    full_index = filtered_index


# Apply --exclude filters
if args.exclude:
    full_index_modified = True
    exclusions = []
    for (name,) in args.exclude:
        with open(os.path.join(data_dir, 'index.%s' % name), 'r') as fp:
            lines = fp.readlines()
            print("index.%s: loaded %u frames to exclude" % (name, len(lines)))
            exclusions += lines

    full_set = set(full_index)
    exclusion_set = set(exclusions)
    difference = full_set.difference(exclusion_set)
    full_index = list(difference)


if not len(full_index):
    sys.exit("No frames left after filtering")


if full_index_modified:
    n_frames = len(full_index)
    print("\n%u frames left after applying filters" % n_frames)
    print("sorting...")
    full_index.sort()


# Sample index files
if args.index:
    names = {}

    for (name, length_str) in args.index:
        if name in names:
            raise ValueError("each index needs a unique name")
        names[name] = 1
        n_samples = int(length_str)
        if (args.without_replacement or args.all) and n_samples > n_frames:
            raise ValueError("Not enough frames to create requested index file %s" % name)

    print("")
    start = 0
    for (name, length_str) in args.index:
        N = int(length_str)

        if args.seed:
            random.seed(args.seed)
        else:
            random.seed(name)

        frame_range = range(n_frames)
        if args.all:
            samples = frame_range[:N]
        elif args.without_replacement:
            samples = random.sample(frame_range, N)
        else:
            samples = [ random.choice(frame_range) for i in range(N) ]

        with open(os.path.join(data_dir, "index.%s" % name), 'w+') as fp:
            for i in samples:
                fp.write(full_index[i])

            if args.all:
                print("index %s: %d frames" % (name, N))
            elif args.without_replacement:
                print("index %s: %d samples (without replacement)" % (name, N))
            else:
                print("index %s: %d samples (with replacement)" % (name, N))

