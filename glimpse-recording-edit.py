#!/usr/bin/env python3
#
# Copyright (c) 2019 Glimp IP Ltd
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

# Lets us trim and concatenate glimpse viewer recordings, optionally repeating
# appended sections (with mirroring to remain seamless) to create longer
# recordings. Note that duplicated frames will share large binary resources.

import os
import sys
import copy
import json
import argparse
import shutil
import hashlib

parser = argparse.ArgumentParser()

parser.add_argument('--verbose', action='store_true',
                    help="Enable verbose debugging")
parser.add_argument('--dry-run', action='store_true',
                    help="Don't output a new recording")

subparsers = parser.add_subparsers(dest='operation')


trim_parser = subparsers.add_parser('trim',
                                    help="Trim the recording")
trim_parser.add_argument("-i", "--input", required=True,
                         help="Input recording to load and trim")
trim_parser.add_argument("-o", "--output", required=True,
                         help="Output recording directory")
trim_parser.add_argument('--start', type=int, default=0,
                         help="First frame to keep")
trim_parser.add_argument('--end', type=int, default=0,
                         help="Last frame to keep (negative counts from the end, 0 corresponds to the last frame)")


append_parser = subparsers.add_parser('append',
                                      help="Append another recording to this one")
append_parser.add_argument("-i", "--input", required=True,
                           help="Input recording to load (will be output unmodified)")
append_parser.add_argument("-a", "--append", required=True,
                           help="Recording to be appended (with optional modifications)")
append_parser.add_argument("-o", "--output", required=True,
                           help="Output recording directory")
append_parser.add_argument('--start', type=int, default=0,
                           help="First frame from recording to append")
append_parser.add_argument('--end', type=int, default=0,
                           help="Last frame from src recording to append")
append_parser.add_argument('--reverse', action='store_true',
                           help="Reverse the source recording frames before appending")
append_parser.add_argument('--repeat-n', type=int, metavar='N',
                           help="Repeat the source recording frames N times (with reflections)")
append_parser.add_argument('--repeat-duration', type=int, metavar='DURATION',
                           help="Repeat the source recording frames (with reflection) until extended by at least DURATION seconds long (the appended sections aren't ever cut)")

concat_parser = subparsers.add_parser('concat',
                                      help="Concatenate multiple recordings")
concat_parser.add_argument("-i", "--input", action="append", required=True,
                           help="Input recordings to load and concatenate in order (will all be output unmodified)")
concat_parser.add_argument("-o", "--output", required=True,
                           help="Output recording directory")

args = parser.parse_args()


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# Note: the original filenames for the depth/video .bin files are based
# on frame numbers and so we can't assume they are unique when combining
# multiple recordings and so we change .bin files to instead be based
# on an md5 hash of their contents
def append_frame(recording, recording_dir, frame, frame_src_dir):
    if 'depth_file' in frame:
        bin_filename = os.path.join(frame_src_dir, frame['depth_file'][1:])
        md5hash = md5(bin_filename)
        shutil.copy2(bin_filename, os.path.join(recording_dir, 'depth', md5hash + '.bin'))
        frame['depth_file'] = '/depth/%s.bin' % md5hash
    if 'video_file' in frame:
        bin_filename = os.path.join(frame_src_dir, frame['video_file'][1:])
        md5hash = md5(bin_filename)
        shutil.copy2(bin_filename, os.path.join(recording_dir, 'video', md5hash + '.bin'))
        frame['video_file'] = '/video/%s.bin' % md5hash

    recording['frames'].append(frame)


def create_empty_output(reference_recording, out_dir):

    if not args.dry_run:
        if os.path.exists(args.output):
            sys.exit("%s already exists" % args.output)
        os.mkdir(args.output)
        os.mkdir(os.path.join(args.output, 'depth'))
        os.mkdir(os.path.join(args.output, 'video'))

    ret = copy.deepcopy(reference_recording)
    ret['frames'] = []
    return ret


def load_recording(recording_dir):
    index_filename = os.path.join(recording_dir, "glimpse_recording.json")
    with open(index_filename, 'r') as fp:
        return json.load(fp)
    sys.exit("Failed to open %s" % recording_dir)
    return None


if args.operation == 'trim':

    if args.end < args.start:
        sys.exit("Trim end must be >= trim start")

    rec = load_recording(args.input)
    print("Loaded %d frames from %s" % (len(rec['frames']), args.input))
    out_rec = create_empty_output(rec, args.output)
    print("Output:")

    initial_frame_count = len(rec['frames'])

    if args.end:
        print("Trimming frame range [%d:%d]" % (args.start, args.end))
        keep_frames = copy.deepcopy(rec['frames'][args.start:args.end])
    else:
        print("Trimming from frame %d to end" % args.start)
        keep_frames = copy.deepcopy(rec['frames'][args.start:])

    for frame in keep_frames:
        append_frame(out_rec, args.output, frame, args.input)

    print("Trimmed from %d frames to %d" % (initial_frame_count, len(rec['frames'])))

elif args.operation == 'append':

    if args.end < args.start:
        sys.exit("Trim end must be >= trim start")

    rec = load_recording(args.input)
    print("Loaded %d frames from %s" % (len(rec['frames']), args.input))
    out_rec = create_empty_output(rec, args.output)
    print("Output:")

    for frame in copy.deepcopy(rec['frames']):
        append_frame(out_rec, args.output, frame, args.input)
    print("> Added %d frames from %s" % (len(out_rec['frames']), args.input))

    append_rec = load_recording(args.append)
    print("> Opened %s for appending" % args.append)

    if args.end:
        append_frames = append_rec['frames'][args.start:args.end]
    else:
        append_frames = append_rec['frames'][args.start:]

    if len(append_frames) == 0:
        sys.exit("No frames to append")

    # We want to keep track of how much we've extended the recording
    # so save this before we start appending anything
    input_end_time = out_rec['frames'][-1]['timestamp']

    start_time = append_frames[0]['timestamp']
    end_time = append_frames[-1]['timestamp']

    # Add a small time gap between appended sections
    append_gap_time = 1e9 / 30

    if args.reverse:
        direction = -1
    else:
        direction = 1

    repeat_count = 0
    append_frame_count = 0
    while True:
        ref_time = out_rec['frames'][-1]['timestamp']
        if direction > 0:
            for frame in append_frames:
                new_frame = copy.deepcopy(frame)
                frame_time = frame['timestamp'] - start_time
                new_frame['timestamp'] = ref_time + frame_time + append_gap_time
                append_frame(out_rec, args.output, new_frame, args.append)
                append_frame_count += 1
        else:
            for frame in reversed(append_frames):
                new_frame = copy.deepcopy(frame)
                frame_time = end_time - frame['timestamp']
                new_frame['timestamp'] = ref_time + frame_time + append_gap_time
                append_frame(out_rec, args.output, new_frame, args.append)
                append_frame_count += 1

        extend_duration = out_rec['frames'][-1]['timestamp'] - input_end_time

        repeat_count += 1
        direction = -direction;

        if args.repeat_n:
            if repeat_count >= args.repeat_n:
                break
        elif args.repeat_duration:
            if extend_duration > (args.repeat_duration * 1e9):
                break
        else:
            break
    print("> Appended %d frames from %s" % (append_frame_count, args.append))

elif args.operation == 'concat':

    if len(args.input) == 0:
        sys.exit("No input recordings specified with -i,--input")

    input_rec0 = load_recording(args.input[0])
    print("Loaded first recording (%s) as reference to initialize output" % args.input[0])

    out_rec = create_empty_output(input_rec0, args.output)
    print("Output:")
    for input_dir in args.input:
        input_rec = load_recording(input_dir)
        for frame in copy.deepcopy(input_rec['frames']):
            append_frame(out_rec, args.output, frame, input_dir)
        print("> Added %s" % input_dir)

duration = out_rec['frames'][-1]['timestamp'] - out_rec['frames'][0]['timestamp']
print("Final recording duration = %.2f seconds" % (duration / 1e9))


if not args.dry_run:
    with open(os.path.join(args.output, "glimpse_recording.json"), 'w') as fp:
        json.dump(out_rec, fp, indent=4)
