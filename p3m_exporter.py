# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Perfect 3D Model (.p3m) Exporter",
    "author": "John Kenneth L. Andales (Raitou)",
    "description": "(Fixed) Exports blender model to .p3m, including meshes and bones",
    "blender": (2, 83, 1),
    "version": (1, 0, 0),
    "location": "File > Export > Perfect 3D Model (.p3m)",
    "warning": "",
    "category": "Import-Export"
}

import os
import struct
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

def removeDuplicates(boneList):
     #Fix duplicates
    for i in range(len(boneList)):
        try:
            for j in range(i+1, len(boneList)):
                if boneList[i]['head']['x'] == boneList[j]['head']['x'] and boneList[i]['head']['y'] == boneList[j]['head']['y'] and  boneList[i]['head']['z'] == boneList[j]['head']['z']:
                    getList = boneList[i]['children_angles']
                    getList.append(boneList[j]['index'])
                    boneList[i]['children_angles'] = getList
                    boneList.remove(boneList[j])
                    removeDuplicates(boneList)
        except:
            break
    return boneList


def export_object(self, context):
    bones_position = []
    bones_children = []
    faces = []
    vertices = []

    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            print("---------- ARMATURE ----------")
            bone_count = 0
            ang_bone_chk = 0
            for bone in obj.pose.bones:
                print("Exporting " + bone.name + "...")

                # Initialize bones children array
                bones_children.append([])

                # Multiply position by the world matrix
                obj_bone_matrix = obj.matrix_world @ bone.matrix
                global_location = obj_bone_matrix @ bone.location

                # Get bone head position
                temp = {
                    "index": bone_count,
                    "head": {"x": global_location[0], "y": global_location[2], "z": global_location[1]},
                    "children_angles": [bone_count]
                }
                bones_position.append(temp)

                # Check if bone has parent
                parent_count = 0
                parent_index = -1
                for b in obj.pose.bones:
                    if bone.parent == b:
                        parent_index = parent_count
                        break
                    parent_count += 1

                bones_position[bone_count]['parent'] = parent_index

                ang_indexX = bones_position[bone_count]['head']['x']
                ang_indexY = bones_position[bone_count]['head']['y']
                ang_indexZ = bones_position[bone_count]['head']['z']
                if ang_indexX == 0.0 and ang_indexY == 0.0 and ang_indexZ == 0.0 and bone_count > 0:
                    ang_bone_chk += 1

                if parent_index >= 0:
                    bones_children[parent_index].append(bone_count - ang_bone_chk)

                

                #print(bones_position[bone_count])
                #print(bones_children[parent_index])
                bone_count += 1
        
            #print(bones_position)
            #print(bones_children)
        elif obj.type == 'MESH':
            print("\n---------- MESH ----------")
            print("Exporting vertices...")
            print(len(obj.data.vertices))
            for vertex in obj.data.vertices:
                v_pos = obj.matrix_world @ vertex.co
                #v_pos[0] = v_pos[0] * -1 if v_pos[0] != 0 else 0

                v_nor = obj.matrix_world @ vertex.normal

                temp = {
                    "weight": vertex.groups[0].weight if len(vertex.groups) > 0 else 1,
                    "position": {"x": v_pos[0], "y": v_pos[2], "z": v_pos[1]},
                    "normal": {"x": v_nor[0], "y": v_nor[1], "z": v_nor[2]},
                    "texture": {"u": 0, "v": 0},
                    "bone": 0
                }

                #print(temp)
                #print(v_nor)

                vertices.append(temp)

            print("Exporting faces...")
            for loop in range(len(obj.data.loops)):
                if loop % 3 == 0:
                    if loop + 2 < len(obj.data.loops):
                        face = {"a": obj.data.loops[loop].vertex_index, "b": obj.data.loops[loop + 1].vertex_index, "c": obj.data.loops[loop + 2].vertex_index}
                        faces.append(face)

            print("Exporting vertex groups...")
            for group in obj.vertex_groups:
                vs = [v for v in obj.data.vertices if group.index in [vg.group for vg in v.groups]]
                for v in vs:
                    vertices[v.index]['bone'] = group.index

            print("Exporting UVs...")
            for face in obj.data.polygons:
                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                    uv_coords = obj.data.uv_layers.active.data[loop_idx].uv
                    uv_coords.y = 1 - uv_coords.y
                    vertices[vert_idx]["texture"] = {"u": uv_coords.x, "v": uv_coords.y}

    # Put vertices to right location
    for vertex in vertices:
        if 'bone' in vertex:
            bone = vertex['bone']

            vertex['position']['x'] = vertex['position']['x'] - bones_position[bone]['head']['x']
            vertex['position']['y'] = vertex['position']['y'] - bones_position[bone]['head']['y']
            vertex['position']['z'] = vertex['position']['z'] - bones_position[bone]['head']['z']

            vertex['position']['x'] = vertex['position']['x'] * -1 if vertex['position']['x'] != 0 else 0
    

    # Put bones head to right location
    for bone in reversed(bones_position):
        if bone['parent'] != -1:
            parent = bones_position[bone['parent']]

            bone['head']['x'] = float(bone['head']['x']) - float(parent['head']['x'])
            bone['head']['y'] = float(bone['head']['y']) - float(parent['head']['y'])
            bone['head']['z'] = float(bone['head']['z']) - float(parent['head']['z'])

            bone['head']['x'] = bone['head']['x'] * -1 if bone['head']['x'] != 0 else 0

    bones_position = removeDuplicates(bones_position)

    
    #print(bones_position)
    #print(vertices)

    with open(self.filepath, 'wb') as file:
        print("\n---------- WRITING TO FILE ----------")
        file.write("Perfect 3D Model (Ver 0.5)".encode("ascii") + b'\x00')

        print("Writing bones...")
        print(len(bones_position))
        print(len(bones_children))
        file.write(struct.pack('<B', len(bones_position)))
        file.write(struct.pack('<B', len(bones_children)))

        for bone in range(len(bones_position)):
            file.write(struct.pack('<f', bones_position[bone]['head']['x']))
            file.write(struct.pack('<f', bones_position[bone]['head']['y']))
            file.write(struct.pack('<f', bones_position[bone]['head']['z']))

            chIndex = 10
            getList = bones_position[bone]['children_angles']
            for i in getList:
                file.write(struct.pack('<B', i))
                chIndex -= 1
            
            for i in range(chIndex):
                 file.write(b'\xff')

            file.write(b'\x00\x00')  # add padding

        for x in range(len(bones_children)):
            file.write(b'\x00\x00\x00\x00')
            file.write(b'\x00\x00\x00\x00')
            file.write(b'\x00\x00\x00\x00')
            file.write(b'\x00\x00\x80\x3f')

            for _ in range(10):
                if _ < len(bones_children[x]):
                    file.write(struct.pack('<B', bones_children[x][_]))
                else:
                    file.write(b'\xff')

            file.write(struct.pack('<2x'))

        print("Writing mesh...")
        file.write(struct.pack('<H', len(vertices)))
        file.write(struct.pack('<H', len(faces)))

        file.write(struct.pack('<260x'))

        print(faces)
        print("Writing faces...")
        for x in range(len(faces)):
            file.write(struct.pack('<H', faces[x]['a']))
            file.write(struct.pack('<H', faces[x]['b']))
            file.write(struct.pack('<H', faces[x]['c']))

        print(vertices)
        print("Writing vertices...")
        for x in range(len(vertices)):
            position = vertices[x]['position']
            weight = vertices[x]['weight']
            bone = vertices[x]['bone'] + len(bones_position)
            normal = vertices[x]['normal']
            texture = vertices[x]['texture']

            file.write(struct.pack('<3f', position['x'], position['y'], position['z']))
            file.write(struct.pack('<f', weight))
            file.write(struct.pack('<B', bone))
            file.write(struct.pack('<3x'))  # padding
            file.write(struct.pack('<3f', normal['x'], normal['y'], normal['z']))
            file.write(struct.pack('<2f', texture['u'], texture['v']))

        file.close()

    return {'FINISHED'}


class ExportFile(Operator, ExportHelper):
    """Export a P3M file"""
    bl_idname = "export_model.p3m"
    bl_label = "Export P3M"
    bl_options = {'PRESET'}
    bl_description = "Exports scene to Perfect 3D Model"
    obj_name = ""

    # ExportHelper mixin class uses this
    filename_ext = ".p3m"

    filepath = bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        os.system("cls")

        if context.active_object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        export_object(self, context)
        return {'FINISHED'}


def create_menu(self, context):
    self.layout.operator(ExportFile.bl_idname, text="Perfect 3D Model (.p3m)")


def register():
    """
    Handles the registration of the Blender Addon.
    """
    bpy.utils.register_class(ExportFile)
    bpy.types.TOPBAR_MT_file_export.append(create_menu)


def unregister():
    """
    Handles the unregistering of this Blender Addon.
    """
    bpy.utils.unregister_class(ExportFile)
    bpy.types.TOPBAR_MT_file_export.remove(create_menu)


if __name__ == "__main__":
    print("Registering.")
    register()

    print("Executing.")
    bpy.ops.export_model.p3m()
