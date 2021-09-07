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
    "name": "Perfect 3D Model (.p3m) Importer",
    "author": "John Kenneth L. Andales (Raitou)",
    "description": "Imports .p3m files into Blender, including meshes and bones.",
    "blender": (2, 83, 1),
    "version": (1, 0, 0),
    "location": "File > Import > Perfect 3D Model (.p3m)",
    "warning": "",
    "category": "Import-Export"
}

import os
import struct
import bmesh
import bpy
import mathutils
from bpy.props import (BoolProperty, CollectionProperty, StringProperty)
from bpy.types import Operator, OperatorFileListElement
from bpy_extras.io_utils import ImportHelper

class ONE_TRIANGLE():
    def __init__(self, a, b, c):
        self.m_usA = a
        self.m_usB = b
        self.m_usC = c
    
    def __repr__(self):
        return "ONE_TRIANGLE({}, {}, {})".format(self.m_usA, self.m_usB, m_usC)

    def __str__(self):
        return 'ONE_TRIANGLE: \n Triangle : A: {} B: {} C: {}'.format(self.m_usA, self.m_usB, self.m_usC)
        
    @property
    def a(self):
        return self.m_usA
    
    @property
    def b(self):
        return self.m_usB
    
    @property
    def c(self):
        return self.m_usC

class SKINVERTEX():
    def __init__(self, fVectorPosX = 0.0, fVectorPosY = 0.0, fVectorPosZ = 0.0, fWeight = 0.0, ucIndex = 0, fVectorNorX = 0.0, fVectorNorY = 0.0, fVectorNorZ = 0.0, fTu = 0.0, fTv = 0.0):
        self.m_fVectorPosX = fVectorPosX
        self.m_fVectorPosY = fVectorPosY
        self.m_fVectorPosZ = fVectorPosZ
        self.m_fWeight = fWeight
        self.m_ucIndex = ucIndex
        self.m_fVectorNorX = fVectorNorX
        self.m_fVectorNorY = fVectorNorY
        self.m_fVectorNorZ = fVectorNorZ
        self.m_fTu = fTu
        self.m_fTv = fTv
    
    def __getitem__(self, index):
        if index == 0:
            return self.m_ucIndex
        else:
            return self.m_fWeight
    @property
    def fTu(self):
        return self.m_fTu
    
    @property
    def ucIndex(self):
        return self.m_ucIndex
        
    @property
    def fWeight(self):
        return self.m_fWeight
    
    @property
    def fTv(self):
        return self.m_fTv
    
    def __repr__(self):
        return "SKINVERTEX({}, {}, {}, {}, {}, {}, {}, {}, {}, {})".format(self.m_fVectorPosX, self.m_fVectorPosY, self.m_fVectorPosZ, self.m_fWeight, self.m_ucIndex, self.m_fVectorNorX, self.m_fVectorNorY, self.m_fVectorNorZ, self.m_fTu, self.m_fTv)

    def __str__(self):
        return 'SKINVERTEX: \n VectorPos (X, Y, Z): {} {} {}\n Weight: {}\n Index: {}\n VectorNor (X, Y, Z): {} {} {}\n fTu: {}\n fTv: {}'.format(self.m_fVectorPosX, self.m_fVectorPosY, self.m_fVectorPosZ, self.m_fWeight, self.m_ucIndex, self.m_fVectorNorX, self.m_fVectorNorY, self.m_fVectorNorZ, self.m_fTu, self.m_fTv)

class AngleBoneFromFile():
    def __init__(self, fVectorX = 0.0, fVectorY = 0.0, fVectorZ = 0.0, fScale = 0.0, aucChildIndex = None):
        self.m_fVectorX = fVectorX
        self.m_fVectorY = fVectorY
        self.m_fVectorZ = fVectorZ
        self.m_fScale = fScale
        self.m_aucChildIndex = aucChildIndex
        
    def __repr__(self):
        return "AngleBoneFromFile({}, {}, {}, {}. {})".format(self.m_fVectorX, self.m_fVectorY, self.m_fVectorZ, self.m_fScale, self.m_aucChildIndex)

    def __str__(self):
        return 'AngleBoneFromFile: \n Vector (X, Y, Z, Scale): {} {} {} {}\n ChildIndex : {}'.format(self.m_fVectorX, self.m_fVectorY, self.m_fVectorZ, self.m_fScale, self.m_aucChildIndex)
        
    @property
    def aucChildIndex(self):
        return self.m_aucChildIndex

class PositionBone():
    def __init__(self, fVectorX = 0.0, fVectorY = 0.0, fVectorZ = 0.0, aucChildIndex = None):
        self.m_fVectorX = fVectorX
        self.m_fVectorY = fVectorY
        self.m_fVectorZ = fVectorZ
        self.m_aucChildIndex = aucChildIndex
        
    def __repr__(self):
        return "PositionBone({}, {}, {}, {})".format(self.m_fVectorX, self.m_fVectorY, self.m_fVectorZ, self.m_aucChildIndex)

    def __str__(self):
        return 'PositionBone: \n Vector (X, Y, Z): {} {} {}\n ChildIndex : {}'.format(self.m_fVectorX, self.m_fVectorY, self.m_fVectorZ, self.m_aucChildIndex)
        
    @property
    def aucChildIndex(self):
        return self.m_aucChildIndex    
        
    @property
    def fVectorX(self):
        return self.m_fVectorX    
        
    @property
    def fVectorY(self):
        return self.m_fVectorY    
        
    @property
    def fVectorZ(self):
        return self.m_fVectorZ    
    

def import_p3m(context, strFilepath, hide_unused_bones):
    strModelName = bpy.path.basename(strFilepath)    
    
    print("\n\nImporting P3M file {}\n\n".format(strModelName))
    
    strModelName = os.path.splitext(strModelName)[0]
    
    iFile = open(strFilepath, 'rb')
    
    buffStrP3MVer = iFile.read(26)
    strP3MVer, = struct.unpack('<26s', buffStrP3MVer) # read P3M Version
    
    iFile.read(1); # skip padding 
    
    print("{}\n".format(strP3MVer))
    
    buff = iFile.read(2)
    dwNumPositionBone, dwNumAngleBone = struct.unpack('<2B', buff)
    pPositionBone = []
    print(" NumPositionBone: {0}\n NumAngleBone: {1}".format(dwNumPositionBone, dwNumAngleBone))
    
    print("\n\nReading pPositionBone:")
    for i in range(dwNumPositionBone):
        buff = iFile.read(12) # 3 Float Size = 12
        fVectorX, fVectorY, fVectorZ = struct.unpack('<3f',buff) 
        
        aucChildIndex = []  
        for j in range(10): # KSafeArray<unsigned char,10> acChildIndex
            ChildIndex, = struct.unpack('<B',iFile.read(1))
            if ChildIndex != 255:
                aucChildIndex.insert(j, ChildIndex)   
        
        pPositionBone_ = PositionBone(fVectorX, fVectorY, fVectorZ, aucChildIndex)
        print( "Index {}:\n{}".format(i, str(pPositionBone_)))
        pPositionBone.insert(i, pPositionBone_)
        iFile.read(2) #Struct Padding
    
    armature = bpy.data.armatures.new('Armature') 
    armature_object = bpy.data.objects.new("%s_armature" % strModelName, armature)

    bpy.context.collection.objects.link(armature_object)
    context.view_layer.objects.active = armature_object
    
    bpy.ops.object.mode_set(mode='EDIT')
    
    pAngleBone = []
    print("\n\nReading pAngleBone:")   
    for i in range(dwNumAngleBone):
        buff = iFile.read(16) # 4 Float Size = 16
        fVectorX, fVectorY, fVectorZ, fScale = struct.unpack('<4f',buff) 
        
        joint = armature.edit_bones.new("bone_%d" % i)
        for j in range(dwNumPositionBone):
            for x in pPositionBone[j].aucChildIndex:
                if i == x:
                    vectorPos = (pPositionBone[j].fVectorX, pPositionBone[j].fVectorY, pPositionBone[j].fVectorZ)
                    print(" X: {}\n Y: {}\n Z: {}".format(pPositionBone[j].fVectorX, pPositionBone[j].fVectorY, pPositionBone[j].fVectorZ))
                    joint.head = mathutils.Vector(vectorPos)
                    joint.tail = mathutils.Vector(vectorPos)
        
        aucChildIndex = []
        for j in range(10): # KSafeArray<unsigned char,10> acChildIndex
            ChildIndex, = struct.unpack('<B',iFile.read(1))
            if ChildIndex != 255:
                aucChildIndex.insert(j, ChildIndex)
        
        pAngleBone_ = AngleBoneFromFile(fVectorX, fVectorY, fVectorZ, fScale, aucChildIndex)
        print( "Index {}:\n{}".format(i, str(pAngleBone_)))
        pAngleBone.insert(i, pAngleBone_)
        iFile.read(2) #Struct Padding
    
    for i in range(dwNumAngleBone):
        chIndex = []
        for posTree in pAngleBone[i].aucChildIndex:
            for angTree in pPositionBone[posTree].aucChildIndex:
                chIndex.append(angTree)
                print("pos : {} ang {}".format(posTree, angTree))
        print(len(chIndex))
        if len(chIndex) != 1:
            current = armature.edit_bones[i]
            parent = current.parent

            if parent != None:
                v = (parent.tail - parent.head).normalized() * 0.05
            else:
                v = mathutils.Vector((0, 0.05, 0))

            current.tail = current.head + v
        print(chIndex)
        for idx in chIndex:
            current = armature.edit_bones[i]
            child = armature.edit_bones[idx]

            child.parent = current
            child.head = child.parent.head + child.head

            if len(chIndex) == 1:
                current.tail = child.head
        
    buff = iFile.read(4)
    dwNumVertex, dwNumFace = struct.unpack('<2H', buff)
    print(" NumVertex: {0}\n NumFace: {1}".format(dwNumVertex, dwNumFace))
    
    iFile.read(260) #skips reading texture
        
    vecIndex = []
    print("\n\nReading Triangle Vertices:")   
    for i in range(dwNumFace):
        triangleBuff = iFile.read(6)
        a, b, c = struct.unpack('<3H', triangleBuff)
        triangle = ONE_TRIANGLE(a, b, c)
        print( "Index {}:\n{}".format(i, str(triangle)))
        vecIndex.append(triangle)
        
    bm = bmesh.new()
    mesh = bpy.data.meshes.new("%s_mesh" % strModelName)   
     
    vecVertex = []
    print("\n\nReading Skin Vertices:")
    
    for i in range(dwNumVertex):
        buff = iFile.read(16) # 4 Float Size = 16
        fVectorPosX, fVectorPosY, fVectorPosZ, fWeight = struct.unpack('<4f',buff)
        
        aucIndex = []
        buff = iFile.read(1)
        ucIndex, = struct.unpack('<B', buff)
        if ucIndex != 255:
            ucIndex = ucIndex - dwNumPositionBone
            
            fVectorPosX += armature.edit_bones[ucIndex].head[0]
            fVectorPosY += armature.edit_bones[ucIndex].head[1]
            fVectorPosZ += armature.edit_bones[ucIndex].head[2]
            
        iFile.read(3) #padding
                    
        buff = iFile.read(20) # 5 Float Size = 20
        fVectorNorX, fVectorNorY, fVectorNorZ, fTu, fTv = struct.unpack('<5f', buff)
        
        #DirectX to OpenGL UV Mapping
        fTv = 1 - fTv
        
        vecVertex_ = SKINVERTEX(fVectorPosX, fVectorPosY, fVectorPosZ, fWeight, ucIndex, fVectorNorX, fVectorNorY, fVectorNorZ, fTu, fTv)
        
        

        vertex = bm.verts.new((fVectorPosX, fVectorPosY, fVectorPosZ))

        vertex.normal = mathutils.Vector((fVectorNorX, fVectorNorY, fVectorNorZ))
        print(vertex.normal)
        print( "Index {}:\n{}".format(i, str(vecVertex_)))
        vecVertex.insert(i, vecVertex_)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    
    uv_layer = bm.loops.layers.uv.verify()

    for vecInd in vecIndex:
        a = bm.verts[vecInd.a]
        b = bm.verts[vecInd.b]
        c = bm.verts[vecInd.c]

        try:
            face = bm.faces.new((a, b, c))
        except:
            pass

        for vert, loop in zip(face.verts, face.loops):
            tu = vecVertex[vert.index].fTu
            tv = vecVertex[vert.index].fTv

            loop[uv_layer].uv = (tu, tv)

    bm.to_mesh(mesh)
    bm.free()
    
    mesh_object = bpy.data.objects.new("%s_mesh" % strModelName, mesh)

    print("\n\nRendering Vertices")

    for x in range(dwNumAngleBone):
        mesh_object.vertex_groups.new(name="bone_%d" % x)

    for i in range(len(vecVertex)):
        if vecVertex[i].ucIndex != 255:
            ucIndex = vecVertex[i].ucIndex
            fWeight = vecVertex[i].fWeight
            mesh_object.vertex_groups[ucIndex].add([i], fWeight, "REPLACE")

    if hide_unused_bones:
        print("Hiding unused bones...")

        for bone in armature.edit_bones:
            if not bone.children:
                for b in [bone, *bone.parent_recursive]:
                    bone_group = int(b.name.split('_')[-1])

                    # if all the bone's children are hidden and there are no vertices influenced by the bone
                    if not False in [c.hide for c in b.children] and not any([v for v in mesh.vertices if bone_group in [g.group for g in v.groups]]):
                        b.hide = True
                    else:
                        break

        for x in range(len(armature.edit_bones)):
            bone = armature.edit_bones[x]

            if bone.hide:
                bone.select = True

                bpy.ops.object.mode_set(mode='POSE')
                bpy.ops.pose.hide()
                bpy.ops.object.mode_set(mode='EDIT')

    # corrects orientation
    correct_orientation = mathutils.Matrix([[-1.0, 0.0, 0.0, 0.0],
                                            [0.0, 0.0, 1.0, 0.0],
                                            [0.0, 1.0, 0.0, 0.0],
                                            [0.0, 0.0, 0.0, 1.0]])
    
    armature.transform(correct_orientation)
    mesh.transform(correct_orientation)

    bpy.ops.object.mode_set(mode='OBJECT')
    mesh_object.parent = armature_object
    modifier = mesh_object.modifiers.new(type='ARMATURE', name="Armature")
    modifier.object = armature_object

    bpy.context.collection.objects.link(mesh_object)
    context.view_layer.objects.active = mesh_object
    #finish 7-7-2020
    
    
    

class ImportFile(Operator, ImportHelper):
    """Import a P3M file"""
    bl_idname = "import_model.p3m"
    bl_label = "Import P3M"

    filename_ext = ".p3m"

    filter_glob: StringProperty(
        default="*.p3m",
        options={'HIDDEN'},
        maxlen=255,
    )

    files: CollectionProperty(
        name="P3M files",
        type=OperatorFileListElement,
    )

    hide_unused_bones: BoolProperty(
        name="Hide unused bones",
        description="Hides all the bones that do not influence the mesh. They will still be accessible through the object hierarchy panel and can be selected with the Select Box Tool in the pose mode",
        default=False,
    )

    directory = StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        for file in self.files:
            strFilepath = os.path.join(self.directory, file.name)
            import_p3m(context, strFilepath, self.hide_unused_bones)

        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(ImportFile.bl_idname, text="Perfect 3D Model (.p3m)")


def register():
    bpy.utils.register_class(ImportFile)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportFile)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
    bpy.ops.import_model.p3m('INVOKE_DEFAULT')
