#!/usr/bin/env python3

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
import sys
import argparse
import subprocess
import datetime

print("All arguments: %s" % " ".join(sys.argv))

# Argparse doesn't provide a decent way of handling '--' for us so we manually
# pull out arguments for glimpse-cli.py first...
for i in range(len(sys.argv)):
    if sys.argv[i] == '--':
        generator_args = sys.argv[i + 1:]
        sys.argv = sys.argv[:i]
        break;

dt = datetime.datetime.today()
date_str = "%04u-%02u-%02u-%02u-%02u-%02u" % (dt.year,
        dt.month, dt.day, dt.hour, dt.minute, dt.second)

parser = argparse.ArgumentParser(prog="glimpse-render",
                                 description="""\
A helper script for scheduling multiple instances of Blender to render a set
of Glimpse training data.
""",
                                  epilog="""\
Note: any arguments that follow a stand-alone '--' argument will be passed through
to glimpse-cli.py.
""")
parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
parser.add_argument('--dry-run', help='Just print information without rendering', action='store_true')
parser.add_argument('-j', '--num-instances', type=int, default=1, help='Number of Blender instances to run for rendering')
parser.add_argument('--start', type=int, default=0, help='Index of first MoCap to render (default 0)')
parser.add_argument('--end', type=int, default=2000, help='Index of last MoCap to render (default 2000)')
parser.add_argument('--dest', default=os.path.join(os.getcwd(), 'renders'), help='Top-level directory for all renders (default ./renders)')
parser.add_argument('--name', default=date_str, help='Unique name for this render run (subdirectories created under --dest)')
parser.add_argument('training_data', nargs=1, help='Path to top of training data')

cli_args = parser.parse_args()


def run_cmd(args):
    global cli_args

    if cli_args.debug:
        print("# " + " ".join(map(str, args)), file=sys.stderr)
        returncode = subprocess.call(args)
        print("# return status = " + str(returncode))
        return returncode
    else:
        return subprocess.call(args)

training_data = cli_args.training_data[0]
name = cli_args.name
dest = cli_args.dest

n_mocaps = cli_args.end - cli_args.start
step = int(n_mocaps / cli_args.num_instances)

print("Rendering %d motion capture sequences with %d instance[s] of Blender" % (n_mocaps, cli_args.num_instances))
print("Each instance is rendering %d sequences" % step)
print("Path to training data is '%s'" % training_data)
print("Destination is '%s'" % dest)
print("Pass-through arguments for glimpse-cli.py: %s" % " ".join(generator_args))
print("")

if step * cli_args.num_instances != n_mocaps:
    sys.exit("Instance count of %d doesn't factor into count of %d motion capture sequences" %
             (cli_args.num_instances, n_mocaps))

processes = []

n_frames = 0
for i in range(cli_args.num_instances):
    start = cli_args.start + i * step
    end = start + step
    part_name = name + '-part-%d' % i

    generator_command = [ os.path.join(training_data, 'blender', 'glimpse-cli.py')] + generator_args
    generator_command += ['--start', str(start)]
    generator_command += ['--end', str(end)]
    generator_command += ['--dest', dest]
    generator_command += ['--name', part_name]
    generator_command += [ training_data ]
    if cli_args.dry_run:
        generator_command += ['--dry-run']
        print("  " + " ".join(generator_command))
        blender_output = subprocess.check_output(generator_command).decode('utf-8')
        blender_lines = blender_output.splitlines()
        found_frame_count = False
        for line in blender_lines:
            if line.startswith("> DRY RUN FRAME COUNT:"):
                parts = line.split(":")
                frame_count = int(parts[1])
                found_frame_count = True
                break
        if not found_frame_count:
            print("blender output = " + blender_output)
            sys.exit("Failed to determine frame count from blender output")
        print("   - N frames = %d" % frame_count)
        n_frames += frame_count
    else:
        print("  " + " ".join(generator_command))
        os.makedirs(os.path.join(dest, part_name), exist_ok=True)
        with open(os.path.join(dest, part_name, 'render.log'), 'w') as fp:
            p = subprocess.Popen(generator_command, stdout=fp, stderr=fp)
            processes.append(p)
    #subprocess.check_output(generator_command)

print("")
if cli_args.dry_run:
    print("Total frame count would be = %d" % n_frames)
    print("")
    print("NB: the frame count should roughly double after running the")
    print("image-pre-processor since it will create flipped versions of each frame")
else:
    print("Waiting for all Blender instances to complete...")
    status = 0
    for p in processes:
        if p.wait() != 0:
            status = 1

    if status:
        sys.exit("There were some errors; check log files under destination directory for details")
