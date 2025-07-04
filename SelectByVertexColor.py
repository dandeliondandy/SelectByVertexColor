bl_info = {
    "name": "Select by Vertex Color (v2)",
    "author": "Cody Swanson",
    "version": (2, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar (N-Key) > VColor Select Tab",
    "description": "Selects faces by vertex color using a robust 'Get from Active' workflow.",
    "warning": "",
    "doc_url": "",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector

# --- Property Group to store settings ---
class VColorSelectProperties(bpy.types.PropertyGroup):
    target_color: bpy.props.FloatVectorProperty(
        name="Target Color", subtype='COLOR', default=(1.0, 1.0, 1.0),
        min=0.0, max=1.0, description="The color to select. Use 'Get from Active' to set this accurately."
    )
    threshold: bpy.props.FloatProperty(
        name="Threshold", default=0.01, min=0.0, max=1.732,
        description="Tolerance for color matching. A small value should now work."
    )
    match_mode: bpy.props.EnumProperty(
        name="Match Mode",
        items=[('ALL', "All Vertices", "Select if ALL vertices match"),
               ('ANY', "Any Vertex", "Select if ANY vertex matches")],
        default='ALL'
    )
    select_mode: bpy.props.EnumProperty(
        name="Select Mode",
        items=[('REPLACE', "Replace", "Replace current selection"),
               ('ADD', "Add", "Add to current selection")],
        default='REPLACE'
    )

# --- NEW OPERATOR: Get Color from Active Face ---
class MESH_OT_get_color_from_active(bpy.types.Operator):
    """Sets the Target Color from the average color of the active face."""
    bl_idname = "mesh.get_color_from_active"
    bl_label = "Get Color from Active Face"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Can only run if we have an active mesh object in edit mode
        obj = context.active_object
        return (obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH')

    def execute(self, context):
        props = context.scene.vcolor_select_props
        bm = bmesh.from_edit_mesh(context.active_object.data)
        
        color_layer = bm.loops.layers.color.active
        if not color_layer:
            self.report({'ERROR'}, "No active vertex color layer found.")
            return {'CANCELLED'}
        
        active_face = bm.faces.active
        if not active_face:
            self.report({'ERROR'}, "No active face selected. Please select one face.")
            return {'CANCELLED'}
            
        # Calculate the average color of the face's vertices
        avg_color = Vector((0.0, 0.0, 0.0))
        num_loops = len(active_face.loops)
        if num_loops == 0:
            return {'CANCELLED'}
            
        for loop in active_face.loops:
            # Add up the RGB components (slicing off alpha)
            avg_color += Vector(loop[color_layer][:3])
        
        avg_color /= num_loops
        
        # Set the target color and report success
        props.target_color = avg_color
        self.report({'INFO'}, f"Set target color to average: {avg_color[:3]}")
        
        return {'FINISHED'}


# --- The main selection Operator ---
class MESH_OT_select_by_vertex_color(bpy.types.Operator):
    """Select faces based on vertex color"""
    bl_idname = "mesh.select_by_vertex_color"
    bl_label = "Select Faces by Color"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and context.active_object.type == 'MESH' and context.mode == 'EDIT_MESH')

    def execute(self, context):
        props = context.scene.vcolor_select_props
        target_color = Vector(props.target_color)

        bm = bmesh.from_edit_mesh(context.active_object.data)
        color_layer = bm.loops.layers.color.active
        if not color_layer:
            self.report({'ERROR'}, "No active vertex color layer found.")
            return {'CANCELLED'}

        if props.select_mode == 'REPLACE':
            bpy.ops.mesh.select_all(action='DESELECT')

        threshold_sq = props.threshold * props.threshold
        
        for face in bm.faces:
            match_count = 0
            for loop in face.loops:
                loop_color = Vector(loop[color_layer][:3])
                distance_sq = (loop_color - target_color).length_squared
                if distance_sq <= threshold_sq:
                    match_count += 1
            
            should_select = False
            if props.match_mode == 'ALL' and match_count == len(face.loops):
                should_select = True
            elif props.match_mode == 'ANY' and match_count > 0:
                should_select = True

            if should_select:
                face.select = True

        bmesh.update_edit_mesh(context.active_object.data)
        return {'FINISHED'}


# --- The UI Panel ---
class MESH_PT_select_by_vertex_color_panel(bpy.types.Panel):
    bl_label = "Select by Vertex Color"
    bl_idname = "MESH_PT_select_by_vcolor_v2"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Select by Vertex Color'

    def draw(self, context):
        layout = self.layout
        props = context.scene.vcolor_select_props
        
        box = layout.box()
        main_col = box.column()
        
        # Color property and new button side-by-side
        split = main_col.split(factor=0.75, align=True)
        split.prop(props, "target_color", text="")
        split.operator(MESH_OT_get_color_from_active.bl_idname, text="", icon='EYEDROPPER')

        main_col.prop(props, "threshold")
        
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Match Mode:")
        col.prop(props, "match_mode", expand=True)
        col.label(text="Selection:")
        col.prop(props, "select_mode", expand=True)

        layout.operator(MESH_OT_select_by_vertex_color.bl_idname, text="Select Faces", icon='RESTRICT_SELECT_OFF')


# --- Registration ---
classes = (
    VColorSelectProperties,
    MESH_OT_get_color_from_active,
    MESH_OT_select_by_vertex_color,
    MESH_PT_select_by_vertex_color_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.vcolor_select_props = bpy.props.PointerProperty(type=VColorSelectProperties)

def unregister():
    del bpy.types.Scene.vcolor_select_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()