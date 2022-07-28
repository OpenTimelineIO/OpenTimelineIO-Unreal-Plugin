# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

"""
NOTE: This is an example `otio_ue_post_export_clip` hook, providing
      a pipeline-specific UE-to-OTIO media reference mapping
      implementation.
"""

import os

import unreal
import opentimelineio as otio
import otio_unreal


def hook_function(in_timeline, argument_map=None):
    # Get level sequence path from clip (in_timeline is a Clip here)
    level_seq_path = otio_unreal.get_sub_sequence_path(in_timeline)
    if level_seq_path is not None:
        # Get output path components
        shot_name = os.path.splitext(os.path.basename(level_seq_path))[0]
        render_dir = os.path.realpath(
            os.path.join(unreal.Paths.project_saved_dir(), "MovieRenders", shot_name)
        )
        # Get available_range, which is the sub-sequence's playback range
        available_range = in_timeline.media_reference.available_range

        # Setup anticipated MRQ output image sequence reference
        media_ref = otio.schema.ImageSequenceReference(
            target_url_base=render_dir.replace("\\", "/"),
            name_prefix=shot_name + ".",
            name_suffix=".png",
            start_frame=available_range.start_time.to_frames(),
            frame_step=1,
            rate=available_range.start_time.rate,
            frame_zero_padding=4,
            available_range=available_range,
        )
        in_timeline.media_reference = media_ref
