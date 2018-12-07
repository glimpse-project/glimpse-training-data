#!/usr/bin/env python3

# Copyright (c) 2017-2018 Glimp IP Ltd
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
# A command-line front end for the glimpse_data_generator addon
#
# The script can be run directly and it will handle the trickery necessary to
# run itself with the same arguments via Blender.
#
# The script can also handle spawning multiple instances of Blender to
# help better parallelize rendering
#

import os
import sys
import argparse
import subprocess
import datetime
import json

# Detect whether the script is running under Blender or not...
try:
    import bpy
    import addon_utils
    as_blender_addon = True
except ModuleNotFoundError:
    as_blender_addon = False

if as_blender_addon:
    parser = argparse.ArgumentParser(prog="glimpse-generator", add_help=False)
    parser.add_argument('--help-glimpse',
                        help='Show this help message and exit', action='help')
    # used to override --name/start/end if we split the user's given start/end
    # range across multiple Blender instances...
    parser.add_argument('--instance-overrides',
                        action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--instance-name', help=argparse.SUPPRESS)
    parser.add_argument('--instance-start', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--instance-end', type=int, help=argparse.SUPPRESS)
else:
    parser = argparse.ArgumentParser(prog="glimpse-generator")

subparsers = parser.add_subparsers(dest='subcommand')

dt = datetime.datetime.today()
date_str = "%04u-%02u-%02u-%02u-%02u-%02u" % (dt.year, dt.month, dt.day,
                                              dt.hour, dt.minute, dt.second)

parser.add_argument('--debug', action='store_true',
                    help="Enable extra debug messages")
parser.add_argument('--verbose', action='store_true',
                    help="Enable more verbose debug messages")

parser.add_argument('--training-data',
                    default=os.path.dirname(os.path.realpath(__file__)),
                    help="Path to training data")


# TODO: support being able to give an explicit bvh name instead of --start/end
def add_filter_options(parser):
    parser.add_argument("-n", "--name-match", action='append',
                        help="Only look at entries whose name matches this "
                             "wildcard pattern")

    parser.add_argument('--start', type=int, default=0,
                        help='Index of first MoCap to filter')
    parser.add_argument('--end', type=int, default=-1,
                        help='Index of last MoCap to filter (exclusive)')

    # XXX: Note that any value other than 'all' may override a
    # render --config, so don't change the default here unless the
    # check later is also updated...
    parser.add_argument('--tags-whitelist', default='all',
                        help='Only index entries whose tags match this'
                             ' (comma separated) whitelist will be processed'
                             ' (default \'all\')')

    # XXX: Note that any value other than 'none' may override a
    # render --config, so don't change the default here unless the
    # check later is also updated...
    parser.add_argument('--tags-blacklist', default='none',
                        help='Index entires whose tags match this'
                             ' (comma separated) blacklist will not be'
                             ' processed. (default \'none\')')


parser_info = subparsers.add_parser(
    'info', help='Load the mocap index and print summary information')
add_filter_options(parser_info)


parser_preload = subparsers.add_parser(
    'preload', help='Preload mocap files as actions before rendering')
add_filter_options(parser_preload)
parser_preload.add_argument('--blend-file',
                            help='Override .blend file to preload mocap actions '
                                 'within (default '
                                 '<training_data>/blender/glimpse-training.blend)')
parser_preload.add_argument('--dry-run',
                            help="Don't save the results", action='store_true')


parser_purge = subparsers.add_parser('purge', help='Purge mocap actions')
add_filter_options(parser_purge)
parser_purge.add_argument('--dry-run',
                          help="Don't save the results", action='store_true')


parser_link = subparsers.add_parser('link', help='Link mocap actions')
parser_link.add_argument('--mocap-library',
                         default="//glimpse-training-mocap-library.blend",
                         help='.blend file library with preloaded mocap actions'
                              ' (default //glimpse-training-mocap-library.blend)')
add_filter_options(parser_link)
parser_link.add_argument('--dry-run',
                         help="Don't save the results", action='store_true')


parser_render = subparsers.add_parser('render', help='Render data')

parser_render.add_argument('--dest', default=os.path.join(os.getcwd(), 'renders'),
                           help='Directory to write files too')
parser_render.add_argument('--name', default=date_str,
                           help='Unique name for this render run')

add_filter_options(parser_render)

parser_render.add_argument('--skip-percentage', type=int, default=0,
                           help='(random) percentage of frames to skip '
                                '(overrides config; default 0)')

parser_render.add_argument('--config',
                           help='Detailed configuration for filtering and '
                                'camera resolution + positioning options')
parser_render.add_argument('--dry-run',
                           help='Just print information without rendering',
                           action='store_true')

parser_render.add_argument('-j', '--num-instances', type=int, default=1,
                           help='Number of Blender instances to run')

# If this script is run from the command line and we're not yet running within
# Blender's Python environment then we will spawn Blender and tell it to
# re-evaluate this script.
#
if not as_blender_addon:
    cli_args = parser.parse_args()

    if cli_args.end < 0:
        mocaps_dir = os.path.join(cli_args.training_data, 'mocap')
        index_filename = os.path.join(mocaps_dir, "index.json")
        with open(index_filename, 'r') as fp:
            full_index = json.load(fp)
            cli_args.end = len(full_index) - cli_args.end
            if cli_args.debug:
                print("Inferred --end=%d" % cli_args.end)

    blend_filename = os.path.join(cli_args.training_data,
                                  'blender', 'glimpse-training.blend')
    if cli_args.subcommand == 'preload' and cli_args.blend_file:
        blend_filename = cli_args.blend_file

    blender_cmd = [
            'blender', '-b',
            blend_filename,
            '-P',
            os.path.abspath(sys.argv[0]),
            '--']

    # The render command is special because we might want to spawn multiple
    # instances of blender...
    #
    if cli_args.subcommand == 'render':

        if cli_args.dest == "":
            sys.exit("--dest argument required in this case to find files to preload")

        training_data = cli_args.training_data
        name = cli_args.name
        dest = cli_args.dest

        n_mocaps = cli_args.end - cli_args.start
        if cli_args.num_instances > n_mocaps:
            cli_args.num_instances = n_mocaps

        step = int(n_mocaps / cli_args.num_instances)

        print("Rendering %d mocap sequences with %d instance[s] of Blender" %
              (n_mocaps, cli_args.num_instances))
        print("Each instance is rendering %d sequences" % step)
        if step * cli_args.num_instances != n_mocaps:
            print("Except last instance is rendering %d sequences" %
                  (n_mocaps - (cli_args.num_instances * step)))

        print("Path to training data is '%s'" % training_data)
        print("Destination is '%s'" % dest)

        processes = []

        n_frames = 0

        status = 0

        for i in range(cli_args.num_instances):
            if cli_args.num_instances > 1:
                part_suffix = '-part-%d' % i
            else:
                part_suffix = ""

            part_name = name + part_suffix

            start = cli_args.start + i * step
            # The last instance may have to do some extra work if the step
            # doesn't factor neatly...
            if i is not cli_args.num_instances - 1:
                end = start + step
            else:
                end = cli_args.end

            # So we don't have to fiddle around with trying to edit
            # the user's given options to change the start/end range
            # for each instance we have some hidden override options
            # instead...
            instance_args = [
                    '--instance-overrides',
                    '--instance-start', str(start),
                    '--instance-end', str(end),
                    '--instance-name', part_name
            ]

            print("Instance %d name: %s" % (i, part_name))

            instance_cmd = blender_cmd + instance_args + sys.argv[1:]
            print("Blender instance %d command:  %s" %
                  (i, " ".join(instance_cmd)))

            # We have some special case handling of dry-run when split across
            # multiple instances since we really want some extra convenience
            # for determining a total frame count
            if cli_args.dry_run:
                try:
                    blender_output = subprocess.check_output(instance_cmd).decode('utf-8')
                    blender_lines = blender_output.splitlines()
                    found_frame_count = False
                    for line in blender_lines:
                        if line.startswith("> DRY RUN FRAME COUNT:"):
                            parts = line.split(":")
                            frame_count = int(parts[1].strip())
                            found_frame_count = True
                            break
                    print(blender_output)
                    if found_frame_count:
                        n_frames += frame_count
                except subprocess.CalledProcessError:
                    status = 1
            else:
                log_filename = os.path.join(dest, part_name,
                                            'render%s.log' % part_suffix)
                print("Instance %d log: %s" % (i, log_filename))
                os.makedirs(os.path.join(dest, part_name), exist_ok=True)
                with open(log_filename, 'w') as fp:
                    p = subprocess.Popen(instance_cmd, stdout=fp, stderr=fp)
                    processes.append(p)

        print("Waiting for all Blender instances to complete...")
        print("")
        for p in processes:
            if p.wait() != 0:
                status = 1

        if status == 1:
            print("WARNING: One of the Blender instances exited with an error")
        elif cli_args.dry_run:
            if n_frames:
                print("Total frame count across all instances = %d" % n_frames)
            print("")
            print("NB: the frame count may double to ~ %d after running the\n"
                  "image-pre-processor if flipping is enabled." %
                  (n_frames * 2))
            print("")

        sys.exit(status)

    else:
        # So we don't have to fiddle around with trying to edit
        # the user's given options to change the start/end range
        # for each instance we have some hidden override options
        # instead...
        instance_args = [
                '--instance-overrides',
                '--instance-start', str(cli_args.start),
                '--instance-end', str(cli_args.end)
        ]

        instance_cmd = blender_cmd + instance_args + sys.argv[1:]
        print("Blender command:  %s" % " ".join(instance_cmd))
        status = subprocess.call(instance_cmd)
        sys.exit(status)


##############################################################################
# From this point on we can assume we are running withing Blender's Python
# environment...

def blender_exit(ret=0):
    if ret:
        print("ERROR: %s" % str(ret), flush=True)
    bpy.ops.wm.quit_blender()
    sys.exit("wm.quite_blender() not synchronous")  # Not expected


if "--" in sys.argv:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

cli_args = parser.parse_args(argv)

addon_dependencies = [
    'glimpse_data_generator',
    'mesh_paint_rig',
    'makeclothes',
    'maketarget',
    'makewalk',
]

dep_error = ""
for dep in addon_dependencies:
    addon_status = addon_utils.check(dep)
    if not addon_status[0] or not addon_status[1]:
        dep_error += ("Addon '%s' has not been enabled through "
                      "Blender's User Preferences\n" % dep)

if dep_error != "":
    print("\n")
    print("Error:\n")
    print(dep_error)
    print("\n")
    print("Please find the instructions for setting up the required addons in blender/README.md")
    print("> https://github.com/glimpse-project/glimpse/blob/master/blender/README.md")
    print("\n")
    sys.exit(1)

bpy.context.scene.GlimpseDebug = cli_args.debug
bpy.context.scene.GlimpseVerbose = cli_args.verbose


# Currently all the subcommands accept filtering options...
if cli_args.instance_overrides:
    bpy.context.scene.GlimpseBvhGenFrom = cli_args.instance_start
    bpy.context.scene.GlimpseBvhGenTo = cli_args.instance_end
else:
    bpy.context.scene.GlimpseBvhGenFrom = cli_args.start
    bpy.context.scene.GlimpseBvhGenTo = cli_args.end

bpy.context.scene.GlimpseBvhTagsWhitelist = cli_args.tags_whitelist
bpy.context.scene.GlimpseBvhTagsBlacklist = cli_args.tags_blacklist

if cli_args.name_match:
    bpy.context.scene.GlimpseBvhNamePatterns = ','.join(cli_args.name_match)


mocaps_dir = os.path.join(cli_args.training_data, 'mocap')
if not os.path.isdir(mocaps_dir):
    blender_exit("Non-existent mocaps directory %s" % mocaps_dir)
bpy.context.scene.GlimpseBvhRoot = mocaps_dir

if cli_args.subcommand == 'info':
    bpy.ops.glimpse.generator_info()
    blender_exit()
elif cli_args.subcommand == 'preload':
    bpy.ops.glimpse.generator_preload()
    if not cli_args.dry_run:
        print("Saving to %s" % bpy.context.blend_data.filepath)
        bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    blender_exit()
elif cli_args.subcommand == 'link':
    bpy.context.scene.GlimpseMocapLibrary = cli_args.mocap_library
    bpy.ops.glimpse.generator_link()
    if not cli_args.dry_run:
        print("Saving to %s" % bpy.context.blend_data.filepath)
        bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    blender_exit()
elif cli_args.subcommand == 'purge':
    bpy.ops.glimpse.purge_mocap_actions()
    if not cli_args.dry_run:
        print("Saving to %s" % bpy.context.blend_data.filepath)
        bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    blender_exit()
elif cli_args.subcommand == 'render':

    bpy.context.scene.GlimpseDataRoot = cli_args.dest
    print("DataRoot: " + cli_args.dest)

    bpy.context.scene.GlimpseDryRun = cli_args.dry_run

    bpy.context.scene.GlimpseMinCameraDistanceMM = bpy.context.scene.GlimpseMinCameraDistanceMM

    skip_percentage = 0

    if cli_args.config:
        with open(cli_args.config, 'r') as fp:
            config = json.load(fp)

            def check_scalar(obj, obj_namespace, prop, minimum, maximum, scale):
                if prop in obj:
                    val = obj[prop]
                    if val < minimum:
                        blender_exit("%s.%s=%f < minimum of %f" % (obj_namespace, prop, val, minimum))
                    if val > maximum:
                        blender_exit("%s.%s=%f > maximum of %f" % (obj_namespace, prop, val, maximum))
                    return val * scale
                else:
                    blender_exit("Config missing %s.%s value" % (obj_namespace, name))
                    return 0

            if 'filters' in config:
                filters = config['filters']
                skip_percentage = filters.get('skip_percentage', 0)

                body_whitelist = filters.get('body_whitelist', 'all')
                if body_whitelist is not 'all':
                    bpy.context.scene.GlimpseBodyWhitelist = ','.join(body_whitelist)

                clothes_whitelist = filters.get('clothes_whitelist', 'all')
                if clothes_whitelist is not 'all':
                    bpy.context.scene.GlimpseClothesWhitelist = ','.join(clothes_whitelist)

                if 'tag_skip_percentages' in filters:
                    tag_skip_percentages = filters['tag_skip_percentages']
                    tag_skip_strings = []
                    for key in tag_skip_percentages:
                        val = tag_skip_percentages[key]
                        if val < 0 or val > 100:
                            blender_exit("Skip percentage for '%s' tag out of range [0,100]" % key)
                        tag_skip_strings += ["%s=%d" % (key, val)]
                    bpy.context.scene.GlimpseBvhTagsSkip = ",".join(tag_skip_strings)

            if 'camera' not in config:
                blender_exit('config must include "camera" description')

            camera = config['camera']

            bpy.context.scene.GlimpseRenderWidth = \
                check_scalar(camera, 'camera', 'width', 240, 2048, 1)
            bpy.context.scene.GlimpseRenderHeight = \
                check_scalar(camera, 'camera', 'height', 240, 2048, 1)

            bpy.context.scene.GlimpseVerticalFOV = \
                check_scalar(camera, 'camera', 'vertical_fov', 20, 170, 1)

            if 'position' not in camera:
                blender_exit('config "camera" must include "position"')
            camera_pos = camera['position']

            if 'mode' not in camera_pos:
                blender_exit('config camera.position must specify a "mode"')

            camera_mode = camera_pos['mode']

            if camera_mode == 'randomized':
                bpy.context.scene.GlimpseMinCameraDistanceMM = \
                    check_scalar(camera_pos, 'camera.position', 'min_distance',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMaxCameraDistanceMM = \
                    check_scalar(camera_pos, 'camera.position', 'max_distance',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMinCameraHeightMM = \
                    check_scalar(camera_pos, 'camera.position', 'min_height',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMaxCameraHeightMM = \
                    check_scalar(camera_pos, 'camera.position', 'max_height',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMinViewingAngle = \
                    check_scalar(camera_pos, 'camera.position', 'min_horizontal_rotation',
                                 -180, 180, 1)
                bpy.context.scene.GlimpseMaxViewingAngle = \
                    check_scalar(camera_pos, 'camera.position', 'max_horizontal_rotation',
                                 -180, 180, 1)

                if (bpy.context.scene.GlimpseMaxCameraDistanceMM <
                        bpy.context.scene.GlimpseMinCameraDistanceMM):
                    blender_exit("Maximum camera distance must be >= minimum camera distance")

                if (bpy.context.scene.GlimpseMaxCameraHeightMM <
                        bpy.context.scene.GlimpseMinCameraHeightMM):
                    blender_exit("Maximum camera height must be >= minimum camera height")

                if (bpy.context.scene.GlimpseMaxViewingAngle <
                        bpy.context.scene.GlimpseMinViewingAngle):
                    blender_exit("Min viewing angle is higher than or equal to max viewing angle")

                if 'focus_bone' in camera_pos:
                    bpy.context.scene.GlimpseFocusBone = camera_pos['focus_bone']

            elif camera_mode == 'smooth':
                bpy.context.scene.GlimpseSmoothCameraMovement = True

                bpy.context.scene.GlimpseMinCameraDistanceMM = \
                    check_scalar(camera_pos, 'camera.position', 'min_distance',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMaxCameraDistanceMM = \
                    check_scalar(camera_pos, 'camera.position', 'max_distance',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMinCameraHeightMM = \
                    check_scalar(camera_pos, 'camera.position', 'min_height',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMaxCameraHeightMM = \
                    check_scalar(camera_pos, 'camera.position', 'max_height',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMinViewingAngle = \
                    check_scalar(camera_pos, 'camera.position', 'min_horizontal_rotation',
                                 -180, 180, 1)
                bpy.context.scene.GlimpseMaxViewingAngle = \
                    check_scalar(camera_pos, 'camera.position', 'max_horizontal_rotation',
                                 -180, 180, 1)
                bpy.context.scene.GlimpseSmoothCameraFrequency = \
                    check_scalar(camera_pos, 'camera.position', 'drift_frequency',
                                 0, 100, 1)

                if (bpy.context.scene.GlimpseMaxCameraDistanceMM <
                        bpy.context.scene.GlimpseMinCameraDistanceMM):
                    blender_exit("Maximum camera distance must be >= minimum camera distance")

                if (bpy.context.scene.GlimpseMaxCameraHeightMM <
                        bpy.context.scene.GlimpseMinCameraHeightMM):
                    blender_exit("Maximum camera height must be >= minimum camera height")

                if (bpy.context.scene.GlimpseMaxViewingAngle <
                        bpy.context.scene.GlimpseMinViewingAngle):
                    blender_exit("Min viewing angle is higher than or equal to max viewing angle")

                if 'focus_bone' in camera_pos:
                    bpy.context.scene.GlimpseFocusBone = camera_pos['focus_bone']
            elif camera_mode == 'fixed':
                bpy.context.scene.GlimpseFixedCamera = True

                bpy.context.scene.GlimpseMinCameraDistanceMM = \
                    check_scalar(camera_pos, 'camera.position', 'distance',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMinCameraHeightMM = \
                    check_scalar(camera_pos, 'camera.position', 'height',
                                 0, 20, 1000)
                bpy.context.scene.GlimpseMinViewingAngle = \
                    check_scalar(camera_pos, 'camera.position', 'horizontal_rotation',
                                 -180, 180, 1)

                if 'focus_bone' in camera_pos:
                    bpy.context.scene.GlimpseFocusBone = camera_pos['focus_bone']

            elif camera_mode == 'debug':
                bpy.context.scene.GlimpseDebugCamera = True
            else:
                blender_exit('Unknown camera mode: %s (expected "randomized",'
                             ' "smooth", "fixed" or "debug")')

            if 'add_background' in config:
                bpy.context.scene.GlimpseAddBackground = config['add_background']
            if 'clothing_step' in config:
                bpy.context.scene.GlimpseClothingStep = config['clothing_step']

    # Note: some command line options may override the given --config

    if cli_args.tags_whitelist != 'all':
        # XXX: maybe it would be better to union with whatever is in the
        # config?
        bpy.context.scene.GlimpseBvhTagsWhitelist = cli_args.tags_whitelist
    if cli_args.tags_blacklist != 'none':
        # XXX: maybe it would be better to union with whatever is in the
        # config?
        bpy.context.scene.GlimpseBvhTagsBlacklist = cli_args.tags_blacklist

    if cli_args.skip_percentage:
        skip_percentage = cli_args.skip_percentage

    if skip_percentage < 0 or skip_percentage > 100:
        blender_exit("'skip_percentage' %d out of range [0,100]" % skip_percentage)

    bpy.context.scene.GlimpseSkipPercentage = skip_percentage

    if cli_args.instance_overrides and cli_args.instance_name:
        render_name = cli_args.instance_name
    else:
        render_name = cli_args.name

    if render_name == "":
        print("--name argument required in this case to determine where to write results")
        bpy.ops.wm.quit_blender()
    bpy.context.scene.GlimpseGenDir = render_name

    print("Rendering Info:")
    print("Name: " + render_name)
    print("Dest: " + bpy.context.scene.GlimpseDataRoot)

    if not cli_args.dry_run:
        import cProfile
        cProfile.run("bpy.ops.glimpse.generate_data()",
                     os.path.join(cli_args.dest,
                                  render_name,
                                  "glimpse-" + render_name + ".prof"))

        import pstats
        p = pstats.Stats(os.path.join(cli_args.dest,
                                      render_name,
                                      "glimpse-" + render_name + ".prof"))
        p.sort_stats("cumulative").print_stats(20)
    else:
        bpy.ops.glimpse.generate_data()

    blender_exit()
