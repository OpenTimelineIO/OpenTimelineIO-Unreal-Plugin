# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

import traceback

try:
    import otio_unreal
except ImportError:
    traceback.print_exc()
    print("Failed to import otio_unreal! Is opentimelineio on UE_PYTHONPATH?")

try:
    import otio_unreal_actions
except ImportError:
    traceback.print_exc()
    print("Failed to import otio_unreal_actions! Is PySide2 on UE_PYTHONPATH?")
