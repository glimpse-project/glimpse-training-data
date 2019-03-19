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

import os
import argparse
import textwrap
import json
import glob
import fnmatch
import ntpath

parser = argparse.ArgumentParser()

parser.add_argument("-a", "--add", action='append', help="Add BVH file - implicitly selected for applying any edit options given too")
parser.add_argument("-r", "--remove", action='append', help="Remove BVH file")

# Select entries to view/edit (overridden when adding new entries)
parser.add_argument("-s", "--start", type=int, default=0, help="Start range (negative values are relative to end of index)")
parser.add_argument("-e", "--end", type=int, default=0, help="End range (zero means to go to the end of the index, negative values are relative to end of index)")
parser.add_argument("-n", "--name-match", action='append', help="Only look at entries whose name matches this wildcard pattern")
parser.add_argument("--file-match", action='append', help="Only look at entries whose relative filename matches this wildcard pattern")
parser.add_argument("--blacklisted", action='store_true', help="Only look at blacklisted entries")
parser.add_argument("--non-blacklisted", action='store_true', help="Only look at non-blacklisted entries")
parser.add_argument("--with-tag", action='append', help="Only look at entries with this tag")
parser.add_argument("--without-tag", action='append', help="Only look at entries without this tag")


# Edit commands
parser.add_argument("--clear-tags", action='store_true', help="Clear all tags (done before adding any new tags")
parser.add_argument("-t", "--tag", action='append', help="Add tag")
parser.add_argument("-u", "--untag", action='append', help="Remove tag")
parser.add_argument("--blacklist", action='store_true', help="Mark entries as blacklisted (will add a 'blacklist' tag too)")
parser.add_argument("--unblacklist", action='store_true', help="Clear blacklist status of entries (will remove any 'blacklist' tag too)")
parser.add_argument("--fps", type=int, default=0, help="Define what the capture frame rate was (negative means to unset any definition, zero means leave untouched)")
parser.add_argument("--note", help="Append a descriptive comment")

parser.add_argument("--list", action="store_true", help="List the names of matched entries")
parser.add_argument("--dry-run", action="store_true", help="Dry run")
parser.add_argument("-v", "--verbose", action="store_true", help="Display verbose debug information")

parser.add_argument("index_filename", help="Filename of index.json to parse / edit")

args = parser.parse_args()

print_matched=False
print_entries=False
print_changes=False

if args.verbose:
    print_matched=True
    print_changes=True
    print_entries=True

if args.dry_run:
    print_matched=True
    print_changes=True

if args.list:
    print_matched=True

filename_map = {}
name_map = {}


def process_entry(entry, i):
    changes = []

    if 'name' not in entry:
        new_name = ntpath.basename(entry['file'])[:-4]

        if new_name in name_map:
            for n in range(1, 1000):
                unique_name = '%s-%05d' % (new_name, n)
                if unique_name not in name_map:
                    new_name = unique_name
                    break
        if new_name in name_map:
            sys.exit("ERROR: Failed to determine unique name for %s" % entry['file'])

        entry['name'] = new_name
        name_map[new_name] = entry
        changes += [ "Set name to '%s', based on filename" % new_name]

    if args.clear_tags:
        if 'tags' in entry:
            del entry['tags']
            changes += [ "Clear tags" ]

    if 'camera' in entry:
        del entry['camera']
        changes += [ "Delete legacy camera data" ]

    if args.blacklist:
        if 'blacklist' not in entry or not entry['blacklist']:
            entry['blacklist']=True
            if 'tags' not in entry:
                entry['tags']={}
            entry['tags']['blacklist']=True
            changes += [ "Blacklisted" ]

    if args.unblacklist:
        if 'blacklist' in entry:
            del entry['blacklist']
            changes += [ "Un-blacklisted" ]
        if 'tags' in entry and 'blacklist' in entry['tags']:
            del entry['tags']['blacklist']

    if 'blacklist' in entry:
        if entry['blacklist'] == True:
            if 'tags' not in entry:
                entry['tags']={}
            entry['tags']['blacklist']=True
        else:
            del entry['blacklist']
            changes += [ "Remove redundant blacklist=false" ]

    if args.fps > 0:
        if 'fps' not in entry or entry['fps'] != args.fps:
            entry['fps'] = args.fps
            changes += [ "Set fps" ]
    elif args.fps < 0:
        if 'fps' in entry:
            del entry['fps']
            changes += [ "Unset fps" ]
    
    if args.note:
        if 'notes' not in entry:
            entry['notes'] = []
        entry['notes'] = [ args.note ]
        changes += [ "Add note" ]

    if 'notes' in entry and len(entry['notes']) == 0:
        del entry['notes']
        changes += [ "Remove empty notes array" ]

    if args.tag:
        for tag in args.tag:
            tag = tag.lower()
            if 'tags' not in entry:
                entry['tags'] = {}
            if tag not in entry['tags']:
                entry['tags'][tag] = True
                changes += [ "Add tag %s" % tag ]

    if 'tags' in entry and args.untag:
        for tag in args.untag:
            tag = tag.lower()
            if tag in entry['tags']:
                del entry['tags'][tag]
                changes += [ "Remove tag %s" % tag ]

    if 'tags' in entry and len(entry['tags']) == 0:
        del entry['tags']
        changes += [ "Remove empty tags" ]

    if print_matched:
        if len(changes):
            print("%d) %s - CHANGED" % (i, entry['name']))
            if print_changes:
                for c in changes:
                    print("> %s" % c)
        else:
            print("%d) %s - unchanged" % (i, entry['name']))
        if print_entries:
            print("  > filename: %s" % entry['file'])
            if 'blacklist' in entry and entry['blacklist']:
                print("  > black-listed: true")
            if 'fps' in entry:
                print("  > fps: %d" % entry['fps'])
            if 'notes' in entry and len(entry['notes']):
                print("  > notes:")
                for note in entry['notes']:
                    print("  > | %s" % note)
            if 'tags' in entry and len(entry['tags']):
                print("  > tags: %s" % ','.join(entry['tags']))


def normalize_path(bvh_path):
    index_dir = os.path.dirname(args.index_filename)
    abs_bvh_path = os.path.abspath(bvh_path)
    abs_index_dir = os.path.abspath(index_dir)
    # no matter what OS we're using we want consistent filename
    # indexing conventions...
    rel_path = os.path.relpath(abs_bvh_path, abs_index_dir)
    rel_path = ntpath.normpath(rel_path)
    rel_path = ntpath.normcase(rel_path)
    return rel_path


with open(args.index_filename, 'r+') as fp:
    index = json.load(fp)

    print("Opened %s with %d entries" % (args.index_filename, len(index)))

    if args.remove:
        for bvh_path in args.remove:
            rel_path = normalize_path(bvh_path)
            before_len = len(index)
            index = [ entry for entry in index if entry['file'] != rel_path ]
            if len(index) < before_len:
                if print_changes:
                    print("Remove %s from index" % bvh_path)
            else:
                print("WARNING: no entry for %s found for removal" % bvh_path)

    # Add all filenames and names to dictionaries so we can ensure we don't
    # index any duplicates...
    for entry in index:
        if 'file' in entry:
            if entry['file'] in filename_map:
                sys.exit("ERROR: %s has duplicate entries for %s" % (args.index_filename, entry['file']))
            filename_map[entry['file']] = entry
        if 'name' in entry:
            if entry['name'] in name_map:
                sys.exit("ERROR: %s has duplicate entries for name: '%s'" % (args.index_filename, entry['name']))
            name_map[entry['name']] = entry

        # Normalize how we blacklist entries:
        blacklisted=False
        if 'blacklist' in entry:
            blacklisted = entry['blacklist']
            del entry['blacklist']
        if 'tags' in entry and 'blacklist' in entry['tags']:
            blacklisted = True

        if blacklisted:
            if 'tags' not in entry:
                entry['tags'] = {}
            entry['tags']['blacklist'] = True

    # All filtering options (--start, --end, --name-match, --with[out]-tag etc)
    # are ignored when adding new entries and instead it's as if all the new
    # entries were selected for any edit operations...
    if args.add:
        i = len(index)
        for bvh_path in args.add:
            rel_path = normalize_path(bvh_path)

            if rel_path in filename_map:
                print('WARNING: Not re-adding %s to index' % rel_path)
                continue

            new_entry = { 'file': rel_path }
            filename_map[rel_path] = new_entry

            index.append(new_entry)
            if print_changes:
                print("Add %s to index" % rel_path)
            process_entry(new_entry, i)
            i+=1
    else:
        end = args.end
        if end == 0:
            end = len(index)

        for i in range(args.start, end):
            entry = index[i]

            blacklisted=False
            if 'tags' in entry and 'blacklist' in entry['tags']:
                blacklisted = True

            if args.blacklisted and not blacklisted:
                continue

            if args.non_blacklisted and blacklisted:
                continue

            tags_whitelist = args.with_tag
            if tags_whitelist:
                matched_whitelist=False
                if 'tags' in entry:
                    for tag in tags_whitelist:
                        if tag in entry['tags']:
                            matched_whitelist=True
                            break
                if not matched_whitelist:
                    continue

            tags_blacklist = args.without_tag
            if tags_blacklist:
                matched_blacklist=False
                if 'tags' in entry:
                    for tag in tags_blacklist:
                        if tag in entry['tags']:
                            matched_blacklist=True
                            break
                if matched_blacklist:
                    continue

            if args.name_match:
                if 'name' not in entry:
                    continue
                matched_name=False
                for match in args.name_match:
                    if fnmatch.fnmatch(entry['name'], match):
                        matched_name = True
                        break
                if not matched_name:
                    continue

            if args.file_match:
                matched_filename=False
                for match in args.file_match:
                    norm_match = normalize_path(match)
                    if fnmatch.fnmatch(entry['file'], norm_match):
                        matched_filename = True
                        break
                if not matched_filename:
                    continue

            process_entry(entry, args.start + i)
            i+=1

    if not args.dry_run:
        fp.seek(0)
        fp.truncate(0)
        json.dump(index, fp, indent=4, sort_keys=True)


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


print("")
print("Summary of index contents:")

with open(args.index_filename, 'r+') as fp:
    index = json.load(fp)

    print("")
    full_len = len(index)
    n_blacklisted = len([x for x in index if 'tags' in x and 'blacklist' in x['tags']])
    print("%d non-blacklisted entries" % (full_len - n_blacklisted))
    print("%d blacklisted entries" % n_blacklisted)

    tag_count = {}
    for e in index:
        if 'tags' in e:
            if 'blacklist' in e['tags']:
                continue
            for tag in e['tags']:
                tag_count[tag] = tag_count.get(tag, 0) + 1

    print("")
    print("Index tags (ignoring blacklisted entries):")
    print("")
    print('  {:<15s}{:<10s}{:<8s}|{:<10s}|'.format("TAG NAME", "COUNT", "PERCENT", " "))
    print('-' * 80)
    for (key, val) in sorted(tag_count.items(),
                             key=lambda kv: (-kv[1], kv[0])):
        count = tag_count[key]
        percentage = count / full_len * 100
        bar = get_percentage_bar(count, full_len)
        print('  {:<15s}{:<10d}{:<8.2f}|{:<10s}|'.format(key, count, percentage, bar))






