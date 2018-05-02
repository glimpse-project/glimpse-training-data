#!/bin/bash

# render.sh creates multiple directories like renders/render-$NAME-$i
# but for pre-processing we want a single combined directory...

if test $# != 2; then
	echo "Usage: $0 NAME N"
	exit 1
fi

NAME=$1
N=$2

cd renders

mkdir -p $NAME/labels
mkdir -p $NAME/depth
cp render-$NAME-0/meta.json $NAME

for i in `seq 0 $(($N - 1))`
do
	echo "cp -a render-$NAME-$i/labels/* $NAME/labels ..."
	cp -a render-$NAME-$i/labels/* $NAME/labels
	echo "cp -a render-$NAME-$i/depth/* $NAME/depth ..."
	cp -a render-$NAME-$i/depth/* $NAME/depth
done

