# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

bl_info = {
    "name": "Glimpse Training Data Generator",
    "description": "Tool to help generate skeleton tracking training data",
    "author": "Robert Bragg",
    "version": (0, 1, 1),
    "blender": (2, 78, 0),
    #"location": "",
    "warning": "",
    "support": 'COMMUNITY',
    "wiki_url": "",
    "category": "Mesh"}

# Copyright (C) 2017-2018: Glimp IP Ltd <robert@impossible.com>

import math
import mathutils
import os
import json
import ntpath
import numpy
import time
import datetime
import random

import bpy
from bpy.props import (
        CollectionProperty,
        StringProperty,
        BoolProperty,
        IntProperty,
        EnumProperty,
        FloatProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper_factory,
        axis_conversion,
        )

import bmesh


#all_bodies = [ 'Man0', 'Woman0', 'Man1', 'Woman1', 'Man2', 'Woman2' ]

# XXX: Woman1 black listed for now because the mocap doesn't make sense
# with the large hips and the hands often intersect the hips which will
# affect our labeling / training
all_bodies = [ 'Man0', 'Woman0', 'Man1', 'Man2', 'Woman2' ]

hat_choices = [ 'none', 'knitted_hat_01', 'newsboy_cap', 'patrol_cap' ]
hat_probabilities = [ 0.4, 0.2, 0.2, 0.2 ]

glasses_choices = [ 'none', 'glasses' ]
glasses_probabilities = [ 0.7, 0.3 ]

# XXX: start fleet uniform black listed for now because hands may intersect it too much
# resulting in labelling the hips as hands/wrists.
#top_choices = [ 'none', 'hooded_cardigan', 'star_fleet_uniform_female_gold_reference' ]
top_choices = [ 'none', 'hooded_cardigan' ]
top_probabilities = [ 0.8, 0.2 ]

trouser_choices = [ 'none', 'm_trousers_01' ]
trouser_probabilities = [ 0.5, 0.5 ]

shoe_choices = []
shoe_probabilities = []

hbars = [u"\u0020", u"\u258f", u"\u258e", u"\u258d", u"\u258b", u"\u258a", u"\u2589"]
max_bar_width = 10

# outputs the percentage bar (made from hbars) calculated from provided values
def get_percentage_bar(value, max_entries):
    bar_len = int(max_bar_width * 6 * value / max_entries)
    bar_output = ""
    for i in range(0, max_bar_width):
        if bar_len > 6:
            bar_output += hbars[6]
            bar_len -= 6
        else:
            bar_output += hbars[bar_len]
            bar_len = 0
    return bar_output


def add_clothing(op, context, clothing_name):

    if clothing_name + "_reference" not in bpy.data.objects:
        return

    mhclo_relpath = os.path.join(clothing_name, clothing_name + ".mhclo")
    ref_clothing_obj = bpy.data.objects[clothing_name + "_reference"]

    # XXX: we don't reference context.active_object because for some reason
    # (bug or important misunderstanding about blender's state management)
    # then changes to context.scene.objects.active aren't immediately
    # reflected in context.active_object (and not a question of calling
    # scene.update() either)
    helper_mesh = context.scene.objects.active
    human_mesh_name = helper_mesh.name[:-len("BodyHelperMeshObject")]

    mhclo_file = bpy.path.abspath(context.scene.GlimpseClothesRoot + mhclo_relpath)
    bpy.ops.mhclo.test_clothes(filepath = mhclo_file)

    clothing = context.selected_objects[0]
    context.scene.objects.active = clothing
    clothing.layers = helper_mesh.layers

    clothing.data.materials.append(bpy.data.materials.get("JointLabelsMaterial"))

    bpy.ops.object.modifier_add(type='DATA_TRANSFER')
    clothing.modifiers['DataTransfer'].object = ref_clothing_obj

    clothing.modifiers['DataTransfer'].use_vert_data = True
    clothing.modifiers['DataTransfer'].data_types_verts = {'VGROUP_WEIGHTS'}
    clothing.modifiers['DataTransfer'].vert_mapping = 'TOPOLOGY'

    clothing.modifiers['DataTransfer'].use_loop_data = True
    clothing.modifiers['DataTransfer'].data_types_loops = {'VCOL'}
    clothing.modifiers['DataTransfer'].loop_mapping = 'TOPOLOGY'

    context.scene.objects.active = clothing
    bpy.ops.object.datalayout_transfer(modifier="DataTransfer")
    bpy.ops.object.modifier_apply(modifier='DataTransfer')

    for ob in bpy.context.selected_objects:
        ob.select = False

    clothing.select = True
    bpy.data.objects[human_mesh_name + 'PoseObject'].select = True
    context.scene.objects.active = bpy.data.objects[human_mesh_name + 'PoseObject']

    bpy.ops.object.parent_set(type='ARMATURE_NAME')
    context.scene.objects.active = clothing


class AddClothingOperator(bpy.types.Operator):
    """Adds clothing to the active body"""

    bl_idname = "glimpse.add_clothing"
    bl_label = "Add Clothing"

    clothing_name = StringProperty(
            name="Clothing Name",
            description="Name of clothing register_module"
            )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and "BodyHelperMeshObject" in context.active_object.name

    def execute(self, context):
        if self.clothing_name + "_reference" not in bpy.data.objects:
            self.report({'ERROR'}, "didn't find reference clothing object " + self.clothing_name + "_reference")
            return {'FINISHED'}
        add_clothing(self, context, self.clothing_name)

        return {'FINISHED'}


# The data generator operator expects that each body has previously had all
# possible clothing items added to the body. This avoids the cost of loading
# the clothing at runtime and also clothing that's not applicable to a
# particular body can be excluded and the generator will handle that gracefully
class AddClothingLibraryOperator(bpy.types.Operator):
    """Adds the full library of known clothing items to active body"""

    bl_idname = "glimpse.add_clothes_library"
    bl_label = "Add Clothes Library To Body"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object is not None and "PoseObject" in context.active_object.name

    def execute(self, context):

        all_clothes = []
        all_clothes.extend(hat_choices)
        all_clothes.extend(glasses_choices)
        all_clothes.extend(top_choices)
        all_clothes.extend(trouser_choices)
        all_clothes.extend(shoe_choices)

        # The clothing sub-lists have 'none' entries we want to ignore here
        all_clothes = [ clothing for clothing in all_clothes if clothing != 'none' ]

        body = context.active_object.name[:-len("PoseObject")]

        pose_obj = context.active_object

        pose_obj = bpy.data.objects[body + 'PoseObject']
        if pose_obj == None:
            self.report({'ERROR'}, "didn't find pose mesh for " + body)
            return {'FINISHED'}
        helper_obj = bpy.data.objects[body + 'BodyHelperMeshObject']
        if helper_obj == None:
            self.report({'ERROR'}, "didn't find helper mesh for " + body)
            return {'FINISHED'}

        for child in pose_obj.children:
            self.report({'INFO'}, body + " child:" + child.name)

            if body + "Clothes:" in child.name:
                self.report({'INFO'}, "removing " + child.name + " from " + body)
                context.scene.objects.active = bpy.data.objects[child.name]
                bpy.data.objects[child.name].select = True
                bpy.ops.object.delete()

        for clothing in all_clothes:
            for ob in bpy.context.selected_objects:
                ob.select = False
            context.scene.objects.active = helper_obj
            add_clothing(self, context, clothing)

            for child in pose_obj.children:
                if child.name == clothing:
                    child.name = body + "Clothes:" + clothing
                    child.hide = True
                    break

        return {'FINISHED'}


class GeneratorInfoOperator(bpy.types.Operator):
    """Print summary information about our data generation state"""

    bl_idname = "glimpse.generator_info"
    bl_label = "Print Glimpse Generator Info"

    def execute(self, context):

        print("Number of indexed motion capture files = %d" % len(bvh_index))

        print("Pre-loaded actions:");
        for action in bpy.data.actions:
            print("> %s" % action.name)

        start = bpy.context.scene.GlimpseBvhGenFrom
        end = bpy.context.scene.GlimpseBvhGenTo
        print("start =  %d end = %d" % (start, end))

        for i in range(start, end):
            bvh = bvh_index[i]
            bvh_name = bvh['name']

            if 'Base' + bvh_name in bpy.data.actions:
                action = bpy.data.actions['Base' + bvh_name]
                if action.library == None:
                    print(" > %s: Cached" % bvh_name)
                else:
                    print(" > %s: Linked from %s" % (bvh_name, action.library.filepath))
            else:
                print(" > %s: Uncached" % bvh_name)


        return {'FINISHED'}


class GeneratorPurgeActionsOperator(bpy.types.Operator):
    """Purge preloaded actions"""

    bl_idname = "glimpse.purge_mocap_actions"
    bl_label = "Purge MoCap Actions"

    def execute(self, context):

        print("Number of indexed motion capture files = %d" % len(bvh_index))

        start = bpy.context.scene.GlimpseBvhGenFrom
        end = bpy.context.scene.GlimpseBvhGenTo

        for i in range(start, end):
            bvh = bvh_index[i]
            bvh_name = bvh['name']
            action_name = 'Base%s' % bvh_name

            if action_name in bpy.data.actions:
                action = bpy.data.actions[action_name]
                action.use_fake_user = False
                print(" > Purging %s" % bvh_name)

        return {'FINISHED'}


class GeneratorPreLoadOperator(bpy.types.Operator):
    """Pre-loads the mocap files as actions before a render run"""

    bl_idname = "glimpse.generator_preload"
    bl_label = "Preload MoCap Files"

    def execute(self, context):

        print("Number of indexed motion capture files = %d" % len(bvh_index))

        start = bpy.context.scene.GlimpseBvhGenFrom
        end = bpy.context.scene.GlimpseBvhGenTo
        print("start =  %d end = %d" % (start, end))

        for i in range(start, end):
            bvh = bvh_index[i]
            bvh_name = bvh['name']

            if 'Base' + bvh_name in bpy.data.actions:
                print(" > %s: Cached" % bvh_name)
            else:
                print(" > %s: Loading" % bvh_name)

                # Note we always load the mocap animations with the base the
                # base mesh, and then associate the animation_data.action with
                # all the other armatures we have
                base_pose_obj = bpy.data.objects['BasePoseObject']
                bpy.context.scene.objects.active = base_pose_obj

                load_bvh_file(bvh)

        return {'FINISHED'}


class GeneratorLinkMocapsOperator(bpy.types.Operator):
    """Links the mocap actions from an external .blend file"""

    bl_idname = "glimpse.generator_link"
    bl_label = "Link MoCap Files"

    def execute(self, context):

        filepath = bpy.context.scene.GlimpseMocapLibrary
        print("Linking mocap files from: " + filepath)
        print("Number of indexed motion capture files = %d" % len(bvh_index))

        start = bpy.context.scene.GlimpseBvhGenFrom
        end = bpy.context.scene.GlimpseBvhGenTo
        print("start =  %d end = %d" % (start, end))

        with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
            names = []
            for i in range(start, end):
                bvh = bvh_index[i]
                bvh_name = bvh['name']

                if 'Base' + bvh_name in bpy.data.actions:
                    action = bpy.data.actions['Base' + bvh_name]
                    if action.library == None:
                        print(" > %s: Cached" % bvh_name)
                    else:
                        print(" > %s: Already linked from %s" % (bvh_name, action.library.filepath))
                else:
                    print(" > %s: Linking" % bvh_name)
                    names += [ 'Base' + bvh_name ]

            data_to.actions = names

        return {'FINISHED'}


def mkdir_p(path):
    os.makedirs(path, exist_ok=True)


class GeneratorOperator(bpy.types.Operator):
    """Generates Glimpse training data"""

    bl_idname = "glimpse.generate_data"
    bl_label = "Generate Glimpse training data"

    @classmethod
    def poll(cls, context):
        return len(bvh_index) > 0

    def execute(self, context):

        top_meta = {}
        meta = {}
        frame_count = 0
        frame_skip_count = 0

        # stats
        clothes_stats = {}
        body_stats = {}

        dt = datetime.datetime.today()
        date_str = "%04u-%02u-%02u-%02u-%02u-%02u" % (dt.year,
                dt.month, dt.day, dt.hour, dt.minute, dt.second)

        if bpy.context.scene.GlimpseGenDir and bpy.context.scene.GlimpseGenDir != "":
            gen_dir = bpy.context.scene.GlimpseGenDir
        else:
            gen_dir = date_str

        if bpy.context.scene.GlimpseDataRoot and bpy.context.scene.GlimpseDataRoot != "":
            abs_gen_dir = bpy.path.abspath(os.path.join(bpy.context.scene.GlimpseDataRoot, gen_dir))
        else:
            abs_gen_dir =os.path.join(os.getcwd(), gen_dir)

        print("Generate Destination: " + abs_gen_dir)
        if bpy.context.scene.GlimpseDryRun == False:
            mkdir_p(abs_gen_dir)

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for ob in bpy.context.selected_objects:
            ob.select = False
        bpy.context.scene.objects.active = bpy.data.objects['BasePoseObject']

        meta['date'] = date_str

        render_layers = []
        for i in range(0, 20):
            render_layers.append(False)
        render_layers[0] = True

        # Do all our rendering from layer zero, pulling in other objects
        # as needed
        context.scene.layers = render_layers

        for body in all_bodies:
            pose_obj = bpy.data.objects[body + 'PoseObject']
            for child in pose_obj.children:
                child.layers = pose_obj.layers

        camera = bpy.data.objects['Camera']

        z_forward = mathutils.Vector((0, 0, 1))
        zero_vec = mathutils.Vector((0, 0, 0))

        bpy.context.scene.render.resolution_x = bpy.context.scene.GlimpseRenderWidth
        bpy.context.scene.render.resolution_y = bpy.context.scene.GlimpseRenderHeight
        bpy.data.cameras['Camera'].angle = math.radians(bpy.context.scene.GlimpseVerticalFOV)

        camera_meta = {}
        camera_meta['width'] = bpy.context.scene.render.resolution_x
        camera_meta['height'] = bpy.context.scene.render.resolution_y
        camera_meta['vertical_fov'] = math.degrees(bpy.data.cameras['Camera'].angle)
        is_camera_fixed = bpy.context.scene.GlimpseFixedCamera
        is_camera_debug = bpy.context.scene.GlimpseDebugCamera
        camera_meta['is_camera_fixed'] = is_camera_fixed
        is_camera_smooth_movement = bpy.context.scene.GlimpseSmoothCameraMovement
        camera_meta['is_camera_smooth_movement'] = is_camera_smooth_movement
        frequency = bpy.context.scene.GlimpseSmoothCameraFrequency
        camera_meta['smooth_camera_frequency'] = frequency

        meta['camera'] = camera_meta
        top_meta['camera'] = camera_meta
        top_meta['n_labels'] = 34
        
        if(is_camera_fixed):
            min_viewing_angle = bpy.context.scene.GlimpseMinViewingAngle
            top_meta['min_viewing_angle'] = min_viewing_angle
            min_distance_mm = bpy.context.scene.GlimpseMinCameraDistanceMM
            top_meta['min_camera_distance'] = min_distance_mm
            min_height_mm = bpy.context.scene.GlimpseMinCameraHeightMM
            top_meta['min_camera_height'] = min_height_mm
        else:
            min_viewing_angle = bpy.context.scene.GlimpseMinViewingAngle
            max_viewing_angle = bpy.context.scene.GlimpseMaxViewingAngle
            top_meta['min_viewing_angle'] = min_viewing_angle
            top_meta['max_viewing_angle'] = max_viewing_angle
            min_distance_mm = bpy.context.scene.GlimpseMinCameraDistanceMM
            max_distance_mm = bpy.context.scene.GlimpseMaxCameraDistanceMM
            top_meta['min_camera_distance'] = min_distance_mm
            top_meta['max_camera_distance'] = max_distance_mm
            min_height_mm = bpy.context.scene.GlimpseMinCameraHeightMM
            max_height_mm = bpy.context.scene.GlimpseMaxCameraHeightMM
            top_meta['min_camera_height'] = min_height_mm
            top_meta['max_camera_height'] = max_height_mm
        
        tags_skip = bpy.context.scene.GlimpseBvhTagsSkip.split("#")
        tags_skip.pop()
        tags_skipped = {}
        if tags_skip != 'none':
            for skip_tag in tags_skip:
                tag_data = skip_tag.split("=") 
                tags_skipped[tag_data[0]] = tag_data[1]
        
        top_meta_filename = os.path.join(abs_gen_dir, 'meta.json')

        if bpy.context.scene.GlimpseDryRun == False:
            with open(top_meta_filename, 'w') as fp:
                json.dump(top_meta, fp, indent=2)

        # Nested function for sake of improving cProfile data
        def render_bvh_index(idx):
            bvh = bvh_index[idx] 

            bvh_name = bvh['name']

            if bvh['blacklist']:
                self.report({'INFO'}, "skipping blacklisted")
                return 
            
            if bvh['tags'] != 'unknown':    
                tags_blacklist = bpy.context.scene.GlimpseBvhTagsBlacklist
                tags_blacklist = tags_blacklist.split(",")            
                
                for tag in tags_blacklist:
                    if tag in bvh['tags']:
                        print(bvh_name + " blacklisted - skipping")
                        self.report({'INFO'}, "skipping blacklisted tags")
                        return

                tags_whitelist = bpy.context.scene.GlimpseBvhTagsWhitelist
                if tags_whitelist != "all":
                    tags_whitelist = tags_whitelist.split(",")
                    for tag in tags_whitelist:
                        if tag not in bvh['tags']:
                            print(bvh_name + " not whitelisted - skipping")
                            self.report({'INFO'}, "not whitelisted - skipping")  
                            return

            print("> Rendering " + bvh_name)
    
            numpy.random.seed(0)
            random.seed(0)

            bpy.context.scene.frame_start = bvh['start']
            bpy.context.scene.frame_end = bvh['end']

            bvh_fps = bvh['fps']

            action_name = "Base" + bvh_name
            if action_name not in bpy.data.actions:
                print("WARNING: Skipping %s (not preloaded)" % bvh_name) 
                return
    
            numpy.random.seed(0)
            random.seed(0)
           
            print("Setting %s action on all body meshes" % action_name)
            assign_body_poses(action_name)

            meta['bvh'] = bvh_name

            # Nested function for sake of improving cProfile data
            def render_body(body):

                def hide_body_clothes(body):
                    pose_obj  = bpy.data.objects[body + "PoseObject"]
                    for child in pose_obj.children:
                        if body + "Clothes:" in child.name:
                            child.hide = True
                            child.layers = child.parent.layers

                # Make sure the clothes defined in meta are visible on the render layer
                def show_body_clothes_from_meta(body):
                    pose_obj  = bpy.data.objects[body + "PoseObject"]
                    if 'clothes' in meta:
                        for key in meta['clothes']:
                            for child in pose_obj.children:
                                if body + "Clothes:" + meta['clothes'][key] in child.name:
                                   child.hide = False
                                   child.layers[0] = True

                # Make sure no other bodies are visible on the render layer
                def hide_bodies_from_render():
                    for _body in all_bodies:
                        mesh_obj = bpy.data.objects[_body + "BodyMeshObject"]
                        mesh_obj.layers[0] = False
                        hide_body_clothes(_body)
                        bpy.data.armatures[_body + 'Pose'].pose_position = 'REST'
                
                #if body in body_stats:
                #    clothes_stats[meta['clothes'][key]] += 1
                #else: 
                #    clothes_stats[meta['clothes'][key]] = 1
                
                dist_mm = 0
                view_angle = 0
                height_mm = 0
                target_x_mm = 0
                target_y_mm = 0
                target_z_mm = 0
                camera_location = mathutils.Vector((0,0,0))
                target = mathutils.Vector((0,0,0))
                is_camera_pointing = False

                # random seed when smooth_camera_movement is true
                height_seed = 1

                print("> Rendering with " + body)

                meta['body'] = body
                
                hide_bodies_from_render()

                body_pose = bpy.data.objects[body + "PoseObject"]
                body_obj = bpy.data.objects[body + "BodyMeshObject"]
                body_obj.layers[0] = True
                bpy.data.armatures[body + 'Pose'].pose_position = 'POSE'

                if is_camera_debug:
                    hide_bodies_from_render()

                # Hit some errors with the range bounds not being integer and I
                # guess that comes from the json library loading our mocap
                # index may make some numeric fields float so bvh['start'] or
                # bvh['end'] might be float
                for frame in range(int(bvh['start']), int(bvh['end'])):
                    
                    nonlocal frame_skip_count

                    if random.randrange(0, 100) < bpy.context.scene.GlimpseSkipPercentage:
                        frame_skip_count += 1
                        print("> Skipping (randomized)" + bvh_name + " frame " + str(frame))
                        continue
                    
                    skip = False
                    tag_name = ""
                    for skip_tag in tags_skipped:
                        if skip_tag in bvh['tags'] and random.randrange(0, 100) < int(tags_skipped[skip_tag]):
                            skip = True
                            tag_name = skip_tag
                            break
                                        
                    if skip:
                        frame_skip_count += 1
                        print("> Skipping (randomized) by tag '" + tag_name + "' in " + bvh_name + " frame " + str(frame))
                        continue
                   
                    #foot_l = body_pose.pose.bones['foot_l'].tail.to_4d() 
                    #foot_r = camera.matrix_world.inverted() * body_pose.pose.bones['foot_r'].tail.to_4d()
                    #print("foot_l and foot_r %s | %s" %  (foot_l, foot_r) )
                    #skip_foot = False
                    #if foot_l.z > 0.2 or foot_r.z > 0.2:
                    #    skip_foot = True
                    
                    #if skip_foot:
                    #    print("> Skipping jumping legs")

                    nonlocal frame_count 
                    frame_count += 1
                    
                    if body in body_stats:
                        body_stats[body] += 1
                    else: 
                        body_stats[body] = 1

                    if bpy.context.scene.GlimpseDryRun:
                        print("> DRY RUN: Rendering " + bvh_name +
                              " frame " + str(frame) +
                              " with " + body)
                        continue

                    meta['frame'] = frame

                    bpy.context.scene.frame_set(frame) # XXX: this is very slow!
                    context.scene.update()

                    # turn off/on the background (floor and walls) depending
                    # on the set flag
                    added_background = bpy.context.scene.GlimpseAddedBackground;

                    if added_background:

                        print("> Generating background...")

                        floor_obj_name = "Background:Floor"
                        if floor_obj_name in bpy.data.objects:
                            floor_obj = bpy.data.objects[floor_obj_name]
                            floor_obj.hide = False
                            floor_obj.layers[0] = True

                        print("> Background:Floor added")
                        print("> Generating walls...")

                        wall_obj_name = "Background:Wall"
                        if wall_obj_name in bpy.data.objects:
                            wall_obj = bpy.data.objects[wall_obj_name]
                            for obj in wall_obj.children:
                                obj.hide = False
                                obj.layers[0] = True
                        else:
                            objects = bpy.data.objects
                            materials = bpy.data.materials
                            wall_width = 10
                            wall_height = 10
                            room_sides = 3
                            wall_part_size = mathutils.Vector((1.0, 0.5, 0.5))

                            # Create few materials to use for wall parts
                            for m in range(0, 5):
                                if ("BrickMat_%s" % m) not in materials:
                                    materials.new("BrickMat_%s" % m)
                                    materials[("BrickMat_%s" % m)].use_shadeless = True
                                    materials[("BrickMat_%s" % m)].diffuse_color = (random.uniform(0.0, 1.0),
                                                                                    random.uniform(0.0, 1.0),
                                                                                    random.uniform(0.0, 1.0))

                            # Create an empty mesh and the object.
                            wall_start_pos = body_pose.pose.bones['pelvis'].location + mathutils.Vector((-wall_width, wall_width / 3,0))
                            wall_empty = bpy.data.objects.new("Background:Wall", None )
                            bpy.context.scene.objects.link( wall_empty )
                            wall_empty.location = wall_start_pos

                            for k in range(0, room_sides):

                                wall_side = bpy.data.objects.new("Wall:Side_%s" % k, None )
                                bpy.context.scene.objects.link( wall_side )
                                wall_side.location = wall_start_pos

                                for i in range(0, wall_height):
                                    for j in range(0, wall_width):
                                        wall_depth = random.randrange(-1,1)
                                        bpy.ops.mesh.primitive_cube_add(location=(wall_start_pos.x + (j * (wall_part_size.x * 2)),
                                                                                  wall_start_pos.y + wall_depth,
                                                                                  wall_start_pos.z + i))
                                        bpy.ops.transform.resize(value=(wall_part_size.x, wall_part_size.y, wall_part_size.z))
                                        bpy.context.active_object.name = ("WallSide_%s_Part_%s_%s" % (k,i,j))

                                        if len(bpy.context.active_object.material_slots) == 0:
                                            bpy.ops.object.material_slot_add()
                                            bpy.context.active_object.material_slots[0].material = materials['BrickMat_%s' % random.randrange(0,5)]

                                        bpy.context.active_object.select = True
                                        wall_side.select = True
                                        bpy.context.scene.objects.active = wall_side
                                        bpy.ops.object.parent_set(type='OBJECT')
                                        bpy.ops.object.select_all(action='DESELECT')

                                wall_side.select = True
                                wall_empty.select = True
                                bpy.context.scene.objects.active = wall_empty
                                bpy.ops.object.parent_set(type='OBJECT')
                                bpy.ops.object.select_all(action='DESELECT')

                            side1 = objects["Wall:Side_1"]
                            side2 = objects["Wall:Side_2"]

                            wall_rot = mathutils.Quaternion(mathutils.Vector((0,0,1)), math.radians(-90))

                            side1_pos = mathutils.Vector((wall_part_size.x * wall_width, wall_part_size.y * 5,0))
                            side1.location = side1_pos
                            side1.rotation_mode = 'QUATERNION'
                            side1.rotation_quaternion = wall_rot

                            side2_pos = mathutils.Vector((wall_start_pos.x, wall_part_size.y * 5,wall_start_pos.z))
                            side2.location = side2_pos
                            side2.rotation_mode = 'QUATERNION'
                            side2.rotation_quaternion = wall_rot

                            print("> Background:Wall added")

                    # turn off/on the randomization of the clothes in a pool
                    # depending on whether the GlimpseFixedClothes is not "none"
                    fixed_clothes = bpy.context.scene.GlimpseFixedClothes

                    if fixed_clothes != 'none':

                        if 'clothes' not in meta:

                            print ("> Randomization of clothes is off - setting to fixed set")
                            bpy.data.objects['Camera'].constraints['Track To'].target = body_pose
                            clothes_meta = {}

                            fixed_clothes = fixed_clothes.split(",")

                            for wear in fixed_clothes:
                                if wear in hat_choices:
                                    hat_obj_name = "%sClothes:%s" % (body, wear)
                                    if hat_obj_name in bpy.data.objects:
                                        hat_obj = bpy.data.objects[hat_obj_name]
                                        hat_obj.hide = False
                                        hat_obj.layers[0] = True
                                        clothes_meta['hat'] = wear

                                if wear in trouser_choices:
                                    trouser_obj_name = "%sClothes:%s" % (body, wear)
                                    if trouser_obj_name in bpy.data.objects:
                                        trouser_obj = bpy.data.objects[trouser_obj_name]
                                        trouser_obj.hide = False
                                        trouser_obj.layers[0] = True
                                        clothes_meta['trousers'] = wear

                                if wear in top_choices:
                                    top_obj_name = "%sClothes:%s" % (body, wear)
                                    if top_obj_name in bpy.data.objects:
                                        top_obj = bpy.data.objects[top_obj_name]
                                        top_obj.hide = False
                                        top_obj.layers[0] = True
                                        clothes_meta['top'] = wear

                                if wear in glasses_choices:
                                    glasses_obj_name = "%sClothes:%s" % (body, wear)
                                    if glasses_obj_name in bpy.data.objects:
                                        glasses_obj = bpy.data.objects[glasses_obj_name]
                                        glasses_obj.hide = False
                                        glasses_obj.layers[0] = True
                                        clothes_meta['glasses'] = wear

                            context.scene.layers = render_layers
                            meta['clothes'] = clothes_meta

                    else:

                        if 'clothes' not in meta or frame % bpy.context.scene.GlimpseClothingStep == 0:
                            print("> Randomizing clothing")

                            # randomize the model
                            #body = numpy.random.choice(all_bodies)
                            hat = numpy.random.choice(hat_choices, p=hat_probabilities)
                            trousers = numpy.random.choice(trouser_choices, p=trouser_probabilities)
                            top = numpy.random.choice(top_choices, p=top_probabilities)
                            glasses = numpy.random.choice(glasses_choices, p=glasses_probabilities)

                            bpy.data.objects['Camera'].constraints['Track To'].target = body_pose

                            clothes_meta = {}

                            if hat != 'none':
                                hat_obj_name = "%sClothes:%s" % (body, hat)
                                if hat_obj_name in bpy.data.objects:
                                    hat_obj = bpy.data.objects[hat_obj_name]
                                    hat_obj.hide = False
                                    hat_obj.layers[0] = True
                                    clothes_meta['hat'] = hat

                            if trousers != 'none':
                                trouser_obj_name = "%sClothes:%s" % (body, trousers)
                                if trouser_obj_name in bpy.data.objects:
                                    trouser_obj = bpy.data.objects[trouser_obj_name]
                                    trouser_obj.hide = False
                                    trouser_obj.layers[0] = True
                                    clothes_meta['trousers'] = trousers

                            if top != 'none':
                                top_obj_name = "%sClothes:%s" % (body, top)
                                if top_obj_name in bpy.data.objects:
                                    top_obj = bpy.data.objects[top_obj_name]
                                    top_obj.hide = False
                                    top_obj.layers[0] = True
                                    clothes_meta['top'] = top

                            if glasses != 'none':
                                glasses_obj_name = "%sClothes:%s" % (body, glasses)
                                if glasses_obj_name in bpy.data.objects:
                                    glasses_obj = bpy.data.objects[glasses_obj_name]
                                    glasses_obj.hide = False
                                    glasses_obj.layers[0] = True
                                    clothes_meta['glasses'] = glasses

                            context.scene.layers = render_layers
                            meta['clothes'] = clothes_meta
                    
                    for key, val in sorted(meta['clothes'].items()):
                        if meta['clothes'][key] in clothes_stats:
                            clothes_stats[meta['clothes'][key]] += 1
                        else: 
                            clothes_stats[meta['clothes'][key]] = 1

                    # Make sure you render the clothes specified in meta
                    hide_body_clothes(body)
                    if not is_camera_debug:
                        show_body_clothes_from_meta(body)

                    # Randomize the placement of the camera...
                    #
                    # See RandomizedCamView script embedded in glimpse-training.blend
                    # for an experimental copy of this code where it's easy
                    # to get interactive feedback / test that it's working
                    # (Alt-P to run)
                    focus_bone_name = bpy.context.scene.GlimpseFocusBone 
                    focus = body_pose.pose.bones[focus_bone_name]
                    person_forward_2d = (focus.matrix.to_3x3() * z_forward).xy.normalized()

                    # Vector.rotate doesn't work for 2D vectors...
                    person_forward = mathutils.Vector((person_forward_2d.x, person_forward_2d.y, 0))

                    if is_camera_debug:
                        rot = mathutils.Quaternion((0.707, 0.707, 0, 0))
                        camera.rotation_mode = 'QUATERNION'
                        camera.rotation_quaternion = rot
                        camera_location = mathutils.Vector((0, -3, 1))
                        camera.location = camera_location
                        dist_m = 3
                        view_angle = 0

                    # the distance to the camera as well as the
                    # angle needs to be fixed if set in parameter
                    elif is_camera_fixed:

                        dist_mm = min_distance_mm
                        dist_m = dist_mm / 1000
                        view_angle = min_viewing_angle
                        height_mm = min_height_mm
                        target_x_mm = focus.head.x * 1000
                        target_y_mm = focus.head.y * 1000
                        target_z_mm = focus.head.z * 1000

                        # fixed camera location
                        if camera_location.length == 0:
                            view_rot = mathutils.Quaternion((0, 0, 1), math.radians(view_angle))
                            person_forward.rotate(view_rot)
                            person_forward_2d = person_forward.xy
                            camera_location = focus.head.xy + dist_m * person_forward_2d

                        # fixed camera pointing
                        if target.length == 0:
                            target = mathutils.Vector((target_x_mm / 1000,
                                                       target_y_mm / 1000,
                                                       target_z_mm / 1000))

                        # reset camera pointing
                        is_camera_pointing = False

                    elif is_camera_smooth_movement:

                        # add perlin noise to all factors of the camera
                        # final position for a given frame to simulate
                        # the smooth movement of a hand holding a phone camera

                        # mid points and ranges based on min and max values
                        height_range_mm = max_height_mm - min_height_mm
                        mid_height_mm = min_height_mm + (height_range_mm / 2)
                        dist_range_mm = max_distance_mm - min_distance_mm
                        mid_dist_mm = min_distance_mm + (dist_range_mm / 2)
                        view_angle_range_mm = max_viewing_angle - min_viewing_angle
                        mid_view_angle = min_viewing_angle + (view_angle_range_mm / 2)

                        def perlin_noise(frame, bvh_fps, frequency, seed):
                            frame_time = (1 / bvh_fps) * frame * frequency
                            position = mathutils.Vector((frame_time, 0, seed))
                            noise = mathutils.noise.noise(position, mathutils.noise.types.STDPERLIN)
                            return noise

                        height_mm = mid_height_mm + (perlin_noise(frame, bvh_fps, frequency, height_seed) * height_range_mm)
                        dist_mm = mid_dist_mm + (perlin_noise(frame, bvh_fps, frequency, height_seed + 1) * dist_range_mm)
                        dist_m = dist_mm / 1000
                        view_angle = mid_view_angle + (perlin_noise(frame, bvh_fps, frequency, height_seed + 2) * view_angle_range_mm)

                        target_x_mm = (focus.head.x * 1000) + perlin_noise(frame, bvh_fps, frequency, height_seed + 3)
                        target_y_mm = (focus.head.y * 1000) + perlin_noise(frame, bvh_fps, frequency, height_seed + 4)
                        target_z_mm = (focus.head.z * 1000) + perlin_noise(frame, bvh_fps, frequency, height_seed + 5)

                        # smooth camera location
                        view_rot = mathutils.Quaternion((0, 0, 1), math.radians(view_angle))

                        person_forward.rotate(view_rot)
                        person_forward_2d = person_forward.xy
                        camera_location = focus.head.xy + dist_m * person_forward_2d

                        # smooth camera target pointing
                        target = mathutils.Vector((target_x_mm / 1000,
                                                   target_y_mm / 1000,
                                                   target_z_mm / 1000))

                    else:

                        dist_mm = random.randrange(min_distance_mm, max_distance_mm)
                        dist_m = dist_mm / 1000
                        view_angle = random.randrange(min_viewing_angle, max_viewing_angle)
                        height_mm = random.randrange(min_height_mm, max_height_mm)

                        # We roughly point the camera at the focus bone but randomize
                        # this a little...
                        target_fuzz_range_mm = 100
                        focus_x_mm = focus.head.x * 1000
                        focus_y_mm = focus.head.y * 1000
                        focus_z_mm = focus.head.z * 1000
                        target_x_mm = random.randrange(int(focus_x_mm - target_fuzz_range_mm),
                                                       int(focus_x_mm + target_fuzz_range_mm))
                        target_y_mm = random.randrange(int(focus_y_mm - target_fuzz_range_mm),
                                                       int(focus_y_mm + target_fuzz_range_mm))
                        target_z_mm = random.randrange(int(focus_z_mm - target_fuzz_range_mm),
                                                       int(focus_z_mm + target_fuzz_range_mm))

                        # camera location
                        view_rot = mathutils.Quaternion((0, 0, 1), math.radians(view_angle))
                        person_forward.rotate(view_rot)
                        person_forward_2d = person_forward.xy
                        camera_location = focus.head.xy + dist_m * person_forward_2d

                        # camera target pointing
                        target = mathutils.Vector((target_x_mm / 1000,
                                                   target_y_mm / 1000,
                                                   target_z_mm / 1000))

                        # reset camera pointing
                        is_camera_pointing = False

                    if not is_camera_debug:
                        camera.location.z = height_mm / 1000

                    meta['camera']['distance'] = dist_m
                    meta['camera']['viewing_angle'] = view_angle

                    if not is_camera_pointing and not is_camera_debug:
                        camera.location.xy = camera_location
                        direction = target - camera.location
                        rot = direction.to_track_quat('-Z', 'Y')

                        camera.rotation_mode = 'QUATERNION'
                        camera.rotation_quaternion = rot
                        is_camera_pointing = True

                    context.scene.update() # update camera.matrix_world

                    camera_world_inverse_mat4 = camera.matrix_world.inverted()

                    # Calculating the gravity vector
                    # We are flipping the z-axis to match the iOS gravity vector specs
                    z_point = camera.matrix_world.translation - mathutils.Vector((0, 0, 1))
                    cam_gravity_vec = (camera_world_inverse_mat4 * z_point).normalized()
                    meta['gravity'] = [cam_gravity_vec.x, cam_gravity_vec.y, -cam_gravity_vec.z]
                    
                    meta['bones'] = []
                    for bone in body_pose.pose.bones:
                        head_cam = camera_world_inverse_mat4 * bone.head.to_4d()
                        tail_cam = camera_world_inverse_mat4 * bone.tail.to_4d()
                        bone_meta = {
                                'name': bone.name,
                                'head': [head_cam.x, head_cam.y, head_cam.z],
                                'tail': [tail_cam.x, tail_cam.y, tail_cam.z],
                        }
                        meta['bones'].append(bone_meta)

                    pose_cam_vec = body_pose.pose.bones['pelvis'].head - camera.location

                    section_name = body
                    for key in meta['clothes']:
                        section_name += '_' + key

                    context.scene.node_tree.nodes['LabelOutput'].base_path = os.path.join(abs_gen_dir, "labels", bvh_name, section_name)
                    #context.scene.node_tree.nodes['DepthOutput'].base_path = os.path.join(abs_gen_dir, "depth", bvh_name[:-4], section_name)

                    context.scene.render.filepath = os.path.join(abs_gen_dir, "depth", bvh_name, section_name, "Image%04u" % frame)
                    print("> Rendering " + bvh_name +
                          " frame " + str(frame) +
                          " to " + bpy.context.scene.node_tree.nodes['LabelOutput'].base_path)

                    bpy.ops.render.render(write_still=True)

                    meta_filename = os.path.join(abs_gen_dir, "labels", bvh_name, section_name, 'Image%04u.json' % frame)
                    with open(meta_filename, 'w') as fp:
                        json.dump(meta, fp, indent=2)


            # For now we unconditionally render each mocap using all the body
            # meshes we have, just randomizing the clothing
            fixed_bodies = bpy.context.scene.GlimpseFixedBodies;
            if fixed_bodies != 'none':
                fixed_bodies = fixed_bodies.split(",")
                for fixed_body in fixed_bodies:
                    if fixed_body in all_bodies:
                        render_body(fixed_body)
            else:
                for body in all_bodies:
                    render_body(body)

        print("Rendering MoCap indices from " + str(context.scene.GlimpseBvhGenFrom) + " to " + str(context.scene.GlimpseBvhGenTo))
        for idx in range(bpy.context.scene.GlimpseBvhGenFrom, bpy.context.scene.GlimpseBvhGenTo):
            render_bvh_index(idx)

        if bpy.context.scene.GlimpseDryRun:
            print("> DRY RUN FRAME COUNT:%d" % frame_count)         
        
        if bpy.context.scene.GlimpseShowStats:
          
            dash = '-' * 85
            print(dash)
            print('{:^85}'.format("RENDERING STATS"))
            print(dash)   
            print('{:<15s}{:<10d}'.format("Total Frames:", frame_count))   
            print('{:<15s}{:<10d}'.format("Total Skipped Frames:", frame_skip_count))                        
            print(dash)            
            print('{:^85}'.format("BODIES"))
            print(dash)   
            print('{:<15s}{:<10s}{:<8s}{:<8s}'.format("NAME", "FRAMES", "RATIO FRA(%)", " "))    
            print(dash)
    
            for body, val in sorted(body_stats.items(), key=lambda kv: (-kv[1], kv[0])):
                percentage = val / frame_count * 100
                ratio = get_percentage_bar(val, frame_count)
                print('{:<15s}{:<10d}{:<8.2f}{:<8s}'.format(body, val, percentage, ratio))

            print(dash)
            print('{:^85}'.format("CLOTHES"))
            print(dash)  
            print('{:<25s}{:<10s}{:<8s}{:<8s}'.format("NAME", "FRAMES", "RATIO FRA(%)", " "))    
            print(dash)
    
            for clothing, val in sorted(clothes_stats.items(), key=lambda kv: (-kv[1], kv[0])):
                percentage = val / frame_count * 100
                ratio = get_percentage_bar(val, frame_count)

                print('{:<25s}{:<10d}{:<8.2f}{:<8s}'.format(clothing, val, percentage, ratio))

            print(dash)

        return {'FINISHED'}

class GeneratePanel(bpy.types.Panel):
    bl_category = "Glimpse Generate"
    bl_label = "GlimpseGenerate v %d.%d.%d: Main" % bl_info["version"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"

    def draw(self, context):
        layout = self.layout
        ob = context.object
        scn = context.scene

        layout.separator()
        layout.prop(scn, "GlimpseDataRoot", text="Output")
        layout.separator()
        layout.prop(scn, "GlimpseClothesRoot", text="Clothes")
        layout.separator()
        #layout.prop(scn, "GlimpseDebug")
        #layout.separator()
        row = layout.row()
        row.prop(scn, "GlimpseBvhGenFrom", text="From")
        row.prop(scn, "GlimpseBvhGenTo", text="To")
        layout.separator()
        layout.operator("glimpse.generate_data")


# Is there a better place to track this state?
bvh_index = []
bvh_file_index = {}
bvh_index_pos = 0

def get_bvh_index_pos(self):
    return bvh_index_pos


def set_bvh_index_pos(self, value):
    global bvh_index_pos

    if value >= 0 and value < len(bvh_index) and value != bvh_index_pos:
        update_current_bvh_state(None)
        bvh_index_pos = value
        switch_current_bvh_state(None)


# NB: sometimes called with no op
def update_current_bvh_state(optional_op):
    if bvh_index_pos >= len(bvh_index):
        if optional_op != None:
            optional_op.report({'ERROR'}, "Invalid Mo-cap index")
        return

    bvh_state = bvh_index[bvh_index_pos]

    bvh_state['start'] = bpy.context.scene.frame_start
    bvh_state['end'] = bpy.context.scene.frame_end


def load_bvh_file(bvh_state):

    pose_obj = bpy.context.scene.objects.active

    bpy.context.scene.McpStartFrame = 1
    bpy.context.scene.McpEndFrame = 1000
    bpy.ops.mcp.load_and_retarget(filepath = bpy.path.abspath(os.path.join(bpy.context.scene.GlimpseBvhRoot,ntpath_to_os(bvh_state['file']))))

    if 'end' not in bvh_state:
        if bpy.context.object.animation_data:
            frame_end = bpy.context.object.animation_data.action.frame_range[1]
        else:
            frame_end = 1000
        bvh_state['end'] = frame_end

def assign_body_poses(action_name):
    for body in all_bodies:
        pose_obj = bpy.data.objects[body + 'PoseObject']
        if pose_obj.animation_data == None:
            pose_obj.animation_data_create()
        pose_obj.animation_data.action = bpy.data.actions[action_name]

# NB: sometimes called with no op
def switch_current_bvh_state(optional_op):
    if bvh_index_pos >= len(bvh_index):
        if optional_op != None:
            optional_op.report({'ERROR'}, "Invalid Mo-cap index")
        return

    bvh = bvh_index[bvh_index_pos]
    bvh_name = bvh['name']
    action_name = "Base" + bvh_name

    if action_name not in bpy.data.actions:
        if optional_op != None:
            optional_op.report({'WARNING'}, "Mocap index %d (%s) not preloaded yet" % (bvh_index_pos, bvh_name))
        return

    assign_body_poses(action_name)


def load_mocap_index():

    bvh_index = []

    try:
        with open(bpy.path.abspath(os.path.join(bpy.context.scene.GlimpseBvhRoot, "index.json"))) as fp:
            bvh_index = json.load(fp)

        # early version might have indexed non-bvh files...
        keep = [bvh for bvh in bvh_index if bvh['file'][-4:] == '.bvh']
        bvh_index = keep

        bpy.types.Scene.GlimpseBvhIndexPos[1]['max'] = max(0, len(bvh_index) - 1)

        for bvh in bvh_index:
            bvh_file_index[bvh['file']] = bvh

            # normalize so we don't have to consider that it's left unspecified
            if 'blacklist' not in bvh:
                bvh['blacklist'] = False

            if 'tags' not in bvh:
                bvh['tags'] = { 'unknown' }

            if 'start' not in bvh:
                bvh['start'] = 1

            if 'name' not in bvh:
                bvh['name'] = ntpath.basename(bvh['file'])[:-4]

            if 'fps' not in bvh:
                bvh['fps'] = 120

            if 'end' not in bvh:
                bvh_name = bvh['name']

                action_name = "Base" + bvh_name
                if action_name in bpy.data.actions:
                    action = bpy.data.actions[action_name]
                    bvh['end'] = action.frame_range[1]
                    print("WARNING: determined %s frame range based on action since 'end' not found in index" % bvh['name']);
                else:
                    #print("WARNING: just assuming mocap has < 1000 frames since action wasn't preloaded")
                    bvh['end'] = 1000

    except IOError as e:
        self.report({'INFO'}, str(e))

    return bvh_index


class VIEW3D_MoCap_OpenBvhIndexButton(bpy.types.Operator):
    bl_idname = "glimpse.open_bvh_index"
    bl_label = "Load Index"

    def execute(self, context):
        global bvh_index
        global bvh_file_index
        global bvh_index_pos

        bvh_index = []
        bvh_file_index = {}
        bvh_index_pos = 0

        for ob in bpy.context.selected_objects:
            ob.select = False

        pose_obj = bpy.data.objects['Man0PoseObject']
        pose_obj.select=True
        context.scene.layers = pose_obj.layers
        context.scene.objects.active = pose_obj

        bvh_index = load_mocap_index()

        if len(bvh_index) > 0:
            if bvh_index[0]['blacklist']:
                skip_to_next_bvh(self)
            switch_current_bvh_state(self)

        return {"FINISHED"}


# we index bvh files using ntpath conventions
def ntpath_to_os(path):
    elems = path.split('\\')
    return os.path.join(*elems)


class VIEW3D_MoCap_BvhScanButton(bpy.types.Operator):
    bl_idname = "glimpse.scan_bvh_files"
    bl_label = "Scan for un-indexed .bvh files"

    def execute(self, context):
        global bvh_index
        global bvh_index_pos

        for root, dirs, files in os.walk(bpy.path.abspath(bpy.context.scene.GlimpseBvhRoot)):
            relroot = os.path.relpath(root, bpy.path.abspath(bpy.context.scene.GlimpseBvhRoot))
            for file in files:
                if file[-4:] != ".bvh":
                    continue

                filename = os.path.join(relroot, file)

                # no matter what OS we're using we want consistent filename
                # indexing conventions
                filename = ntpath.normpath(filename)
                filename = ntpath.normcase(filename)
                if filename not in bvh_file_index:
                    new_bvh_state = { 'file': filename, 'start': 1 }
                    bvh_index.append(new_bvh_state)
                    bvh_file_index[filename] = new_bvh_state

                    self.report({'INFO'}, "ADD: " + filename)

        return {"FINISHED"}


class VIEW3D_MoCap_SwitchBvhPrev(bpy.types.Operator):
    bl_idname = "glimpse.switch_bvh_prev"
    bl_label = "Prev"

    @classmethod
    def poll(cls, context):
        return bvh_index_pos > 0

    def execute(self, context):

        global bvh_index
        global bvh_index_pos

        update_current_bvh_state(self)

        while bvh_index_pos > 0:
            bvh_index_pos = bvh_index_pos - 1

            if bvh_index[bvh_index_pos]['blacklist'] == False:
                break

        switch_current_bvh_state(self)

        return {"FINISHED"}


def skip_to_next_bvh(op):
    global bvh_index_pos

    while bvh_index_pos < len(bvh_index) - 1:
        bvh_index_pos = bvh_index_pos + 1
        if bvh_index[bvh_index_pos]['blacklist'] == False:
            break


class VIEW3D_MainPanel_SwitchBvhNext(bpy.types.Operator):
    bl_idname = "glimpse.switch_bvh_next"
    bl_label = "Next"

    @classmethod
    def poll(cls, context):
        return bvh_index_pos < len(bvh_index) - 1

    def execute(self, context):
        global bvh_index
        global bvh_index_pos

        update_current_bvh_state(self)

        skip_to_next_bvh(self)

        switch_current_bvh_state(self)

        return {"FINISHED"}


class VIEW3D_MoCap_Preload(bpy.types.Operator):
    bl_idname = "glimpse.bvh_preload"
    bl_label = "Preload"

    @classmethod
    def poll(cls, context):
        return bvh_index_pos > 0

    def execute(self, context):

        global bvh_index
        global bvh_index_pos

        update_current_bvh_state(self)

        if bvh_index_pos >= len(bvh_index):
            self.report({'ERROR'}, "Invalid Mo-cap index")
            return

        load_bvh_file(bvh_index[bvh_index_pos])

        return {"FINISHED"}

def get_mocap_blacklist(self):
    if bvh_index_pos < len(bvh_index):
        return bvh_index[bvh_index_pos]['blacklist']
    else:
        return False


def set_mocap_blacklist(self, value):
    if bvh_index_pos < len(bvh_index):
        bvh_index[bvh_index_pos]['blacklist'] = value


class VIEW3D_MoCap_BlacklistButton(bpy.types.Operator):
    bl_idname = "glimpse.scan_bvh_files"
    bl_label = "Index BVH Files"

    def execute(self, context):
        bvh_index[bvh_index_pos]['blacklist': True]


class VIEW3D_MoCap_SaveBvhIndexButton(bpy.types.Operator):
    bl_idname = "glimpse.save_bvh_index"
    bl_label = "Save Index"

    def execute(self, context):

        if len(bvh_index):
            update_current_bvh_state(self)

            try:
                with open(bpy.path.abspath(os.path.join(bpy.context.scene.GlimpseBvhRoot, "index.json")), "w", encoding="utf-8") as fp:
                    json.dump(bvh_index, fp)
            except IOError as e:
                self.report({'ERROR'}, str(e))
        else:
            self.report({'ERROR'}, "No Mo-cap data to save")

        return {"FINISHED"}


class MoCapPanel(bpy.types.Panel):
    bl_label = "Motion Capture"
    bl_category = "Glimpse Generate"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"

    #@classmethod
    #def poll(self, context):
    #    return (context.object and context.object.type == 'ARMATURE')

    def draw(self, context):
        layout = self.layout
        ob = context.object
        scn = context.scene

        layout.prop(scn, "GlimpseBvhRoot", text="")
        layout.separator()
        layout.operator("glimpse.scan_bvh_files")
        layout.separator()
        layout.operator("glimpse.open_bvh_index")
        row = layout.row()
        row.operator("glimpse.switch_bvh_prev")
        row.operator("glimpse.switch_bvh_next")
        row.prop(scn, "GlimpseBvhIndexPos", text="")
        row.label("/ " + str(len(bvh_index)))
        layout.separator()
        layout.operator("glimpse.save_bvh_index")


class MoCapFilePanel(bpy.types.Panel):
    bl_label = "Motion Capture File"
    bl_category = "Glimpse Generate"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"

    @classmethod
    def poll(self, context):
        return (context.object and context.object.type == 'ARMATURE') and len(bvh_index) > 0

    def draw(self, context):
        layout = self.layout
        ob = context.object
        scn = context.scene

        if bvh_index_pos < len(bvh_index):
            layout.label("File: " + bvh_index[bvh_index_pos]['file'])
        else:
            layout.label("File: None")

        layout.separator()
        layout.prop(scn, "GlimpseMoCapBlacklist")


def register():
    bpy.types.Scene.GlimpseDataRoot = StringProperty(
            name="Training Directory",
            description="Root directory for training data",
            subtype='DIR_PATH',
            )

    bpy.types.Scene.GlimpseClothesRoot = StringProperty(
            name="Clothes Directory",
            description="Root directory for makehuman clothes",
            subtype='DIR_PATH',
            )

    bpy.types.Scene.GlimpseBvhRoot = StringProperty(
            name="BVH Directory",
            description="Root directory for .bvh motion capture files",
            subtype='DIR_PATH',
            )

    bpy.types.Scene.GlimpseGenDir = StringProperty(
            name="Dest Directory",
            description="Destination Directory for Generated Data",
            subtype='DIR_PATH',
            )

    bpy.types.Scene.GlimpseMocapLibrary = StringProperty(
            name="MoCap Library",
            description="Blender file containing preloaded library of mocap actions",
            subtype='FILE_PATH',
            )

    bpy.types.Scene.GlimpseDebug = BoolProperty(
            name="Debug",
            description="Enable Debugging",
            default=False,
            )

    bpy.types.Scene.GlimpseMoCapBlacklist = BoolProperty(
            name="Blacklist",
            description="Blacklist this Mo-cap file",
            default=False,
            get=get_mocap_blacklist,
            set=set_mocap_blacklist
            )

    bpy.types.Scene.GlimpseBvhIndexPos = IntProperty(
            name="Index",
            description="Current BVH state index",
            default=0,
            min=0,
            max=5000,
            get=get_bvh_index_pos,
            set=set_bvh_index_pos
            )

    bpy.types.Scene.GlimpseBvhGenFrom = IntProperty(
            name="Index",
            description="From",
            default=0,
            min=0)

    bpy.types.Scene.GlimpseBvhGenTo = IntProperty(
            name="Index",
            description="To",
            default=0,
            min=0)
    
    bpy.types.Scene.GlimpseBvhTagsWhitelist = StringProperty(
            name="TagsWhitelist",
            description="A set of specified tags for index entries that will be rendered",
            default='all')

    bpy.types.Scene.GlimpseBvhTagsBlacklist = StringProperty(
            name="TagsBlacklist",
            description="A set of specified tags for index entries that will not be rendered",
            default='none')
    
    bpy.types.Scene.GlimpseBvhTagsSkip = StringProperty(
            name="TagsSkip",
            description="A set of specified tags for index entries that will not be rendered",
            default='none')
    
    bpy.types.Scene.GlimpseFocusBone = StringProperty(
            name="FocusBone",
            description="Bone in the armature the camera will focus on during renders",
            default='pelvis')

    bpy.types.Scene.GlimpseRenderWidth = IntProperty(
            name="RenderWidth",
            description="Width, in pixels, of rendered frames",
            default=0,
            min=10,
            max=4096)

    bpy.types.Scene.GlimpseRenderHeight = IntProperty(
            name="RenderHeight",
            description="Height, in pixels, of rendered frames",
            default=0,
            min=10,
            max=4096)

    bpy.types.Scene.GlimpseVerticalFOV = FloatProperty(
            name="VerticalFOV",
            description="Vertical field of view of camera",
            default=54.5,
            min=1,
            max=180)

    bpy.types.Scene.GlimpseMinCameraDistanceMM = IntProperty(
            name="MinCameraDistanceMM",
            description="Minimum distance of camera",
            default=2000,
            min=1500,
            max=10000)

    bpy.types.Scene.GlimpseMaxCameraDistanceMM = IntProperty(
            name="MaxCameraDistanceMM",
            description="Maximum distance of camera",
            default=2500,
            min=1500,
            max=10000)

    bpy.types.Scene.GlimpseMinCameraHeightMM = IntProperty(
            name="MinCameraHeightMM",
            description="Minimum height of camera",
            default=1100,
            min=0,
            max=5000)

    bpy.types.Scene.GlimpseMaxCameraHeightMM = IntProperty(
            name="MaxCameraHeightMM",
            description="Maximum height of camera",
            default=1400,
            min=0,
            max=5000)

    bpy.types.Scene.GlimpseMinViewingAngle = IntProperty(
            name="MinViewAngle",
            description="Maximum viewing angle, to left of center, for rendered training images",
            default=30,
            min=-180,
            max=180)

    bpy.types.Scene.GlimpseMaxViewingAngle = IntProperty(
            name="MaxViewAngle",
            description="Maximum viewing angle, to right of center, for rendered training images",
            default=0,
            min=-180,
            max=180)

    bpy.types.Scene.GlimpseDryRun = BoolProperty(
            name="DryRun",
            description="Dry run generator - just print summary",
            default=False)

    bpy.types.Scene.GlimpseSkipPercentage = IntProperty(
            name="SkipPercent",
            description="Randomized percentage of frames to skip generating",
            default=0,
            min=0,
            max=100)

    bpy.types.Scene.GlimpseClothingStep = IntProperty(
            name="ClothingStep",
            description="Randomize the clothing every N frames",
            default=5,
            min=1,
            max=1000)

    bpy.types.Scene.GlimpseFixedCamera = BoolProperty(
            name="FixedCamera",
            description="Lock camera in a fixed position using the specified min parameters",
            default=False)
    bpy.types.Scene.GlimpseDebugCamera = BoolProperty(
            name="DebugCamera",
            description="Lock camera straight in front of a model in order to debug glimpse viewer",
            default=False)

    bpy.types.Scene.GlimpseSmoothCameraMovement = BoolProperty(
            name="SmoothCameraMovement",
            description="Smooth camera movement (disable randomization of the camera position and orientation)",
            default=False)
    bpy.types.Scene.GlimpseSmoothCameraFrequency = IntProperty(
            name="SmoothCameraFrequency",
            description="Period at which data is sampled when --smooth-camera-movement is enabled",
            default=1,
            min=1,
            max=100)

    bpy.types.Scene.GlimpseFixedClothes = StringProperty(
            name="FixedClothes",
            description="A set of specified clothes to be used in all renders",
            default='none')

    bpy.types.Scene.GlimpseFixedBodies = StringProperty(
            name="FixedBodies",
            description="A specified body to use during the rendering",
            default='none')

    bpy.types.Scene.GlimpseAddedBackground = BoolProperty(
            name="AddedBackground",
            description="Add background in a form of a floor and walls",
            default=False)

    bpy.types.Scene.GlimpseShowStats = BoolProperty(
            name="ShowStats",
            description="Output statistics after the rendering",
            default=False)

    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
