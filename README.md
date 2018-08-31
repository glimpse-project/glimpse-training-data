# Glimpse Training Data

*Note: we recommend passing --depth=1 while cloning considering the size of the
tracked files*

The `mocap/` directory  includes compressed archives of the CMU motion capture
data we use for rendering our training images.

The `blender/` directory includes a glimpse-training.zip file containing a
glimpse-training.blend file for use in conjunction with
`blender/addon/glimpse_data_generator` and `glimpse/glimpse-cli.py` that helps
us import the CMU mocap animations into Blender and render our training images.

After cloning this repository you need to run `./unpack.sh` to decompress the
CMU mocap archives and `blender/glimpse-training.blend`

After cloning this repository you need to follow the instructions below to
install and enable all the required Blender addons.

Before trying to render anything you also will need to pre-load some mocap
animations into glimpse-training.blend.

*Note: We don't store a .blend file with preloaded animations in this repository
because the file size can balloon from to around 2GB.*

# TL;DR

Fetch and setup:
```
git clone --depth=1 https://github.com/glimpse-project/glimpse-training-data
cd glimpse-training-data
./unpack.sh
cd blender
./install-addons.sh
```
Pre-load mocap data:
```
./blender/glimpse-cli.py \
    --start 20 \
    --end 25 \
    --preload \
    .
```
Render training data:
```
./blender/glimpse-cli.py \
    --start 20 \
    --end 25 \
    --width 320 \
    --height 240  \
    --vertical-fov 43.921572 \
    --min-camera-height 1.1 \
    --max-camera-height 1.4 \
    --min-camera-distance 2 \
    --max-camera-distance 2.5 \
    --max-angle-left 30 \
    --max-angle-right 0 \
    --dest ./renders \
    --name "test-render" \
    .
```

Pre-process images:
```
image-pre-processor \
    /path/to/glimpse-training-data/renders/test-render \
    /path/to/glimpse-training-data/pre-processed/test-render \
    /path/to/glimpse-training-data/label-maps/2018-06-render-to-2018-08-rdt-map.json \
    -c /path/to/glimpse-training-data/pre-processor-configs/iphone-x-config.json
```

Create index file for a test set
```
indexer.py \
    -i test 20000 \
    /path/to/glimpse-training-data/pre-processed/test-render
```

Create index file for each tree to train (excluding test set images)
```
indexer.py \
    -e test \
    -i tree0 300000 \
    -i tree1 300000 \
    -i tree2 300000 \
    /path/to/glimpse-training-data/pre-processed/test-render
```

Train each decision tree:
```
train_rdt /path/to/glimpse-training-data/pre-processed/test-render tree0 tree0.json
train_rdt /path/to/glimpse-training-data/pre-processed/test-render tree1 tree1.json
train_rdt /path/to/glimpse-training-data/pre-processed/test-render tree2 tree2.json
```

Train joint inference parameters:
```
train_joint_params /path/to/glimpse-training-data/pre-processed/test-render \
                   joint-param-training \
                   /path/to/glimpse-training-data/joint-maps/2018-06-joint-map.json \
                   output.jip -- tree0.json tree1.json tree2.json
```

Create binary-format decision trees for use at runtime:
```
json-to-rdt tree0.json tree0.rdt
json-to-rdt tree1.json tree1.rdt
json-to-rdt tree2.json tree2.rdt
```

# About the CMU Motion captures

This mocap data originally comes from CMU at http://mocap.cs.cmu.edu/

With the following permissive licensing terms:

```
This data is free for use in research projects.
You may include this data in commercially-sold products,
but you may not resell this data directly, even in converted form.
If you publish results obtained using this data, we would appreciate it
if you would send the citation to your published paper to jkh+mocap@cs.cmu.edu,
and also would add this text to your acknowledgments section:

  "The data used in this project was obtained from mocap.cs.cmu.edu.
  The database was created with funding from NSF EIA-0196217."
```

and this in their FAQ:

```
  Q. How can I use this data?
  A. The motion capture data may be copied, modified, or redistributed without
     permission.
```

The files we're using contain a conversion of the original data to BVH format,
which were published at cgspeed.com and now archived here:
https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/cmu-bvh-conversion

Considering that the cgspeed files are hosted on mediaflare.com which requires
interaction with a browser to download, we commit the files to our repository
for convenience.

For reference, we also found that these files have been republished under
http://codewelt.com/cmumocap where it's also possible to download these files
non-interactively, but for downloading to Travis for CI (cached) we have better
bandwidth cloning from github.


# Setting up Blender automatically

After cloning this repository, then assuming you have Blender (2.79) installed
you can install and enable all of the required addons like so:

```
cd blender/
./install-addons.sh
```

This will download and install the Makehuman BlenderTools addons (MakeTarget,
MakeWalk and MakeClothes) and update your Blender user preferences to add
glimpse-training-data/blender as a scripts directory so that Blender can find
the glimpse_data_generator addon.


# Setting up Blender manually

Firstly, follow the instructions here to install the Makehuman BlenderTools addons:
http://www.makehumancommunity.org/wiki/Documentation:Getting_and_installing_BlenderTools

Within Blender's User Preferences -> File tab:

Point the 'Scripts:' entry to the glimpse-training-data/blender/ directory

Press 'Save User Settings' and quit and reopen Blender

Under User Preferences -> Addons now enable these Addons:

* Make Walk
* Make Clothes
* Make Target
* Glimpse Rig Paint
* Glimpse Training Data Generator


# Pre-load CMU mocap animations in glimpse-training.blend

First, you need to have unpacked the mocap data via `./unpack.sh` and installed the
required Blender addons as described above.

You can get some help with running glimpse-cli.py by running like:

```
./blender/glimpse-cli.py --help
```

Here it's good to understand that `mocap/index.json` is an index of all the
different `.bvh` mocap files under the `mocap/` directory. The file lets us
blacklist certain files or specify overrides for how they should be handled when
rendering.

Before the `glimpse_data_generator` addon can be used to render, it requires
there to be some number of pre-loaded motion capture animations. We pre-load
these because it's quite a slow process to retarget them to the animation rigs
within glimpse-training-data.blend and we don't want to be repeating this
work for each run of rendering.

The units used for specifying what to pre-load are the sequential indices for
mocap files tracked within `mocap/index.json`, whereby it's possible to
pre-load a subset of the data by specifying a `--start` and `--end` index.
*(Blacklisted files within the given range will be automatically skipped over)*

A small number of motion capture files can be pre-loaded as follows:

```
./blender/glimpse-cli.py \
    --start 20 \
    --end 25 \
    --preload \
    .
```

# Render Training Images

*Note: before rendering you must pre-load some motion capture data as described
above*

The units used for specifying what to render are the sequential indices for
mocap files tracked within `mocap/index.json`, the same as used for pre-loading
data.

A small number of images can be rendered as follows:

```
./blender/glimpse-cli.py \
    --start 20 \
    --end 25 \
    --width 320 \
    --height 240  \
    --vertical-fov 43.921572 \
    --min-camera-height 1.1 \
    --max-camera-height 1.4 \
    --min-camera-distance 2 \
    --max-camera-distance 2.5 \
    --max-angle-left 30 \
    --max-angle-right 0 \
    --dest ./renders \
    --name "test-render" \
    .
```


# Pre-process rendered images

At this point it's assumed that you've used `glimpse-cli.py` to render some
training images, as described above.

Before starting training we process the images rendered by Blender so we can
increase the amount of training data we have by e.g. mirroring images and we
add noise to make the data more representative of images captured by a
camera instead of being rendered.

Since different cameras exhibit different kinds of sensor noise we have some
per-device config files under `pre-processor-configs/`. (See
`pre-processor-configs/README.md` for more details)

The pre-processor is responsible for mapping the greyscale values found in
rendered image for body part labels into a tightly packed sequence of greyscale
values that will serve as label indices while training. The greyscale values in
rendered images aren't necessarily tightly packed but in pre-processed images
they are. It's also possible we don't want to learn about all the rendered
labels so the pre-processor accepts a "label map" configuration (found under
the `label-maps/` directory). (See `label-maps/README.md` for more details)

If we have rendered data via `glimpse-cli.py` under
`/path/to/glimpse-training-data/renders/test-render` then these images
can be processed as follows:

```
image-pre-processor \
    /path/to/glimpse-training-data/renders/test-render \
    /path/to/glimpse-training-data/pre-processed/test-render \
    /path/to/glimpse-training-data/label-maps/2018-06-render-to-2018-08-rdt-map.json \
    -c /path/to/glimpse-training-data/pre-processor-configs/iphone-x-config.json
```

# Index frames to train with

For specifying which frames to train with, an index should be created with the
`/path/to/glimpse/src/indexer.py` script.

This script builds an index of all available rendered frames in a given
directory and can then split that into multiple sub sets with no overlap. For
example you could index three sets of 300k images out of a larger set of 1
million images for training three separate decision trees.

For example to create a 'test' index of 10000 images you could run:
```
indexer.py -i test 10000 /path/to/glimpse-training-data/pre-processed/test-render
```
(*Note: this will also automatically create an `index.full` file*)

and then create three tree index files (sampled with replacement, but excluding
the test set images):
```
indexer.py \
    -e test \
    -i tree0 100000 \
    -i tree1 100000 \
    -i tree2 100000 \
    /path/to/glimpse-training-data/pre-processed/test-render
```
*Note: there may be overlapping frames listed in tree0, tree1 and tree1 but
none of them will contain test-set frames. See --help for details.*


# Training a decision tree

Run the tool `train_rdt` to train a tree. Running it with no parameters, or
with the `-h/--help` parameter will print usage details, with details about the
default parameters.

For example, if you have an index.tree0 file at the top of your training data
you can train a decision tree like:

```
train_rdt /path/to/glimpse-training-data/pre-processed/test-render tree0 tree0.json
```


# Creating a joint map

To know which bones from the training data are of interest, and what body
labels they are associated with, these tools need a joint-map file.  This is a
human-readable JSON text file that describes what bones map to which labels.

It's an array of objects where each object specifies a joint, an array of
label indices and an array of other joints it connects to. A joint name is
comprised of a bone name follow by `.head` or `.tail` to specify which end of
the bone. For example:

```
[
    {
        "joint": "head.tail",
        "labels": [ 2, 3 ],
        "connections": [ "neck_01.head" ]
    },
    {
        "joint": "neck_01.head",
        "labels": [ 4 ],
        "connections": [ "upperarm_l.head" ]
    },
    {
        "joint": "upperarm_l.head",
        "labels": [ 7 ],
        "connections": []
    },
    ...
]
```

Typically the latest `joint-maps/YEAR-MONTH-joint-map.json` file should be used.


# Training joint inference parameters

Run the tool `train_joint_params` to train joint parameters. Running it with no
parameters, or with the `-h/--help` parameter will print usage details, with
details about the default parameters.

Note that this tool doesn't currently scale to handling as many images as
the decision tree training tool so it's recommended to create a smaller
dedicated index for training joint params.

For example, if you have an `index.joint-param-training` file then to train
joint parameters from a decision forest of three trees named `tree0.json`,
`tree1.json` and `tree2.json` you could run:

```
train_joint_params /path/to/glimpse-training-data/pre-processed/test-render \
                   joint-param-training \
                   /path/to/glimpse-training-data/joint-maps/2018-06-joint-map.json \
                   output.jip -- tree0.json tree1.json tree2.json
```

_Note: the YEAR-MONTH prefix for the chosen joint-map should typically match
the -to-YEAR-MONTH-rdt-map.json suffix of the label map used when running
the pre-processor._


# Convert .json trees to .rdt for runtime usage

To allow faster loading of decision trees at runtime we have a simple binary
`.rdt` file format for trees.

For example, to create an `tree0.rdt` file from a `tree0.json` you can run:
```
json-to-rdt tree0.json tree0.rdt
```

*Note: `.rdt` files only include the information needed at runtime and so
training tools don't support loading these files.*

*Note: We don't aim to support forwards compatibility for `.rdt` besides having
a version check that lets us recognise incompatibility. Newer versions of
Glimpse may require you to recreate `.rdt` files.
