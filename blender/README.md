# How to add a new makehuman model to glimpse-training.blend

## Within makehuman:
- Use sliders to define a body type
- Under Pose/Animate->Skeleton select the 'Game engine' rig
- Under Pose/Animate->Pose select Tpose
- Under Files->Export:
    - select 'Mesh Format' = mh2 (need to install plugin for this first)
    - select 'Scale units' = meter
- Choose export filename and export
    - use a name like 'Man3' or 'Woman3' just for consistency with the
    current naming.
- Also save a .mhm file in case it's useful for future reference
Notes:
- The model must use the default mesh topology since we rely on this in
  Blender for transfering vertex colors according to the topology


## Within Blender:
(assuming you've added the mh2 import and the MakeWalk addon and the Glimpse
 paint rig addon)
- Switch to an empty layer
- Import .mh2, select the file exported from makehuman
    - Before import: check 'Override Exported Data' in left 'Import MHX2' panel
        - check 'Helper Geometry' needed for fitting clothes to the mesh
- Select the body mesh in object mode
- Use the left hand 'MHX2 Runtime' panel and select 'Add simple materials'
    (This will ensure that the clothing related parts will be transparent and
    invisible to rendering)
- Use the right hand 'Make Clothes' panel to set the 'Mesh Type' to 'Human'
    (press the 'Clothes' button to toggle)
- Go to Edit Mode and then to the far right Material properties tab
- Select the Defaultskin material
- Make sure no vertices are selected in Edit Mode and press the 'Select' by
    active material slot button in the properties tab. This should just select
    the body without any helper geometry. This will also select a small cube
    around the root bone which you should unselect (press 'c' for the circle
    select tool and press shift which brushing over the cube)
- Shift-D to duplicate these vertices and press Esc without moving them
- Press 'p' and separate these vertices by Selection
- Delete associated materials then assign the JointLabelsMaterial
- Rename the objects, mesh and pose like 'Woman1PoseObject'. E.g. for a 'Woman1'
  model there would be these named objects:
        Woman1PoseObject
        Woman1Pose
        Woman1BodyMeshObject
        Woman1BodyMesh
        Woman1BodyHelperMeshObject
        Woman1BodyHelperMesh
- In the Outliner click the camera icon next to the *BodyHelperMeshObject and
  the other 'High-poly' mesh so they're not included in renders
- Select the separated BodyMeshObject
- Go to the modifiers panel and add a 'DataTransfer' modifer
    - Set 'Source Object' to 'BaseBodyMeshObject'
    - Check 'Face Corner Data', choose 'Topology' from the drop down,
    select 'VCol' and press 'Generate Data Layers'
- Select the new PoseObject, press _Space_ and search for the 'Add Clothes Library To Body`
  operator to add all known clothes to the new model. Remove any clothing items
  that have a bad or unlikely fit.


# Adding new reference clothes

- Select the BaseBodyHelperMeshObject in ObjectMode
- From the Make Clothes tools panel press 'Test Clothes' and select the clothing
- Select the new clothing object and the BasePoseObject and run the 'Rig Paint Operator'
- Make sure the BasePoseObject is in the 'Reset Position' (so the pose isn't affecting the mesh)
- Select just the new clothing object
- Add a DataTransfer modifier
    - Set 'Source Object' to 'BaseBodyMeshObject'
    - Check 'Vertex Data', select 'Nearest Vertex', select 'Vertex Group(s)' and press 'Generate Data Layers'
-  Apply the modifier
- Shift select the 'BasePoseObject' in addition to the clothing object and press
  Ctrl-P to re-parent the clothing under the base pose, selecting the
  'With Empty Groups' option
- Rename the object to something like 'clothing_item_reference'
- assign the JointLabelsMaterial
- Finally with just the clothing object selected press 'm' and move it to the
  top-right clothing layer
