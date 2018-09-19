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
else:
    parser = argparse.ArgumentParser(prog="glimpse-generator")

dt = datetime.datetime.today()
date_str = "%04u-%02u-%02u-%02u-%02u-%02u" % (dt.year,
        dt.month, dt.day, dt.hour, dt.minute, dt.second)

parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
parser.add_argument('--info', help='Load the mocap index and print summary information', action='store_true')
parser.add_argument('--preload', help='Preload mocap files as actions before rendering', action='store_true')
parser.add_argument('--purge', help='Purge mocap actions', action='store_true')
parser.add_argument('--link', help='Link mocap actions', action='store_true')
parser.add_argument('--start', type=int, default=20, help='Index of first MoCap to render')
parser.add_argument('--end', default=25, type=int, help='Index of last MoCap to render')

parser.add_argument('--width', default=172, type=int, help='Width, in pixels, of rendered frames (default 172)')
parser.add_argument('--height', default=224, type=int, help='Height, in pixels, of rendered frames (default 224)')
parser.add_argument('--vertical-fov', default=54.5, type=float, help='Vertical field of view of camera (degrees, default = 54.5)')
parser.add_argument('--min-camera-distance', default=2, type=float, help='Minimum distance of camera from person (meters, default 2m)')
parser.add_argument('--max-camera-distance', default=2.5, type=float, help='Maximum distance of camera from person (meters, default 2.5m)')
parser.add_argument('--min-camera-height', default=1.1, type=float, help='Minimum height of camera (meters, default 1.1m)')
parser.add_argument('--max-camera-height', default=1.4, type=float, help='Maximum height of camera (meters, default 1.4m)')
parser.add_argument('--min-camera-angle', default=-30, type=int, help='Min viewing angle deviation (measured from face-on direction, default=-30)')
parser.add_argument('--max-camera-angle', default=0, type=int, help='Max viewing angle deviation (measured from face-on direction, default=0)')
parser.add_argument('--fixed-camera', help='Lock camera in a fixed position using the specified min parameters', action='store_true')
parser.add_argument('--smooth-camera-movement', help='Smooth camera movement (disable randomization of the camera position and orientation)', action='store_true')
parser.add_argument('--smooth-camera-frequency', default=1, type=int, help='Period at which data is sampled when --smooth-camera-movement is enabled (frequency, default=1)')

parser.add_argument('--dest', default=os.path.join(os.getcwd(), 'renders'), help='Directory to write files too')
parser.add_argument('--name', default=date_str, help='Unique name for this render run')
parser.add_argument('--mocap-library', default="//glimpse-training-mocap-library.blend", help='.blend file library with preloaded mocap actions (default //glimpse-training-mocap-library.blend)')
parser.add_argument('--dry-run', help='Just print information without rendering', action='store_true')
parser.add_argument('--skip-percentage', type=int, default=0, help='(random) percentage of frames to skip (default 0)')
parser.add_argument('--clothing-step', type=int, default=5, help='randomize the clothing items every N frames (default 5)')
parser.add_argument('--fixed-bodies', default='none', help='A set specified bodies to be used in all renders - needs to be comma separated (default \'none\')')
parser.add_argument('--fixed-clothes', default='none', help='A set of specified clothes to be used in all renders - needs to be comma separated (default \'none\')')

parser.add_argument('training_data', help='Directory with all training data')

def run_cmd(args):
    if cli_args.debug:
        print("# " + " ".join(map(str, args)), file=sys.stderr)
        returncode = subprocess.call(args)
        print("# return status = " + str(returncode))
        return returncode
    else:
        return subprocess.call(args)

if as_blender_addon:
    if "--" in sys.argv:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    cli_args = parser.parse_args(argv)
else:
    cli_args = parser.parse_args()
    ret = run_cmd(['blender', '-b',
                   os.path.join(cli_args.training_data, 'blender', 'glimpse-training.blend'),
                   '-P',
                   sys.argv[0],
                   '--'] +
                   sys.argv[1:])
    sys.exit(ret)

if cli_args.skip_percentage < 0 or cli_args.skip_percentage > 100:
    sys.exit("Skip perctange out of range [0,100]")

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

#
# XXX: from here on, we know we are running within Blender...
#

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

bpy.context.scene.GlimpseRenderWidth = cli_args.width
bpy.context.scene.GlimpseRenderHeight = cli_args.height
bpy.context.scene.GlimpseVerticalFOV = cli_args.vertical_fov

bpy.context.scene.GlimpseMinCameraDistanceMM = int(cli_args.min_camera_distance * 1000)
bpy.context.scene.GlimpseMaxCameraDistanceMM = int(cli_args.max_camera_distance * 1000)
bpy.context.scene.GlimpseMinCameraHeightMM = int(cli_args.min_camera_height * 1000)
bpy.context.scene.GlimpseMaxCameraHeightMM = int(cli_args.max_camera_height * 1000)
bpy.context.scene.GlimpseMinViewingAngle = cli_args.min_camera_angle
bpy.context.scene.GlimpseMaxViewingAngle= cli_args.max_camera_angle
bpy.context.scene.GlimpseMocapLibrary = cli_args.mocap_library
bpy.context.scene.GlimpseBvhGenFrom = cli_args.start
bpy.context.scene.GlimpseBvhGenTo = cli_args.end
bpy.context.scene.GlimpseDryRun = cli_args.dry_run
bpy.context.scene.GlimpseSkipPercentage = cli_args.skip_percentage
bpy.context.scene.GlimpseClothingStep = cli_args.clothing_step
bpy.context.scene.GlimpseFixedCamera = cli_args.fixed_camera
bpy.context.scene.GlimpseFixedBodies= cli_args.fixed_bodies
bpy.context.scene.GlimpseFixedClothes= cli_args.fixed_clothes
bpy.context.scene.GlimpseSmoothCameraMovement= cli_args.smooth_camera_movement
bpy.context.scene.GlimpseSmoothCameraFrequency= cli_args.smooth_camera_frequency

mocaps_dir = os.path.join(cli_args.training_data, 'mocap')
if not os.path.isdir(mocaps_dir):
    print("Non-existent mocaps directory %s" % mocaps_dir)
    bpy.ops.wm.quit_blender()
    sys.exit(1)
bpy.context.scene.GlimpseBvhRoot = mocaps_dir

bpy.ops.glimpse.open_bvh_index()

if cli_args.info:
    bpy.ops.glimpse.generator_info()
    bpy.ops.wm.quit_blender()

if cli_args.preload:
    bpy.ops.glimpse.generator_preload()
    print("Saving to %s" % bpy.context.blend_data.filepath)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    bpy.ops.wm.quit_blender()
elif cli_args.link:
    bpy.ops.glimpse.generator_link()
    print("Saving to %s" % bpy.context.blend_data.filepath)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    bpy.ops.wm.quit_blender()
elif cli_args.purge:
    bpy.ops.glimpse.purge_mocap_actions()
    print("Saving to %s" % bpy.context.blend_data.filepath)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.context.blend_data.filepath)
    bpy.ops.wm.quit_blender()

if cli_args.dest == "":
    print("--dest argument required in this case to find files to preload")
    bpy.ops.wm.quit_blender()

bpy.context.scene.GlimpseDataRoot = cli_args.dest
print("DataRoot: " + cli_args.dest)

if cli_args.name == "":
    print("--name argument required in this case to find files to preload")
    bpy.ops.wm.quit_blender()
bpy.context.scene.GlimpseGenDir = cli_args.name

print("Rendering Info:")
print("Name: " + cli_args.name)
print("Dest: " + bpy.context.scene.GlimpseDataRoot)

import cProfile
cProfile.run("bpy.ops.glimpse.generate_data()", "glimpse-" + cli_args.name + ".prof")

import pstats
p = pstats.Stats("glimpse-" + cli_args.name + ".prof")
p.sort_stats("cumulative").print_stats(20)
