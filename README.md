Large resources used for training the Glimpse motion capture system

After cloning this repository (we recommend passing --depth=1 while cloning
considering the ~80MB size of our .blend file) you also need to run ./fetch.sh
to download the CMU mocap data that we use.


# Blender-based rendering pipeline

The blender/ directory includes a glimpse-training.blend file for use in
conjunction with a glimpse_data_generator addon that helps us import the
CMU mocap animations and render our training images.


# CMU Motion captures

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

The files we're downloading contain a conversion of the original data to
BVH format, which were published at cgspeed.com and now archived here:
https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/cmu-bvh-conversion

Since the files from cgspeed.com were originally hosted on mediaflare.com
which requires browser interaction these files have since been republished
under http://codewelt.com/cmumocap where it's now possible to download these
files non-interactively with wget

