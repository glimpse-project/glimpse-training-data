#!/bin/bash
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

# A helper script for running multiple non-interactive instances of Blender to
# render a large set of training data
#
# It assumes that you have already used glimpse-cli.py to link all the CMU
# mocap data into glimpse-training.blend
#
# TODO: rewrite in python with argparse and e.g. a --dry-run option
#

if test $# != 1; then
    echo "Usage ./render.sh NAME"
    exit 1
fi

NAME=$1

# Number of instances of Blender
N=10

# Range of CPU mocap files to render
START=0
END=2000

# Allow camera to move left/right by += VIEW_RANGE degrees from front-facing
# view
VIEW_RANGE=10

# Used to scale down the size of the final data set by skipping a (randomized)
# percentage of frames
SKIP_PERCENTAGE=90

# Uncomment for quick test render
#N=5
#START=20
#END=25

RANGE=$(($END-$START))
STEP=$(($RANGE/$N))
echo "STEP=$STEP"

if test $(($N*$STEP)) -ne $RANGE; then
        echo "Instance count of $N doesn't factor into RANGE of $RANGE"
        exit 1
fi

for i in `seq 0 $(($N-1))`
do
        S=$(($START+$i*$STEP))
        E=$(($START+$i*$STEP+$STEP))

        echo "./blender/glimpse-cli.py --start $S --end $E --skip-percentage $SKIP_PERCENTAGE --max-angle $VIEW_RANGE --name "render-$NAME-$i" --dest ./renders ."
        ./blender/glimpse-cli.py --start $S --end $E --skip-percentage $SKIP_PERCENTAGE --max-angle $VIEW_RANGE --name "render-$NAME-$i" --dest ./renders . 2>&1 1> render-$NAME-$i.log &
done

