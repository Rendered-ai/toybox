# Copyright 2019-2022 DADoES, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the root directory in the "LICENSE" file or at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import bpy
import mathutils
import anatools.lib.context as ctx
from anatools.lib.node import Node
from anatools.lib.scene import AnaScene

from toybox.lib.parsers import parse_vec3
import logging
import imageio
import math
import os
import numpy
import glob

logger = logging.getLogger(__name__)

class LightNode(Node):
    """
    A class to represent a the Light node, a node that crates a lamp in the scene.
    """

    def exec(self):
        """Execute node"""
        logger.info("Executing {}".format(self.name))
        lightName = self.name
        # Get the light data
        lightType = self.inputs["Type"][0]
        lightEnergy = float(self.inputs["Radiant Power (W)"][0])
        lightData = bpy.data.lights.new(lightName, type=lightType)
        lightData.energy = lightEnergy

        # Color: shared by Spot and Point. Accepts "[r, g, b]" string or a
        # wired Vector3D / 3-element array. Channels are clamped at 0
        # because negative emission is not physical; values above 1.0 are
        # allowed (Blender lets you over-saturate a colour to amplify a
        # hue while keeping Radiant Power separate).
        lightColor = parse_vec3(self.inputs["Color"][0], name="Color", node="Light")
        lightData.color = tuple(max(0.0, c) for c in lightColor)

        logging.info("Light Config.. \n" + '\n'.join([f'\t{k}: {getattr(lightData, k)}' for k in dir(lightData) if '__' not in k]))

        #Instantiate the light
        lightLocation = parse_vec3(self.inputs["Location (m)"][0], name="Location (m)", node="Light")

        lightObject = bpy.data.objects.new(lightName, lightData)
        lightObject.location = lightLocation

        # Direction matters only for Spot. For Point, Blender ignores rotation,
        # so we skip the point_at call and save the math.
        if lightType == "SPOT":
            target = parse_vec3(self.inputs["Target (m)"][0], name="Target (m)", node="Light")
            point_at(lightObject, mathutils.Vector(target))

        return {'Light': lightObject}


class RenderNode(Node):
    """
    A class to represent a the Render node, a node that renders an image of the given scene.
    Executing the Render node creates an image, annotation, and metadata file.
    """

    def exec(self):
        """Execute node"""
        logger.info("Executing %s", self.name)

        #Get the reference to the blender scene
        scn = bpy.context.scene

        scene_input = self.inputs.get("Scene", [""]) or [""]
        upstream_scene = scene_input[0] if scene_input and scene_input[0] not in ("", None) else None
        if upstream_scene is None:
            raise RuntimeError(
                "RenderNode requires a wired Scene input (from a Blend File Scene "
                "or Procedural Scene node)."
            )

        # Camera is set by the upstream scene node (scn.camera = cam_obj).
        # Blender API: the active camera is a scene-space concern, not render-time.
        if scn.camera is None:
            raise RuntimeError(
                "RenderNode: scn.camera is not set. Ensure the Scene node has a "
                "Camera wired (Blend File Scene) or is using the built-in Look Down "
                "camera (Procedural Scene)."
            )

        #Set the render resolution
        # Set up the camera configuration data
        res = self.inputs["Resolution (px)"][0]
        if type(res)==str:
            res = [int(v) for v in res.replace('[','').replace(']','').split(',')]
        scn.render.resolution_x = res[0]
        scn.render.resolution_y = res[1]
        sensor_name = 'RGBCamera'
        scene = upstream_scene
        objects = scene.objects
        logger.info("RenderNode: using upstream Scene with %d objects", len(objects))

        #Configure the compositor to include a denoise node for the image
        s = bpy.data.scenes[ctx.channel.name]
        c_rl = s.node_tree.nodes['Render Layers']
        c_c = s.node_tree.nodes['Composite']
        c_dn = s.node_tree.nodes.new('CompositorNodeDenoise')
        s.node_tree.nodes.remove(s.node_tree.nodes['imgout'])
        c_of = s.node_tree.nodes.new('CompositorNodeOutputFile')
        c_of.base_path = os.path.join(ctx.output,'images')
        c_of.file_slots.clear()
        compositeNodeFieldName = f'{ctx.interp_num:010}-#-{sensor_name}.png'
        c_of.file_slots.new(compositeNodeFieldName)
        s.node_tree.links.new(c_rl.outputs['Image'], c_dn.inputs['Image'])

        _blur_px = float(bpy.context.scene.get("hdri_blur_px", 0.0) or 0.0)
        if _blur_px > 0.0:
            c_blur = s.node_tree.nodes.new('CompositorNodeBlur')
            c_blur.filter_type = 'GAUSS'
            # size_x/y are int pixels; the Size input scales at runtime for sub-px.
            c_blur.size_x = 1
            c_blur.size_y = 1
            c_blur.inputs['Size'].default_value = _blur_px
            s.node_tree.links.new(c_dn.outputs['Image'], c_blur.inputs['Image'])
            s.node_tree.links.new(c_blur.outputs['Image'], c_c.inputs['Image'])
            s.node_tree.links.new(c_blur.outputs['Image'], c_of.inputs[compositeNodeFieldName])
        else:
            s.node_tree.links.new(c_dn.outputs['Image'], c_c.inputs['Image'])
            s.node_tree.links.new(c_dn.outputs['Image'], c_of.inputs[compositeNodeFieldName])

        # Gated debug blend dump: saves the full .blend to output/test/ immediately
        # before rendering so the user can open it in Blender to verify light,
        # camera, and object placement.  Activated by:
        #   - graph input  "Save Blend File" == "Enabled", OR
        #   - environment  TOYBOX_SAVE_DEBUG_BLEND=1
        _dump_blend = self.inputs.get("Save Blend File", ["Disabled"])[0]
        if _dump_blend == "Enabled" or os.environ.get("TOYBOX_SAVE_DEBUG_BLEND", "0") == "1":
            _test_dir = os.path.join(ctx.output, "test")
            os.makedirs(_test_dir, exist_ok=True)
            _blend_path = os.path.join(
                _test_dir,
                f"{ctx.interp_num:010}-{scn.frame_current}-debug.blend",
            )
            bpy.context.preferences.filepaths.save_version = 0
            bpy.ops.wm.save_as_mainfile(filepath=_blend_path)
            logger.info("RenderNode: debug blend saved -> %s", _blend_path)

        #Render the image
        if ctx.preview:
            logger.info("LOW RES Render for Preview")
            render(resolution='preview')
            imgfilename = f"{ctx.interp_num:010}-{scn.frame_current}-{sensor_name}.png"
            preview = imageio.imread(os.path.join(ctx.output,'images',imgfilename))
            imageio.imsave(os.path.join(ctx.output,'preview.png'), preview)
            return{}

        #bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.getcwd(),"scene4render.blend"))
        render()        

        #Prepare for annotataions
        for obj in objects:
            # Scene objects that aren't toybox objects-of-interest (e.g. a Floor
            # or Container wired as a Placed Object) may not implement the mask
            # hook; skip them rather than crash the run.
            if hasattr(obj, "setup_mask"):
                obj.setup_mask()
        
        collect_depth = self.inputs["Collect Depth and Normal Masks"][0]
        # Accept legacy 'T'/'F' as well as the new Enabled/Disabled convention.
        if collect_depth in ('Enabled', 'T'):
            #Configure compositor to write a depth and normal mask
            #Add the Z and normal pass veiw layers
            bpy.context.scene.view_layers["ViewLayer"].use_pass_z = True
            bpy.context.scene.view_layers["ViewLayer"].use_pass_normal = True
            #Connect the depth render layer to a file output node - normalize this for viewing purposes
            c_normalize = s.node_tree.nodes.new("CompositorNodeNormalize")
            depthOutFieldName = f'{ctx.interp_num:010}-#-{sensor_name}-depth.png'
            c_output_depth = s.node_tree.nodes.new('CompositorNodeOutputFile')
            c_output_depth.base_path = os.path.join(ctx.output,'masks')
            c_output_depth.file_slots.clear()
            c_output_depth.file_slots.new(depthOutFieldName)
            s.node_tree.links.new(c_rl.outputs["Depth"], c_normalize.inputs['Value'])
            s.node_tree.links.new(c_normalize.outputs['Value'], c_output_depth.inputs[depthOutFieldName])
            #Connect the normal render layer to a file output
            #c_normalize = s.node_tree.nodes.new("CompositorNodeNormalize")
            normalOutFieldName = f'{ctx.interp_num:010}-#-{sensor_name}-normal.png'
            c_output_normal = s.node_tree.nodes.new('CompositorNodeOutputFile')
            c_output_normal.base_path = os.path.join(ctx.output,'masks')
            c_output_normal.file_slots.clear()
            c_output_normal.file_slots.new(normalOutFieldName)
            # s.node_tree.links.new(c_rl.outputs["Normal"], c_normalize.inputs['Value'])
            # s.node_tree.links.new(c_normalize.outputs['Value'], c_output_depth.inputs[normalOutFieldName])
            s.node_tree.links.new(c_rl.outputs["Normal"], c_output_normal.inputs[normalOutFieldName])    

        #Remove link to image output file
        s = bpy.data.scenes[ctx.channel.name]
        c_of = s.node_tree.nodes['File Output']
        c_of.file_slots.clear()
        
        #Write masks
        #bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.getcwd(),"compositor4masks.blend"))
        render(resolution='masks')
        
        #You can re-link the output image file node if blender is needed to render the image again
        # c_of.file_slots.new(f'{ctx.interp_num:010}-#-{sensor_name}.png')
        # s.node_tree.links.new(c_dn.outputs[0], c_of.inputs[0])

        calculate_obstruction = self.inputs["Calculate Obstruction"][0]
        # Accept legacy 'T'/'F' as well as the new Enabled/Disabled convention.
        if calculate_obstruction in ('Disabled', 'F'):
            # Create annotations 
            scene.write_ana_annotations()
            scene.write_ana_metadata()
            return {}
        
        #Render masks for each object (only render a mask file for objects in the image)

        #Unlink all the object masks in the compositor
        links = scn.node_tree.links
        masknodes = [node for node in scn.node_tree.nodes if node.name.split('_')[-1]=='mask']
        masklinks = {}
        for masknode in masknodes:
            masklinks[masknode.index] = {
                'masknode': masknode,
                'socketinput': masknode.outputs[0].links[0].to_socket
            }
            links.remove(masknode.outputs[0].links[0])
        #Unlink the image from the compositor
        for link in scn.node_tree.nodes['Render Layers'].outputs['Image'].links:
            links.remove(link)

        masktemplate = os.path.join(scene.maskout.base_path,
                                    scene.maskout.file_slots[0].path + '.' + scene.maskout.format.file_format.lower())

        #Only render a mask file for objects in the image
        compositemaskfile = masktemplate.replace('#', str(scn.frame_current))
        compimg = imageio.imread(compositemaskfile)
        allmasks = compimg[numpy.nonzero(compimg)]
        renderedobjectidxs = numpy.unique(allmasks)
        renderedobjects = [obj for obj in objects if obj.instance in renderedobjectidxs]

        #Hide all but a single object and render a mask
        for obj in objects:
            obj.root.hide_render = True
            if obj not in renderedobjects:
                obj.rendered = False

        imgpath = scene.imgout.file_slots[0].path
        maskpath = scene.maskout.file_slots[0].path
        for obj in renderedobjects:
            obj.solo_mask_id = f'obj{obj.instance:03}'
            scene.maskout.file_slots[0].path = '{}-{}'.format(maskpath, obj.solo_mask_id)
            scene.imgout.file_slots[0].path = '{}-{}'.format(imgpath, obj.solo_mask_id)

            obj.root.hide_render = False

            # link the ID mask node to it's divide node
            masknode = masklinks[obj.instance]['masknode']
            socketinput = masklinks[obj.instance]['socketinput']
            links.new(masknode.outputs['Alpha'], socketinput)

            render(resolution='low')

            # rehide object
            obj.root.hide_render = True
            links.remove(masknode.outputs[0].links[0])

        #Create annotations
        # Normalise to legacy 'T'/'F' for downstream anatools annotation API.
        _obstruction_flag = 'T' if calculate_obstruction in ('Enabled', 'T') else 'F'
        scene.write_ana_annotations(calculate_obstruction=_obstruction_flag)
        scene.write_ana_metadata()

        logging.info("Number Objects Rendered: {}".format(len([o for o in objects if o.rendered])))

        #Clean up extra rendered files
        maskpattern = os.path.join(scene.maskout.base_path, maskpath.replace('#', str(scn.frame_current)))
        for filepath in glob.glob('{}-*'.format(maskpattern)):
            os.remove(filepath)
        imgpattern = os.path.join(scene.imgout.base_path, imgpath.replace('#', str(scn.frame_current)))
        for filepath in glob.glob('{}-*'.format(imgpattern)):
            os.remove(filepath)

        return {}


class AnimationRenderNode(Node):
    """Render a frame range for an animated scene.

    Iterates ``Start Frame`` → ``End Frame`` (inclusive) by ``Frame Step``,
    calling the Blender renderer once per frame.  Each frame produces:

    - ``images/{interp_num:010}-{frame}-RGBCamera.png``
    - ``annotations/{interp_num:010}-{frame}-RGBCamera.json``
    - ``metadata/{interp_num:010}-{frame}-RGBCamera.json``
    - ``masks/`` depth + normal if ``Collect Depth and Normal Masks`` is T

    Wire: ``Blend File Scene → Animation Render`` (same as ``Render``).
    The upstream scene must have an NLA animation strip active on the armature
    (supplied by the ``Animation`` node) for poses to change per frame.
    """

    def exec(self):
        logger.info("Executing %s", self.name)

        scn = bpy.context.scene

        scene_input = self.inputs.get("Scene", [""]) or [""]
        upstream_scene = scene_input[0] if scene_input and scene_input[0] not in ("", None) else None
        if upstream_scene is None:
            raise RuntimeError(
                "AnimationRenderNode requires a wired Scene input."
            )
        if scn.camera is None:
            raise RuntimeError(
                "AnimationRenderNode: scn.camera is not set. Wire a Camera into "
                "the upstream Scene node."
            )

        res = self.inputs["Resolution (px)"][0]
        if isinstance(res, str):
            res = [int(v) for v in res.replace("[", "").replace("]", "").split(",")]
        scn.render.resolution_x = res[0]
        scn.render.resolution_y = res[1]

        start  = int(float(self.inputs.get("Start Frame",  [1])[0]))
        end    = int(float(self.inputs.get("End Frame",   [30])[0]))
        step   = int(float(self.inputs.get("Frame Step",   [1])[0]))
        step   = max(1, step)

        collect_depth = self.inputs.get("Collect Depth and Normal Masks", ["F"])[0]

        _dump_blend = self.inputs.get("Save Blend File", ["Disabled"])[0]

        sensor_name = "RGBCamera"
        scene = upstream_scene
        objects = scene.objects

        for directory in ("images", "annotations", "masks", "metadata"):
            os.makedirs(os.path.join(ctx.output, directory), exist_ok=True)

        # Build compositor output nodes once (they use # as frame placeholder).
        s = bpy.data.scenes[ctx.channel.name]
        c_rl = s.node_tree.nodes["Render Layers"]
        c_c  = s.node_tree.nodes["Composite"]

        # Remove legacy imgout if present (Blend File Scene may leave one).
        if "imgout" in s.node_tree.nodes:
            s.node_tree.nodes.remove(s.node_tree.nodes["imgout"])

        c_dn = s.node_tree.nodes.new("CompositorNodeDenoise")
        c_of = s.node_tree.nodes.new("CompositorNodeOutputFile")
        c_of.base_path = os.path.join(ctx.output, "images")
        c_of.file_slots.clear()
        img_slot = f"{ctx.interp_num:010}-#-{sensor_name}.png"
        c_of.file_slots.new(img_slot)
        s.node_tree.links.new(c_rl.outputs["Image"], c_dn.inputs["Image"])
        s.node_tree.links.new(c_dn.outputs["Image"], c_c.inputs["Image"])
        s.node_tree.links.new(c_dn.outputs["Image"], c_of.inputs[img_slot])

        if collect_depth == "T":
            bpy.context.scene.view_layers["ViewLayer"].use_pass_z = True
            bpy.context.scene.view_layers["ViewLayer"].use_pass_normal = True
            c_norm = s.node_tree.nodes.new("CompositorNodeNormalize")
            c_depth_out = s.node_tree.nodes.new("CompositorNodeOutputFile")
            c_depth_out.base_path = os.path.join(ctx.output, "masks")
            c_depth_out.file_slots.clear()
            depth_slot = f"{ctx.interp_num:010}-#-{sensor_name}-depth.png"
            c_depth_out.file_slots.new(depth_slot)
            s.node_tree.links.new(c_rl.outputs["Depth"], c_norm.inputs["Value"])
            s.node_tree.links.new(c_norm.outputs["Value"], c_depth_out.inputs[depth_slot])
            c_normal_out = s.node_tree.nodes.new("CompositorNodeOutputFile")
            c_normal_out.base_path = os.path.join(ctx.output, "masks")
            c_normal_out.file_slots.clear()
            normal_slot = f"{ctx.interp_num:010}-#-{sensor_name}-normal.png"
            c_normal_out.file_slots.new(normal_slot)
            s.node_tree.links.new(c_rl.outputs["Normal"], c_normal_out.inputs[normal_slot])

        logger.info(
            "AnimationRender: frames %d→%d step=%d res=%dx%d",
            start, end, step, res[0], res[1],
        )

        frames = list(range(start, end + 1, step))

        for i, frame in enumerate(frames):
            scn.frame_set(frame)
            logger.info(
                "AnimationRender: set frame %d → scn.frame_current=%d (%d/%d)",
                frame, scn.frame_current, i + 1, len(frames),
            )

            # Save debug blend on the first frame only.
            if i == 0 and (
                _dump_blend == "Enabled"
                or os.environ.get("TOYBOX_SAVE_DEBUG_BLEND", "0") == "1"
            ):
                _test_dir = os.path.join(ctx.output, "test")
                os.makedirs(_test_dir, exist_ok=True)
                _blend_path = os.path.join(
                    _test_dir,
                    f"{ctx.interp_num:010}-{frame}-anim-debug.blend",
                )
                bpy.context.preferences.filepaths.save_version = 0
                bpy.ops.wm.save_as_mainfile(filepath=_blend_path)
                logger.info("AnimationRender: debug blend saved -> %s", _blend_path)

            if ctx.preview:
                render(resolution="preview")
                img_filename = f"{ctx.interp_num:010}-{scn.frame_current}-{sensor_name}.png"
                preview_src = os.path.join(ctx.output, "images", img_filename)
                if os.path.exists(preview_src):
                    import shutil
                    shutil.copy(preview_src, os.path.join(ctx.output, "preview.png"))
                return {}

            render()

            for obj in objects:
                if hasattr(obj, "setup_mask"):
                    obj.setup_mask()

            if collect_depth == "T":
                s2 = bpy.data.scenes[ctx.channel.name]
                c_of2 = s2.node_tree.nodes.get("File Output")
                if c_of2:
                    c_of2.file_slots.clear()
                render(resolution="masks")

            img_filename = f"{ctx.interp_num:010}-{scn.frame_current}-{sensor_name}.png"
            scene.filename = img_filename
            scene.write_ana_annotations()
            scene.write_ana_metadata()
            logger.info("AnimationRender: frame %d annotated → %s", frame, img_filename)

        logger.info("AnimationRender: done — %d frame(s) rendered", len(frames))
        return {}


def render(resolution='high'):
    scn = bpy.context.scene
    # Blender 4.x defaults on; would override explicit samples below.
    scn.cycles.use_adaptive_sampling = False

    hdri_mode = bool(scn.get("hdri_scene_mode", False))
    if hdri_mode:
        scn.cycles.use_denoising = True
        scn.cycles.denoiser = 'OPENIMAGEDENOISE'

    if resolution == 'preview':
        if scn.render.resolution_x > 1000:
            # For speed, set the resolution to a common multiple of the tile size
            scn.render.resolution_x = 640
            scn.render.resolution_y = 384

        scn.cycles.samples = 64 if hdri_mode else 8
        scn.cycles.max_bounces = 6

    elif resolution == 'high':
        # Higher samples and bounces diminishes speed for higher quality images
        scn.cycles.samples = 256 if hdri_mode else 15
        scn.cycles.max_bounces = 12

    else: # masks
        scn.cycles.samples = 1
        scn.cycles.max_bounces = 1

    # In Blender 4.2 headless, 'INVOKE_DEFAULT' spawns a modal render that
    # does not block the script. Use the default EXEC_DEFAULT context with
    # write_still=True so the call blocks until rendering completes.
    bpy.ops.render.render(write_still=True)


def point_at(obj, target, roll=0):
    """
    Rotate obj to look at target

    :arg obj: the object to be rotated. Usually the camera
    :arg target: the location (3-tuple or Vector) to be looked at
    :arg roll: The angle of rotation about the axis from obj to target in radians. 

    Based on: https://blender.stackexchange.com/a/5220/12947 (ideasman42)      
    Based on: https://blender.stackexchange.com/questions/5210/pointing-the-camera-in-a-particular-direction-programmatically (sadern-alwis)
    """
    if not isinstance(target, mathutils.Vector):
        target = mathutils.Vector(target)
    loc = obj.location
    # direction points from the object to the target
    direction = target - loc
    
    #tracker, rotator = (('-Z', 'Y'),'Z') if obj.type=='CAMERA' else (('X', 'Z'),'Y') #because new cameras points down(-Z), usually meshes point (-Y)
    tracker, rotator = (('-Z', 'Y'),'Z')
    quat = direction.to_track_quat(*tracker)
    
    # /usr/share/blender/scripts/addons/add_advanced_objects_menu/arrange_on_curve.py
    quat = quat.to_matrix().to_4x4()
    rollMatrix = mathutils.Matrix.Rotation(roll, 4, rotator)

    # remember the current location, since assigning to obj.matrix_world changes it
    loc = loc.to_tuple()
    #obj.matrix_world = quat * rollMatrix
    # in blender 2.8 and above @ is used to multiply matrices
    # using * still works but results in unexpected behaviour!
    obj.matrix_world = quat @ rollMatrix
    obj.location = loc