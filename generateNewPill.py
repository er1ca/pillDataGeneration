import bpy
import json
import os
import random

'''
Added Printing Apply  

'''


work_dir = os.getcwd()
print(work_dir)

def generatePill(info,pass_index):

    new_pill = bpy.data.objects[info["geometry"]["type"]].copy()
    new_pill.data = bpy.data.objects[info["geometry"]["type"]].data.copy()
    new_pill.name = info['name']
    bpy.context.scene.objects.link(new_pill)
    
    #print(len(new_pill.material_slots.items()))
    
    new_pill.hide = False
    new_pill.hide_render = False
    #new_pill.location = (random.uniform(-1,1),random.uniform(-1,1),0)
    new_pill.location = (0,0,0.8)
    
    pass_index_apply(new_pill, pass_index)
    
    bpy.context.scene.objects.active = new_pill
    bpy.ops.rigidbody.object_add()
    
    
    new_pill.scale = (info["geometry"]["size"]["x"],info["geometry"]["size"]["y"],info["geometry"]["size"]["z"])

    new_pill.active_material_index = 0    
    mat = info['material'][0]
    print(info['name'])
    bpy.data.objects[info['name']].data.materials[0] = material_apply(new_pill,mat,info)
    
    if(len(info['material'])>1):
        mat = info['material'][1]
        new_pill.active_material_index = 1        
        bpy.data.objects[info['name']].data.materials[1] = material_apply(new_pill,mat,info)

    return new_pill

def material_apply(new_pill,mat,info):
    bpy.context.scene.render.engine = 'CYCLES'
        
    shaderName = mat["type"]+'_'+info['name']
    print(shaderName)
    if (bpy.data.materials.find(shaderName)==-1):
        #print('non-exist')
        material = bpy.data.materials.new(name = shaderName)
        
        material.use_nodes = True
        material.node_tree.nodes.remove(material.node_tree.nodes.get('Diffuse BSDF'))
        material_output = material.node_tree.nodes.get('Material Output')
        principled = material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
        
        material.node_tree.links.new(material_output.inputs[0], principled.outputs[0])
    else : 
        #print('exist')
        material = bpy.data.materials[shaderName]
        
        material.use_nodes = True
        principled = bpy.data.materials[shaderName].node_tree.nodes['Principled BSDF']
    
    principled.inputs['Clearcoat Roughness'].default_value = mat["Clearcoat Roughness"]  
    principled.inputs['Sheen Tint'].default_value = mat["Sheen Tint"]
    principled.inputs['Roughness'].default_value = mat["Roughness"]

    principled.inputs['Base Color'].default_value = mat["color"]
    
    if 'Clearcoat' in mat: 
            principled.inputs['Clearcoat'].default_value = mat["Clearcoat"]
    if 'Transmission' in mat: 
            principled.inputs['Transmission'].default_value = mat["Transmission"]   
    
    if 'imprint' in mat: 
        if(material.node_tree.nodes.find('Bump') == -1) :
            imprint_apply(new_pill,info,mat,material,principled)
    if 'print' in mat:
        if(material.node_tree.nodes.find('Mix') == -1) :
            printing_apply(new_pill,info,mat,material,principled)
    
    return material

def imprint_apply(new_pill,info,mat,material,principled):
    print('--- imprint ---')
    #bump node
    bump = material.node_tree.nodes.new(type='ShaderNodeBump')
    material.node_tree.nodes['Bump'].invert = True
    material.node_tree.links.new(principled.inputs[17], bump.outputs[0])

    #invert node
    invert = material.node_tree.nodes.new(type='ShaderNodeInvert')
    material.node_tree.links.new(bump.inputs[0], invert.outputs[0])
    material.node_tree.links.new(bump.inputs[1], invert.outputs[0])
    material.node_tree.links.new(bump.inputs[2], invert.outputs[0])

    #image texture node
    image = material.node_tree.nodes.new(type='ShaderNodeTexImage')
    material.node_tree.links.new(invert.inputs[1], image.outputs[0])    

    #--> image load 
    image_file = work_dir+mat['imprint']
    if(bpy.data.images.find(image_file)==-1):
        print(image_file)
        bpy.data.images.load(image_file)
    image_name = os.path.split(image_file)[1]
    image.image = bpy.data.images.get(image_name)

    #texture coordinate node
    shaderCoord = material.node_tree.nodes.new(type='ShaderNodeTexCoord')
    material.node_tree.links.new(image.inputs[0], shaderCoord.outputs[0])
    material.node_tree.nodes['Texture Coordinate'].object = new_pill 

def printing_apply(new_pill,info,mat,material,principled):
    print('--- printing ---')

    #mixRGB node
    mixRGB = material.node_tree.nodes.new(type='ShaderNodeMixRGB')
    material.node_tree.nodes['Mix'].inputs[1].default_value = mat['color']
    material.node_tree.links.new(principled.inputs[0], mixRGB.outputs[0])
    
    #image texture node
    image = material.node_tree.nodes.new(type='ShaderNodeTexImage')
    material.node_tree.links.new(mixRGB.inputs[0],image.outputs[1])
    material.node_tree.links.new(mixRGB.inputs[2],image.outputs[0])
    
    #--> image load
    image_file = work_dir+mat['print']
    if(bpy.data.images.find(image_file)==-1):
        bpy.data.images.load(image_file)
    image_name = os.path.split(image_file)[1]
    image.image = bpy.data.images.get(image_name)

    #texture coordinate node
    shaderCoord = material.node_tree.nodes.new(type='ShaderNodeTexCoord')
    material.node_tree.links.new(image.inputs[0], shaderCoord.outputs[0])
    material.node_tree.nodes['Texture Coordinate'].object = new_pill

def pass_index_apply(pill, index):
    
    scene = bpy.data.scenes[0]
    render = scene.render
    
    pill.pass_index = index
    
    obj_mask = scene.node_tree.nodes.new('CompositorNodeIDMask')
    obj_output = scene.node_tree.nodes.new('CompositorNodeOutputFile')

    obj_mask.name = pill.name + "_mask"
    obj_mask.index = pill.pass_index

    obj_output.name = pill.name + "_output"
    obj_output.format.file_format = "PNG"
    obj_output.format.color_mode = "BW"
    obj_output.format.color_depth = '8'
    obj_output.file_slots[0].path = pill.name + "_####.png"

    scene.node_tree.links.new(obj_mask.outputs[0], obj_output.inputs[0])
    scene.node_tree.links.new(scene.node_tree.nodes['Render Layers'].outputs['IndexOB'], obj_mask.inputs[0])

if __name__ == '__main__':
    with open(work_dir+'\\pythonScript\\json\\pill_ontology_test7.json') as data_file:
    	pill_data = json.load(data_file)
    
    if (bpy.data.groups.get("PILLS_sample") == None):
        bpy.ops.group.create(name = "PILLS_sample")
    pills_sample_group = bpy.data.groups.get("PILLS_sample")
    
    if(bpy.data.groups['PILLS_sample'].objects.find('m208')==-1):
        obj_m208 = bpy.data.objects.get('m208')
        obj_m208.pass_index = 0
        pills_sample_group.objects.link(obj_m208)
    if(bpy.data.groups['PILLS_sample'].objects.find('m221')==-1):
        obj_m221 = bpy.data.objects.get('m221')
        obj_m221.pass_index = 1
        pills_sample_group.objects.link(obj_m221)
    
    num_pill = len(pills_sample_group.objects)
    
    for i in range(len(pill_data)):
        pass_index = num_pill + i
        #print(pass_index,i)
        pill = generatePill(pill_data[i],pass_index)
        pills_sample_group.objects.link(pill)
        
    
    
