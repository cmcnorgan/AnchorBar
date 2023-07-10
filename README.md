# AnchorBar
This is a CLI Python tool that uses a sqlite database for importing, managing and exporting FreeSurfer cortical surface annotations (e.g., from the /label directory) using set operations.

The tool includes 3 scripts (AnchorBar*.py) and a master database (annot.db). AnchorBar_init.py adds annotations to the database. AnchorBar_sets.py performs set operations (union, intersection) on pairs of annotations to create new annotations. AnchorBar_tools.py includes operations to manage the database and export annotations to .annot files for use in FreeSurfer.

The tool comes the annotation database initialized with all annotations in fsaverage/label directory. Additional annotations (e.g., functionally-defined regions from statistical analyses) can be added via import functionality. Set operations allow for sub-parcellation and annotation merging, so that, e.g. functionally-defined regions can be further segmented along anatomical boundaries.

Program help can be obtained by invoking the .py script with the -? switch.
