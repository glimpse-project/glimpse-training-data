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
# Downloads any third-party training data that we depend on.
#

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

