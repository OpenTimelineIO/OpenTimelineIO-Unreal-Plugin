# OpenTimelineIO-Unreal-Plugin

This `OpenTimelineIOUtilities` plugin for Unreal Engine provides a 
configurable framework and actions for mapping between an OpenTimelineIO 
timeline and a UE level sequence hierarchy.

In the context of this plugin, OTIO stacks and clips map to level sequences;
stacks being interpreted as sequences containing shot tracks, and clips as
individual shot sections and their referenced sub-sequences. This approach
supports arbitrarily nested (or flat) Sequencer pipelines in UE, and leans on
implementation-defined hooks as a translation layer.

When importing a timeline, if a referenced level sequence does not yet exist,
it will be created at the configured path prior to adding it as a sub-sequence.
This capability enables some very useful automation workflows, supporting
simultaneous timeline syncing and setup of shot scaffolding.

The plugin can also register a UE Factory (import mechanism) and Exporter 
(export mechanism) to add support for importing any OTIO-supported file format 
into a level sequence hierarchy, and exporting a level sequence hierarchy to 
one OTIO-supported file format (*.otio by default), through standard Unreal 
import/export interfaces. In many cases though, implementors will want to use 
the `otio_unreal` Python package to directly integrate these interfaces into 
pipeline-specific workflows.

In addition to these lower level components, the plugin provides a collection 
of high level actions with graphical interfaces for previewing (through an 
embedded `opentimelineview` instance) import and export results prior to making 
changes to the Unreal project or committing timeline data to disk. These 
actions serve both as intuitive tools for accelerating pipeline UX, as well as 
example code for exploring other integrations.

**NOTE**

This plugin's import function wraps all Unreal Editor changes in a
`ScopedEditorTransaction`, making the operation revertible with a single
`Undo` action.

## Feature Matrix

This table outlines OTIO features which are currently supported by this plugin.
For unsupported features, contributions are welcome.

| Feature                  | Supported |
|--------------------------| --------- |
| Single Track of Clips    |     ✔     |
| Multiple Video Tracks    |     ✔     |
| Audio Tracks & Clips     |     ✖     |
| Gap/Filler               |     ✔     |
| Markers                  |     ✔     |
| Nesting                  |     ✔     |
| Transitions              |     ✖     |
| Audio/Video Effects      |     ✖     |
| Linear Speed Effects     |     ✔     |
| Fancy Speed Effects      |     ✖     |
| Color Decision List      |     ✖     |
| Image Sequence Reference |     ✖     |

## Install

This plugin requires that the Python packages referenced in `requirements.txt`
are installed to a location on the `UE_PYTHONPATH` environment variable. See 
the [Scripting the Unreal Editor Using Python](https://docs.unrealengine.com/5.0/en-US/scripting-the-unreal-editor-using-python/) 
docs for more info.

Once these dependencies are available to Unreal's Python environment, there are 
two options for installing the plugin:

### Unreal Engine Plugin

To add the `OpenTimelineIOUtilities` plugin to a UE project, move its directory 
to one of the two Unreal plugin search paths:

- Engine: `/<UE Root>/Engine/Plugins`
- Game: `/<Project Root>/Plugins`

To make the plugin fully self-contained, you can install Python package 
dependencies to one or more platform-specific package directories within the 
plugin's `Content` directory structure: 
`OpenTimelineIOUtilities/Content/Python/Lib/[Win64|Linux|Mac]/site-packages/`

After an Unreal Editor restart the `OpenTimelineIO (OTIO) Utilities` plugin can 
be enabled in the UE `Plugins` dialog. Following another restart, all plugin
functionality and Python packages will be available in Unreal Editor.

### Python Only

To make this plugin available in Unreal Editor without installing it as a UE
plugin, simply add the directory containing `init_unreal.py` (and the 
`otio_unreal` and `otio_unreal_actions` Python packages) to the `UE_PYTHONPATH` 
environment variable. UE will run `init_unreal.py` on startup to register the 
import and export interfaces, and make these packages available in Unreal's 
Python environment. Alternatively these same paths can be added to the `Python` 
plugin `Additional Paths` property in UE project settings.

## Actions

When PySide2 is available in the Python environment, two actions with user 
interfaces are added to a new `OPENTIMELINEIO` section of these Unreal Editor 
menus:

- Level Sequence menu above the viewport (slate/clapperboard icon).
- Level Sequence context menu (right-click a Level Sequence asset in the Content 
  Browser).

These actions must be triggered after a level sequence is loaded into 
Sequencer. This should usually be the main sequence under which all 
sequences and shots are organized so that imported and exported timelines will
reflect this structure recursively.

### Export Sequence to OTIO...

This tool will preview and export the current level sequence (loaded in 
Sequencer) to any OTIO-supported timeline format.

To use: launch the dialog, update the default timeline file path to the target 
file, and click `OK` to export. Registered export hooks will be called to 
finalize the timeline data (setting media references, etc.).

### Update Sequence from OTIO...

This tool will preview and update the current level sequence (loaded in 
Sequencer) from any OTIO-supported timeline format. While a top-level sequence
must exist prior to running this tool, sub-sequences will be created and 
referenced into a shot track where they did not exist previously. Existing 
sub-sequences and shot track sections will be updated to match the imported
timeline. 

To use: launch the dialog, update the default timeline file path to the file to 
import, and click `OK` to commit changes to the sequence hierarchy. In the 
dialog's level sequence tree, the `Status` column indicates which sequences 
will be updated (edit icon) or created (plus icon) when accepting the changes.

**NOTE**

A single `Undo` action will revert the committed changes, restoring the 
original sequence hierarchy and asset state.

## Hooks

This plugin supports several custom OTIO hooks for implementing
pipeline-specific mapping between timelines and level sequences. Unless the
required `unreal` metadata is written to a timeline prior to import, at least
one import hook is required to successfully import a timeline. No hooks are
required to export a timeline, but can be used to setup media references
for rendered outputs.

| Hook                     | Stage  | Description                                                                                                                                                                                                 |
|--------------------------| ------ |-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| otio_ue_pre_import       | Import | Called to modify or replace a timeline prior to creating or updating a level sequence hierarchy during an OTIO import: <br/>`hook_function :: otio.schema.Timeline, Optional[Dict] => otio.schema.Timeline` |
| otio_ue_pre_import_item  | Import | Called to modify a stack or clip in-place prior to using it to update a level sequence or shot section during an OTIO import: <br/>`hook_function :: otio.schema.Item, Optional[Dict] => None`              |
| otio_ue_post_export      | Export | Called to modify or replace a timeline following an OTIO export from a level sequence hierarchy: <br/>`hook_function :: otio.schema.Timeline, Optional[Dict] => otio.schema.Timeline`                       |
| otio_ue_post_export_clip | Export | Called to modify a clip in-place following it being created from a shot section during an OTIO export: <br/>`hook_function :: otio.schema.Clip, Optional[Dict] => None`                                     |

The primary goal of the import hooks are to add the following metadata to each
stack and clip in the timeline which should map to a level sequence asset path
in Unreal Engine:

`"metadata": {"unreal": {"sub_sequence": "/Game/Path/To/Sequence.Sequence"}}`

Conversely, the goal of the export hooks are to interpret and convert this
metadata into media references which point to rendered outputs from a movie
render queue. By default, all media references are set to `MissingReference`
on export.

Each of these goals can be implemented at a global level (updating the timeline
once) or a granular level (updating each stack and clip in-place).

See the [OTIO documentation](https://opentimelineio.readthedocs.io/en/latest/tutorials/write-a-hookscript.html)
for instructions on adding hooks to the OTIO environment.

**NOTE**

All OTIO hook functions must have the following signature and parameter names,
regardless of expected parameter type:

```
def hook_function(in_timeline, argument_map=None):
    ...
```

For example, the first parameter should always be named `in_timeline`, even
though the value received in these UE-specific hooks may be a `Timeline`,
`Stack`, or `Clip` object.

## Environment Variables

OTIO import/export behavior in Unreal Engine can also be configured with
a number of supported environment variables. None of these are required.

| Variable                  | Description                                                                                                                                               | Example        |
|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|
| OTIO_UE_REGISTER_UCLASSES | `1` (the default) enables OTIO uclass registration in UE, adding OTIO to UE import and export interfaces. Set to `0` to disable all registration.     | `0`            |
| OTIO_UE_IMPORT_SUFFIXES   | Comma-separated list of OTIO adapter suffixes to register for import into UE. If undefined, all adapters are registered.                                  | `otio,edl,xml` |
| OTIO_UE_EXPORT_SUFFIX     | One OTIO adapter suffix to register for export from UE. Defaults to `otio`.                                                                               | `edl`          |

## Python API

The `otio_unreal` Python package provides an API to assist in implementing
this plugin into pipeline-specific tools and user interfaces. See the
`otio_unreal.adapter` module for the main interface documentation.

## Known Issues

- Registering an `unreal.Factory` via Python, as is done for the OTIO Factory
  (importer), doesn't pass the current Unreal Content Browser location to the
  created `unreal.AssetImportTask` `destination_path` attribute, preventing
  creation of the root level sequence in the expected directory when importing
  via a Content Browser context menu. If a hook defines `sub_sequence` in the
  imported timeline's root "tracks" stack `unreal` metadata, the level
  sequence will be created at that pipeline-defined location, otherwise it will
  be created in a default `/Game/Sequences` directory.
