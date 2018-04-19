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
    --dest ./render \
    --name "test-render" \
    .
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
    --dest ./render \
    --name "test-render" \
    .
```

