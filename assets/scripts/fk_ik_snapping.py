# === DEPRECATED ===
# dev done in this script has been reused in fk / ik control
# just keeping it to have a trace of previous add-on

bl_info = {
    "name": "FK/IK Snapping for Mini Duck Legs",
    "author": "Pollen Robotics",
    "version": (1, 0),
    "blender": (4, 30, 2),
    "description": "Snap FK/IK chains for left and right legs",
    "category": "Rigging",
}

import bpy


# === CORE FUNCTIONS ===
def copy_fk_to_ik(context):
    pb = context.object.pose.bones

    for suffix in [".l", ".r"]:
        eff_ik = pb["leg_ik" + suffix]
        ik_relative_to_fk = (
            pb["knee_fk" + suffix].bone.matrix_local.inverted() @ eff_ik.bone.matrix_local
        )
        eff_ik.matrix = pb["knee_fk" + suffix].matrix @ ik_relative_to_fk
        bpy.context.view_layer.update()


def copy_ik_to_fk(context):
    pb = context.object.pose.bones

    for suffix in [".l", ".r"]:
        pb["hip_roll_fk" + suffix].matrix = pb["hip_roll_ik" + suffix].matrix.copy()
        bpy.context.view_layer.update()
        pb["hip_pitch_fk" + suffix].matrix = pb["hip_pitch_ik" + suffix].matrix.copy()
        bpy.context.view_layer.update()
        pb["knee_fk" + suffix].matrix = pb["knee_ik" + suffix].matrix.copy()
        bpy.context.view_layer.update()
        pb["ankle_fk" + suffix].matrix = pb["ankle_ik" + suffix].matrix.copy()
        bpy.context.view_layer.update()


# === BLENDER OPERATORS and PANEL ===
class SnapFKtoIK(bpy.types.Operator):
    bl_idname = "rig.snap_fk_to_ik"
    bl_label = "Snap FK to IK"
    bl_description = "Aligns the IK legs chains to match the current pose of FK legs chains"

    def execute(self, context):
        copy_fk_to_ik(context)
        self.report({"INFO"}, "Snap FK to IK")
        return {"FINISHED"}


class SnapIKtoFK(bpy.types.Operator):
    bl_idname = "rig.snap_ik_to_fk"
    bl_label = "Snap IK to FK"
    bl_description = "Aligns the FK leg chain to match the current pose of the IK legs chains"

    def execute(self, context):
        copy_ik_to_fk(context)
        self.report({"INFO"}, "Snap IK to FK")
        return {"FINISHED"}


class VIEW3D_PT_fk_ik_snapping(bpy.types.Panel):
    bl_label = "FK/IK Snapping"
    bl_idname = "VIEW3D_PT_fk_ik_snapping"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FK / Ik Snapping"

    def draw(self, context):
        layout = self.layout
        layout.operator("rig.snap_fk_to_ik")
        layout.operator("rig.snap_ik_to_fk")


# === REGISTRATION ===
classes = [
    SnapFKtoIK,
    SnapIKtoFK,
    VIEW3D_PT_fk_ik_snapping,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
