import bpy
import numpy as np
import json
import os

from datetime import datetime


def update_connection(self, context):
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


class DataRecorder:
    def __init__(self, fps=50):
        self.fps = fps
        self.target_frame_time = 1.0 / fps
        self.pose = bpy.data.objects["Armature"].pose

        self.prev_root_pos = self.get_root_position()
        self.prev_root_orientation_quat = self.get_root_orientation(return_quat=True)
        self.prev_root_orientation_euler = self.get_root_orientation(return_quat=False)
        self.prev_joints_positions = self.get_joints_positions()
        self.prev_left_toe_pos = self.get_toe_position("left")
        self.prev_right_toe_pos = self.get_toe_position("right")

        self.episode = {
            "LoopMode": "Wrap",
            "FPS": self.fps,
            "EnableCycleOffsetPosition": True,
            "EnableCycleOffsetRotation": False,
            "Joints": [],
            "Vel_x": [],
            "Vel_y": [],
            "Yaw": [],
            "Placo": [],
            "Frame_offset": [],
            "Frame_size": [],
            "Frames": [],
            "MotionWeight": 1,
        }

    def blender_frame_to_robot_frame(self, x: float, y: float, z: float):
        return [-y, x, z]

    def euler_to_quaternion(self, yaw, pitch, roll):
        cy, sy = np.cos(yaw * 0.5), np.sin(yaw * 0.5)
        cp, sp = np.cos(pitch * 0.5), np.sin(pitch * 0.5)
        cr, sr = np.cos(roll * 0.5), np.sin(roll * 0.5)

        return np.array(
            [
                sr * cp * cy - cr * sp * sy,  # x
                cr * sp * cy + sr * cp * sy,  # y
                cr * cp * sy - sr * sp * cy,  # z
                cr * cp * cy + sr * sp * sy,  # w
            ]
        )

    def get_root_position(self):
        x_root_frame, y_root_frame, z_root_frame = self.pose.bones["root"].location
        x_blender_frame = -x_root_frame
        y_blender_frame = z_root_frame
        z_blender_frame = y_root_frame
        return self.blender_frame_to_robot_frame(
            x_blender_frame, y_blender_frame, z_blender_frame
        )

    def get_root_orientation(self, return_quat=True):
        roll_root_frame, pitch_root_frame, yaw_root_frame = self.pose.bones[
            "root"
        ].rotation_euler
        roll_blender_frame = -roll_root_frame
        pitch_blender_frame = pitch_root_frame
        yaw_blender_frame = yaw_root_frame

        if not return_quat:
            return [roll_blender_frame, pitch_blender_frame, yaw_blender_frame]

        return self.euler_to_quaternion(
            yaw_blender_frame, pitch_blender_frame, roll_blender_frame
        )

    def get_joints_positions(self):
        # Return joints positions in radians
        # Offset have been applied in the Blender model to have the legs bending a bit in rest pose
        # -10 degrees on knee bones
        # +10 degrees on ankle bones
        return [
            self.pose.bones["hip_yaw_fk.l"].rotation_euler[1],
            self.pose.bones["hip_roll_fk.l"].rotation_euler[2],
            self.pose.bones["hip_pitch_fk.l"].rotation_euler[0],
            self.pose.bones["knee_fk.l"].rotation_euler[0] - np.deg2rad(10),
            self.pose.bones["ankle_fk.l"].rotation_euler[0] + np.deg2rad(10),
            self.pose.bones["neck_pitch"].rotation_euler[0],
            self.pose.bones["head_pitch"].rotation_euler[0],
            self.pose.bones["head_yaw"].rotation_euler[2],
            self.pose.bones["head_roll"].rotation_euler[2],
            self.pose.bones["antenna.r"].rotation_euler[2],
            self.pose.bones["antenna.l"].rotation_euler[2],
            self.pose.bones["hip_yaw_fk.r"].rotation_euler[1],
            self.pose.bones["hip_roll_fk.r"].rotation_euler[2],
            self.pose.bones["hip_pitch_fk.r"].rotation_euler[0],
            self.pose.bones["knee_fk.r"].rotation_euler[0] - np.deg2rad(10),
            self.pose.bones["ankle_fk.r"].rotation_euler[0] + np.deg2rad(10),
        ]

    def get_toe_position(self, side: str):
        matrix_world = bpy.data.objects["Armature"].matrix_world
        toe_matrix_world = matrix_world @ self.pose.bones[f"toe.{side[0]}"].matrix
        root_matrix_world = matrix_world @ self.pose.bones["root"].matrix

        return toe_matrix_world.translation - root_matrix_world.translation

    def compute_velocity(self, prev_state, curr_state):
        return [
            (curr - prev) / self.target_frame_time
            for curr, prev in zip(curr_state, prev_state)
        ]

    def update_frame(self):
        root_position = self.get_root_position()
        root_orientation_quat = self.get_root_orientation()
        root_orientation_euler = self.get_root_orientation(return_quat=False)
        joints_positions = self.get_joints_positions()
        left_toe_pos = self.get_toe_position("left")
        right_toe_pos = self.get_toe_position("right")

        world_linear_vel = self.compute_velocity(self.prev_root_pos, root_position)
        world_angular_vel = self.compute_velocity(
            self.prev_root_orientation_euler, root_orientation_euler
        )
        joints_vel = self.compute_velocity(self.prev_joints_positions, joints_positions)
        left_toe_vel = self.compute_velocity(self.prev_left_toe_pos, left_toe_pos)
        right_toe_vel = self.compute_velocity(self.prev_right_toe_pos, right_toe_pos)

        frame_data = {
            "root_position": root_position,
            "root_orientation_quat": root_orientation_quat.tolist(),
            "joints_positions": joints_positions,
            "left_toe_pos": list(left_toe_pos),
            "right_toe_pos": list(right_toe_pos),
            "world_linear_vel": world_linear_vel,
            "world_angular_vel": world_angular_vel,
            "joints_vel": joints_vel,
            "left_toe_vel": list(left_toe_vel),
            "right_toe_vel": list(right_toe_vel),
            "foot_contact": [1, 1],  # for now we don't compute foot contact
        }

        self.episode["Frames"].append(
            [value for measure in (list(frame_data.values())) for value in measure]
        )

        self.prev_root_pos = root_position
        self.prev_root_orientation_quat = root_orientation_quat
        self.prev_root_orientation_euler = root_orientation_euler
        self.prev_joints_positions = joints_positions
        self.prev_left_toe_pos = left_toe_pos
        self.prev_right_toe_pos = right_toe_pos

    def save_to_json(self, filename_prefix="animation_data_"):
        # Save animation recording in json file
        # By default, recording are stored in a folder "duck_mini_data_records" at the root of the Blender folder
        # Recordings are timestamped

        if not os.path.exists("duck_mini_data_records"):
            os.makedirs("duck_mini_data_records")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(
            f"duck_mini_data_records/{filename_prefix}{timestamp}.json", "w"
        ) as f:
            json.dump(self.episode, f, indent=4)
        print(f"Saving json file {filename_prefix}{timestamp}.json")


class StartRecordingOperator(bpy.types.Operator):
    bl_idname = "wm.start_recording"
    bl_label = "Start Operator"

    def execute(self, context):
        context.scene.is_recording = True
        first_frame = bpy.context.scene.frame_start

        # Start animation at first frame
        # Make sure that the animation is stopped when starting the recording
        bpy.context.scene.frame_set(first_frame)
        bpy.ops.screen.animation_play()  # TODO: check if animation is already running
        print("Start recording animation")
        bpy.app.timers.register(update_frame)
        return {"FINISHED"}


class AnimationPanel(bpy.types.Panel):
    bl_category = "Data Recording"
    bl_label = "Data Recording"

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.enabled = not scene.is_recording
        row.operator("wm.start_recording", text="Start Recording")


def update_frame():
    global animator

    if (
        bpy.context.scene.frame_current == bpy.context.scene.frame_end
    ):  # if last animation frame is reached, stop recording
        print("Stopping animation recording")
        bpy.context.scene.is_recording = False
        animator.save_to_json()
        bpy.ops.screen.animation_play()
        return None

    animator.update_frame()
    return 1.0 / FPS


def register():
    classes = [
        StartRecordingOperator,
        AnimationPanel,
    ]
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.types.Scene.is_recording = bpy.props.BoolProperty(
        name="Is Recording", default=False, update=update_connection
    )


def unregister():
    bpy.utils.unregister_class(AnimationPanel)


if __name__ == "__main__":
    FPS = 50
    animator = DataRecorder(fps=FPS)
    register()
