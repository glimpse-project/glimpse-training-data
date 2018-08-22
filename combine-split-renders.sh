#!/bin/bash

# glimpse-render.py creates multiple directories like renders/$NAME-part-$i
# but for pre-processing we want a single combined directory...

if test $# != 3; then
	echo "Usage: $0 RENDERS_TOP_DIR NAME N"
	exit 1
fi

RENDERS_TOP_DIR=$1
NAME=$2
N=$3

cd $RENDERS_TOP_DIR

mkdir -p $NAME/labels
mkdir -p $NAME/depth
cp $NAME-part-0/meta.json $NAME

for i in `seq 0 $(($N - 1))`
do
	echo "cp -a $NAME-part-$i/labels/* $NAME/labels ..."
	cp -a $NAME-part-$i/labels/* $NAME/labels
	echo "cp -a $NAME-part-$i/depth/* $NAME/depth ..."
	cp -a $NAME-part-$i/depth/* $NAME/depth
done

