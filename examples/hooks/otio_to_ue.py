# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

"""
NOTE: This is an example `otio_ue_pre_import_item` hook, providing
      a pipeline-specific OTIO-to-UE level sequence mapping
      implementation.
"""

import opentimelineio as otio
import otio_unreal


MAIN_SEQ_PATH = "/Game/Levels/Main_SEQ.Main_SEQ"


def hook_function(in_timeline, argument_map=None):
    # The root "tracks" Stack needs to be mapped to the main level sequence
    # (containing the top-level shot track).
    if isinstance(in_timeline, otio.schema.Stack) and in_timeline.name == "tracks":
        otio_unreal.set_sub_sequence_path(in_timeline, MAIN_SEQ_PATH)

    # Clips always map to a shot track section sub-sequence
    elif isinstance(in_timeline, otio.schema.Clip):
        shot_name = in_timeline.name
        level_seq_path = (
            "/Game/Levels/shots/{shot_name}/{shot_name}.{shot_name}".format(
                shot_name=shot_name
            )
        )
        otio_unreal.set_sub_sequence_path(in_timeline, level_seq_path)
