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
import sys
import ntpath
import argparse
import json
import random
import shutil
import math
import subprocess
import datetime

parser = argparse.ArgumentParser()

parser.add_argument('--source', default=os.path.join(os.getcwd(), 'pre-processed'), help='Directory with rendered frames to assemble video from')
parser.add_argument('--dest', default=os.path.join(os.getcwd(), 'films'), help='Directory where the output video will be stored')
parser.add_argument("--flipped", action="store_true", help='When enabled, the video will be assembled only from flipped images')
parser.add_argument("--non-flipped", action="store_true", help='When enabled, the video will be assembled only from non flipped images')
parser.add_argument("--fps", default="1", help='Desired framerate of the video being assembled defined in fps (default 1)')
parser.add_argument("--skip-percentage", default="0", type=int, help='Exclude percentage of frames from assembled video')
parser.add_argument("--resolution", default="640x480", help='The resolution of the output video (default 640x480)')
parser.add_argument("--fontsize", default="12", help='The font size of the captions (needs to be between 10 and 16, default 12)')
parser.add_argument("--video-length", default="30", type=int, help='The treshold defining the maximum video length (specified in minutes - max 180 - default 30)') 

args = parser.parse_args()

if int(args.video_length) < 0 or int(args.video_length) > 180:
    print("Video cannot be less than 0 and longer than 180 minutes")
    sys.exit()

if int(args.fontsize) < 10 or int(args.fontsize) > 16:
    print("Fontsize needs to be between 10 and 16")
    sys.exit()

if int(args.fps) < 1 or int(args.fps) > 120:
    print("The FPS cannot be smaller than 1 or greater than 120")
    sys.exit()

MILLIS_HRS = 3600000
MILLIS_MINS = 60000
MILLIS_VIDEO_LENGTH = int(args.video_length) * MILLIS_MINS

dt = datetime.datetime.today()
date_str = "%04u-%02u-%02u-%02u-%02u-%02u" % (dt.year, dt.month, dt.day,
                                              dt.hour, dt.minute, dt.second)

def getTimeCode(time):
    hrs = int(time / MILLIS_HRS)
    time = time - (hrs * MILLIS_HRS)
    mins = int(time / MILLIS_MINS)
    time = time - (mins * MILLIS_MINS)
    secs = int(time / 1000)
    time = time - (secs * 1000)
    ms = time
    timecode = ("%02d:%02d:%02d,%03d" % (hrs,mins,secs,ms)) 
    return timecode

print("Assembling video...")
i = 0
skipped_frames = []
for dirName, subdirList, fileList in os.walk(args.source, topdown=True):
    dirPath = os.path.normpath(dirName)
    dirPathList = dirPath.split(os.sep)
    if 'labels' in dirPathList and dirPathList[len(dirPathList)-1] != 'labels':
        for fname in fileList:
            if fname.endswith('.png'):
            
                if args.flipped and "-flipped" not in fname:  
                    continue

                if args.non_flipped and "-flipped" in fname:
                    continue

                if random.randrange(0, 100) < args.skip_percentage:
                    skipped_frames.append(str(i) + '_' + fname)
                    continue
                
                if (1 / int(args.fps) * 1000) * i > MILLIS_VIDEO_LENGTH:
                    break
                
                i += 1                                 
                filename = "%04d_%s" % (i, fname)
                shutil.copyfile(dirName + '/' + fname, args.dest + '/' + filename)
        else:
            continue
        break

print("Assembling captions...")
subtitles = open(args.dest + "/" + date_str + "-subtitles.srt","w")
for dirName, subdirList, fileList in os.walk(args.source, topdown=True):
    dirPath = os.path.normpath(dirName)
    dirPathList = dirPath.split(os.sep)
    for fname in fileList:
        if fname.endswith('.full'):
            index_full = open(dirName + '/' + fname, "r")
            i = 0
            for index_file in index_full:
                index_file = index_file.rstrip('\n')
                
                if args.flipped and "-flipped" not in index_file:
                    continue

                if args.non_flipped and "-flipped" in index_file:
                    continue

                image_file = index_file.split('/')
                if str(i) + '_' + image_file[len(image_file)-1] + '.png' in skipped_frames:
                    continue 
                
                if (1 / int(args.fps) * 1000) * i > MILLIS_VIDEO_LENGTH:
                    break

                time = (1 / int(args.fps) * 1000) * i
                timecode_from = getTimeCode(time)
                timecode_to = getTimeCode(time + 1 / int(args.fps) * 1000)
                with open(dirName  + '/labels' + index_file + '.json') as fp:
                    bvh_index = json.load(fp)
                    subtitles.write(str(i) + "\n")
                    subtitles.write(timecode_from + " --> " + timecode_to + "\n")
                    subtitles.write("File: " + index_file + ".png\n" + 
                                    "Bvh: " + str(bvh_index['bvh']) + "\n" +
                                    "Frame: " + str(bvh_index['frame']) + "\n")
                subtitles.write("\n")
                i += 1                                            
            subtitles.close() 
            break

#called at the end to assemble video   
subprocess.call('ffmpeg' 
                ' -framerate ' + args.fps + 
                ' -pattern_type glob -i "' + args.dest + '/*.png"' 
                ' -vf subtitles=' + args.dest + 
                '/' + date_str + '-subtitles.srt'
                ':force_style=\'Fontsize=' + args.fontsize + '\''
                ' -s ' + args.resolution + ' -pix_fmt yuv420p ' + 
                args.dest + '/' + date_str + '-review.mp4',
                shell=True)

print("Cleaning up...")
dest_list = os.listdir( args.dest )
for item in dest_list:
    if item.endswith(".png"):
        os.remove( os.path.join( args.dest, item ) )

print("Done")



