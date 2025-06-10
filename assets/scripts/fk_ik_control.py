import bpy

# === CONFIG ===
CONTROLLER_BONE_NAME = "fk_ik_controller"
PROP_NAME = "fk_ik"  # custom property name that controls FK/IK switch


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


# === OPERATORS ===
class SwitchToIK(bpy.types.Operator):
    bl_idname = "rig.switch_to_ik"
    bl_label = "Switch to IK"
    bl_description = "Snap FK to IK and switch control mode to IK"

    def execute(self, context):
        armature = context.object
        pb = armature.pose.bones
        pb[CONTROLLER_BONE_NAME][PROP_NAME] = 1.0
        bpy.context.view_layer.update()
        self.report({"INFO"}, "Switched to IK")
        copy_fk_to_ik(context)
        return {"FINISHED"}


class SwitchToFK(bpy.types.Operator):
    bl_idname = "rig.switch_to_fk"
    bl_label = "Switch to FK"
    bl_description = "Snap IK to FK and switch control mode to FK"

    def execute(self, context):
        armature = context.object
        pb = armature.pose.bones
        pb[CONTROLLER_BONE_NAME][PROP_NAME] = 0.0
        bpy.context.view_layer.update()
        self.report({"INFO"}, "Switched to FK")
        copy_ik_to_fk(context)
        return {"FINISHED"}


# === UI PANEL ===
class VIEW3D_PT_fk_ik_toggle_snapping(bpy.types.Panel):
    bl_label = "FK/IK Control"
    bl_idname = "VIEW3D_PT_fk_ik_toggle_snapping"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FK / IK Control"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Switch control mode:")

        armature = context.object
        pb = armature.pose.bones
        prop_value = pb[CONTROLLER_BONE_NAME].get(PROP_NAME, None)

        row = layout.row()
        row.enabled = prop_value != 0.0
        row.operator("rig.switch_to_fk", icon="HAND")

        row = layout.row()
        row.enabled = prop_value != 1.0
        row.operator("rig.switch_to_ik", icon="CONSTRAINT_BONE")


# === REGISTER ===
classes = [
    SwitchToIK,
    SwitchToFK,
    VIEW3D_PT_fk_ik_toggle_snapping,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
