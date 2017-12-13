#!/bin/bash
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
#
# Downloads any third-party training data that we depend on, including CMU
# mocap recordings and Dlib's pre-trained face landmark model.
#


# This mocap data originally comes from CMU at http://mocap.cs.cmu.edu/
#
# With the following permissive licensing terms:
#
#   This data is free for use in research projects.
#   You may include this data in commercially-sold products,
#   but you may not resell this data directly, even in converted form.
#   If you publish results obtained using this data, we would appreciate it
#   if you would send the citation to your published paper to jkh+mocap@cs.cmu.edu,
#   and also would add this text to your acknowledgments section:
#
#    "The data used in this project was obtained from mocap.cs.cmu.edu.
#    The database was created with funding from NSF EIA-0196217."
# 
# and this in their FAQ:
#
#   Q. How can I use this data?
#   A. The motion capture data may be copied, modified, or redistributed without
#      permission. 
#
# The files we're downloading contain a conversion of the original data to
# BVH format, and originally published at cgspeed.com and now archived here:
# https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/cmu-bvh-conversion
#
# Since the files from cgspeed.com were originally hosted on mediaflare.com
# which requires browser interaction these files have since been republished
# under http://codewelt.com/cmumocap where it's now possible to download these
# files non-interactively with wget:


for i in 01-09 10-14 102-111 113-128 131-135 136-140 141-144 15-19 20-29 30-34 35-39 40-45 46-56 60-75 76-80 81-85 86-94
do
    file="cmuconvert-mb2-$i.zip"
    if ! test -f $file; then
        wget http://codewelt.com/dl/cmuconvert/$file
    fi
    dir=mocap/cmuconvert-mb2-$i
    if ! test -d $dir; then
        mkdir -p $dir
        unzip -d $dir $file
    fi
done


git clone --depth 1 https://github.com/davisking/dlib-models
