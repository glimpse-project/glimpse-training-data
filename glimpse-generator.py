#!/usr/bin/env python3

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

# Detect whether the script is running under Blender or not...
try:
    import bpy
    import addon_utils
    as_blender_addon = True
except:
    as_blender_addon = False

if as_blender_addon:
    parser = argparse.ArgumentParser(prog="glimpse-generator", add_help=False)
    parser.add_argument('--help-glimpse', help='Show this help message and exit', action='help')
    # used to override --name/start/end if we split the user's given start/end
    # range across multiple Blender instances...
    parser.add_argument('--instance-overrides', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--instance-name', help=argparse.SUPPRESS)
    parser.add_argument('--instance-start', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--instance-end', type=int, help=argparse.SUPPRESS)
else:
    parser = argparse.ArgumentParser(prog="glimpse-generator")

subparsers = parser.add_subparsers(dest='subcommand')

dt = datetime.datetime.today()
date_str = "%04u-%02u-%02u-%02u-%02u-%02u" % (dt.year,
        dt.month, dt.day, dt.hour, dt.minute, dt.second)

parser.add_argument('--debug', action='store_true', help="Enable extra debug messages")
parser.add_argument('--verbose', action='store_true', help="Enable more verbose debug messages")

parser.add_argument('--training-data', default=os.path.dirname(os.path.realpath(__file__)), help="Path to training data")


parser_info = subparsers.add_parser('info', help='Load the mocap index and print summary information')
parser_info.add_argument('--start', type=int, default=20, help='Index of first MoCap to render')
parser_info.add_argument('--end', default=25, type=int, help='Index of last MoCap to render')


parser_preload = subparsers.add_parser('preload', help='Preload mocap files as actions before rendering')
parser_preload.add_argument('--start', type=int, default=20, help='Index of first MoCap to render')
parser_preload.add_argument('--end', default=25, type=int, help='Index of last MoCap to render')
parser_preload.add_argument('--dry-run', help="Don't save the results", action='store_true')


parser_purge = subparsers.add_parser('purge', help='Purge mocap actions')
parser_purge.add_argument('--start', type=int, default=20, help='Index of first MoCap to render')
parser_purge.add_argument('--end', default=25, type=int, help='Index of last MoCap to render')
parser_purge.add_argument('--dry-run', help="Don't save the results", action='store_true')


parser_link = subparsers.add_parser('link', help='Link mocap actions')
parser_link.add_argument('--mocap-library', default="//glimpse-training-mocap-library.blend", help='.blend file library with preloaded mocap actions (default //glimpse-training-mocap-library.blend)')
parser_link.add_argument('--start', type=int, default=20, help='Index of first MoCap to render')
parser_link.add_argument('--end', default=25, type=int, help='Index of last MoCap to render')
parser_link.add_argument('--dry-run', help="Don't save the results", action='store_true')


parser_render = subparsers.add_parser('render', help='Render data')

parser_render.add_argument('--dest', default=os.path.join(os.getcwd(), 'renders'), help='Directory to write files too')
parser_render.add_argument('--name', default=date_str, help='Unique name for this render run')

parser_render.add_argument('--config', help='Detailed configuration for the generator addon')
parser_render.add_argument('--dry-run', help='Just print information without rendering', action='store_true')


parser_render.add_argument('--start', type=int, default=20, help='Index of first MoCap to render')
parser_render.add_argument('--end', default=25, type=int, help='Index of last MoCap to render')
# TODO: support being able to give an explicit bvh name instead of --start/end

parser_render.add_argument('-j', '--num-instances', type=int, default=1, help='Number of Blender instances to run for rendering')

# TODO: Move all of these into a .json config
parser_render.add_argument('--tags-whitelist', default='all', help='A set of specified tags for index entries that will be rendered - needs to be comma separated (default \'all\')')
parser_render.add_argument('--tags-blacklist', default='blacklist', help='A set of specified tags for index entries that will not be rendered - needs to be comma separated (default \'blacklist\')')
parser_render.add_argument('--tags-skip', nargs='+', action='append', help='(random) tag-based percentage of frames to skip (default \'none\'). The tags and percentages need to be provided in a <tag>=<integer> format.') 

parser_render.add_argument('--width', default=320, type=int, help='Width, in pixels, of rendered frames (default 320)')
parser_render.add_argument('--height', default=240, type=int, help='Height, in pixels, of rendered frames (default 240)')
parser_render.add_argument('--vertical-fov', default=43.940769, type=float, help='Vertical field of view of camera (degrees, default = 43.94)')
parser_render.add_argument('--min-camera-distance', default=2, type=float, help='Minimum distance of camera from person (meters, default 2m)')
parser_render.add_argument('--max-camera-distance', default=2.5, type=float, help='Maximum distance of camera from person (meters, default 2.5m)')
parser_render.add_argument('--min-camera-height', default=1.1, type=float, help='Minimum height of camera (meters, default 1.1m)')
parser_render.add_argument('--max-camera-height', default=1.4, type=float, help='Maximum height of camera (meters, default 1.4m)')
parser_render.add_argument('--min-camera-angle', default=-30, type=int, help='Min viewing angle deviation (measured from face-on direction, default=-30)')
parser_render.add_argument('--max-camera-angle', default=0, type=int, help='Max viewing angle deviation (measured from face-on direction, default=0)')
parser_render.add_argument('--fixed-camera', help='Lock camera in a fixed position using the specified min parameters', action='store_true')
parser_render.add_argument('--debug-camera', help='Lock camera straight in front of a model in order to debug glimpse viewer', action='store_true')
parser_render.add_argument('--smooth-camera-movement', help='Smooth camera movement (disable randomization of the camera position and orientation)', action='store_true')
parser_render.add_argument('--smooth-camera-frequency', default=1, type=int, help='Period at which data is sampled when --smooth-camera-movement is enabled (frequency, default=1)')
parser_render.add_argument('--focus-bone', default='pelvis', help='Bone in the armature the camera will focus on during renders (bone name in the armature, default=pelvis)')

parser_render.add_argument('--skip-percentage', type=int, default=0, help='(random) percentage of frames to skip (default 0)')
parser_render.add_argument('--clothing-step', type=int, default=5, help='randomize the clothing items every N frames (default 5)')
parser_render.add_argument('--fixed-bodies', default='none', help='A set specified bodies to be used in all renders - needs to be comma separated (default \'none\')')
parser_render.add_argument('--fixed-clothes', default='none', help='A set of specified clothes to be used in all renders - needs to be comma separated (default \'none\')')
parser_render.add_argument('--added-background', help='Add background in a form of a floor and walls', action='store_true')


# If this script is run from the command line and we're not yet running within
# Blender's Python environment then we will spawn Blender and tell it to
# re-evaluate this script.
#
# In this case we handle a few extra arguments at this point such as being able
# to control how many instances of Blender should be run to handle rendering
#
if not as_blender_addon:
    cli_args = parser.parse_args()

    blender_cmd = [
            'blender', '-b',
            os.path.join(cli_args.training_data, 'blender', 'glimpse-training.blend'),
            '-P',
            os.path.abspath(sys.argv[0]),
            '--']

    if cli_args.subcommand == 'render':

        if cli_args.dest == "":
            sys.exit("--dest argument required in this case to find files to preload")

        if cli_args.skip_percentage < 0 or cli_args.skip_percentage > 100:
            sys.exit("Skip percetange out of range [0,100]")

        if cli_args.tags_skip is not None:
            tags_skip = cli_args.tags_skip[0]
            for skip_tag in tags_skip:
                tag_data = skip_tag.split("=")
                if int(tag_data[1]) > 100 or int(tag_data[1]) < 0:
                    sys.exit("Skip percetange for '%s' tag out of range [0,100]" % tag_data[0])

        if cli_args.clothing_step <= 0 or cli_args.clothing_step > 1000:
            sys.exit("Clothing step out of range [1,1000]")

        if cli_args.min_camera_angle < -180 or cli_args.min_camera_angle > 180:
            sys.exit("Min viewing angle out of range [-180,180]]")
        if cli_args.max_camera_angle < -180 or cli_args.max_camera_angle > 180:
            sys.exit("Max viewing angle out of range [-180,180]]")
        if not cli_args.fixed_camera and (cli_args.min_camera_angle >= cli_args.max_camera_angle):
            sys.exit("Min viewing angle is higher than or equal to max viewing angle")
        if not cli_args.fixed_camera and (cli_args.max_camera_angle <= cli_args.min_camera_angle):
            sys.exit("Max viewing angle is less than or equal to min viewing angle")
        if not cli_args.fixed_camera and (cli_args.max_camera_distance <= cli_args.min_camera_distance):
            sys.exit("Maximum camera distance must be >= minimum camera distance")
        if not cli_args.fixed_camera and (cli_args.max_camera_height <= cli_args.min_camera_height):
            sys.exit("Maximum camera height must be >= minimum camera height")

        training_data = cli_args.training_data
        name = cli_args.name
        dest = cli_args.dest

        n_mocaps = cli_args.end - cli_args.start
        step = int(n_mocaps / cli_args.num_instances)

        print("Rendering %d motion capture sequences with %d instance[s] of Blender" % (n_mocaps, cli_args.num_instances))
        print("Each instance is rendering %d sequences" % step)
        print("Path to training data is '%s'" % training_data)
        print("Destination is '%s'" % dest)

        if step * cli_args.num_instances != n_mocaps:
            sys.exit("Instance count of %d doesn't factor into count of %d motion capture sequences" %
                     (cli_args.num_instances, n_mocaps))

        processes = []

        n_frames = 0

        for i in range(cli_args.num_instances):
            if cli_args.num_instances > 1:
                part_suffix = '-part-%d' % i
            else:
                part_suffix = ""

            part_name = name + part_suffix

            start = cli_args.start + i * step
            end = start + step

            instance_args = [
                    '--instance-overrides',
                    '--instance-start', str(start),
                    '--instance-end', str(end),
                    '--instance-name', part_name
            ]

            print("Instance %d name: %s" % (i, part_name))

            instance_cmd = blender_cmd + instance_args + sys.argv[1:]
            print("Blender instance " + str(i) + " command:  " + " ".join(instance_cmd))

            # We have some special case handling of dry-run when split across
            # multiple instances since we really want some extra convenience
            # for determining a total frame count
            if cli_args.dry_run:
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
            else:
                log_filename = os.path.join(dest, part_name, 'render%s.log' % part_suffix)
                print("Instance %d log: %s" % (i, log_filename))
                os.makedirs(os.path.join(dest, part_name), exist_ok=True)
                with open(log_filename, 'w') as fp:
                    p = subprocess.Popen(instance_cmd, stdout=fp, stderr=fp)
                    processes.append(p)

        print("Waiting for all Blender instances to complete...")
        print("")
        status = 0
        for p in processes:
            if p.wait() != 0:
                status = 1

        if cli_args.dry_run:
            if n_frames:
                print("Total frame count across all instances = %d" % n_frames)
            print("")
            print("NB: the frame count may double to ~ %d after running the " % (n_frames * 2))
            print("image-pre-processor if flipping is enabled.")
            print("")

        sys.exit(status)

    elif not as_blender_addon:
        status = subprocess.call(blender_cmd + sys.argv[1:])
        sys.exit(status)

##############################################################################
# From this point on we can assume we are running withing Blender's Python
# environment...


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
    if addon_status[0] != True or addon_status[1] != True:
        dep_error += "Addon '" + dep + "' has not been enabled through Blender's User Preferences\n"

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

if cli_args.instance_overrides:
    bpy.context.scene.GlimpseBvhGenFrom = cli_args.instance_start
    bpy.context.scene.GlimpseBvhGenTo = cli_args.instance_end
else:
    bpy.context.scene.GlimpseBvhGenFrom = cli_args.start
    bpy.context.scene.GlimpseBvhGenTo = cli_args.end

mocaps_dir = os.path.join(cli_args.training_data, 'mocap')
if not os.path.isdir(mocaps_dir):
    print("Non-existent mocaps directory %s" % mocaps_dir)
    bpy.ops.wm.quit_blender()
    sys.exit(1)
bpy.context.scene.GlimpseBvhRoot = mocaps_dir

if cli_args.subcommand == 'info':
    bpy.ops.glimpse.generator_info()
    bpy.ops.wm.quit_blender()
elif cli_args.subcommand == 'preload':
    bpy.ops.glimpse.generator_preload()
    if not cli_args.dry_run:
        print("Saving to %s" % bpy.context.blend_data.filepath)
        bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    bpy.ops.wm.quit_blender()
elif cli_args.subcommand == 'link':
    bpy.context.scene.GlimpseMocapLibrary = cli_args.mocap_library
    bpy.ops.glimpse.generator_link()
    if not cli_args.dry_run:
        print("Saving to %s" % bpy.context.blend_data.filepath)
        bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    bpy.ops.wm.quit_blender()
elif cli_args.subcommand == 'purge':
    bpy.ops.glimpse.purge_mocap_actions()
    if not cli_args.dry_run:
        print("Saving to %s" % bpy.context.blend_data.filepath)
        bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    bpy.ops.wm.quit_blender()
elif cli_args.subcommand == 'render':

    bpy.context.scene.GlimpseDataRoot = cli_args.dest
    print("DataRoot: " + cli_args.dest)

    bpy.context.scene.GlimpseDryRun = cli_args.dry_run

    bpy.context.scene.GlimpseSkipPercentage = cli_args.skip_percentage
    bpy.context.scene.GlimpseBvhTagsWhitelist = cli_args.tags_whitelist
    bpy.context.scene.GlimpseBvhTagsBlacklist = cli_args.tags_blacklist

    if cli_args.tags_skip is not None:
        tags_skip = cli_args.tags_skip[0]
        tags_skipped = ""
        for skip_tag in tags_skip:
            tag_data = skip_tag.split("=")
            tags_skipped += "%s=%s#" % (tag_data[0], tag_data[1])
    else:
        tags_skipped = ""

    bpy.context.scene.GlimpseBvhTagsSkip = tags_skipped

    bpy.context.scene.GlimpseRenderWidth = cli_args.width
    bpy.context.scene.GlimpseRenderHeight = cli_args.height
    bpy.context.scene.GlimpseVerticalFOV = cli_args.vertical_fov

    bpy.context.scene.GlimpseMinCameraDistanceMM = int(cli_args.min_camera_distance * 1000)
    bpy.context.scene.GlimpseMaxCameraDistanceMM = int(cli_args.max_camera_distance * 1000)
    bpy.context.scene.GlimpseMinCameraHeightMM = int(cli_args.min_camera_height * 1000)
    bpy.context.scene.GlimpseMaxCameraHeightMM = int(cli_args.max_camera_height * 1000)
    bpy.context.scene.GlimpseMinViewingAngle = cli_args.min_camera_angle
    bpy.context.scene.GlimpseMaxViewingAngle= cli_args.max_camera_angle

    bpy.context.scene.GlimpseFixedCamera = cli_args.fixed_camera
    bpy.context.scene.GlimpseDebugCamera = cli_args.debug_camera
    bpy.context.scene.GlimpseSmoothCameraMovement = cli_args.smooth_camera_movement
    bpy.context.scene.GlimpseSmoothCameraFrequency = cli_args.smooth_camera_frequency
    bpy.context.scene.GlimpseFocusBone = cli_args.focus_bone

    bpy.context.scene.GlimpseClothingStep = cli_args.clothing_step
    bpy.context.scene.GlimpseFixedBodies = cli_args.fixed_bodies
    bpy.context.scene.GlimpseFixedClothes = cli_args.fixed_clothes

    bpy.context.scene.GlimpseAddedBackground = cli_args.added_background

    bpy.context.scene.GlimpseShowStats = True

    if cli_args.instance_overrides:
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
        cProfile.run("bpy.ops.glimpse.generate_data()", os.path.join(cli_args.dest, render_name, "glimpse-" + render_name + ".prof"))

        import pstats
        p = pstats.Stats(os.path.join(cli_args.dest, render_name, "glimpse-" + render_name + ".prof"))
        p.sort_stats("cumulative").print_stats(20)
    else:
        bpy.ops.glimpse.generate_data()
