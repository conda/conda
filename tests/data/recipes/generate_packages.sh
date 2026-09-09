#!/usr/bin/env bash
# Rebuild test channel packages under tests/data/test-recipes from recipe sources.
#
# Workflow:
#   1. Edit recipes under tests/data/recipes/
#   2. Run this script
#   3. Commit the updated artifacts (and repodata.json from indexing below)
#   4. Pre-commit regenerates tests/data/recipes/README.md from the artifacts
#
# If you rename/remove a package or change its filename (version/build), delete the
# old artifact under tests/data/test-recipes/ yourself before rebuilding so orphans
# are not left in the channel.

# exit if any command fails
set -e

RECIPES_DIR=$(dirname $0)
TEST_RECIPES_DIR=$(dirname $RECIPES_DIR)/test-recipes

conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/activate_deactivate_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/another_dependent
CONDA_SUBDIR=linux-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/arch-package
CONDA_SUBDIR=osx-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/arch-package
CONDA_SUBDIR=win-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/arch-package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/buildstring
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/clobber
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/dependent
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/failing_post_link
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/feature
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/other_dependent
CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/pip
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/post_link_run_in_env_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/post_link-b
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/post_link-c
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/post_link-d
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/post_link-e
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/pre_link_messages_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/private-package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/pycosat
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/conda
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/python
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/run_constrained
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/sample_noarch_python
# non-conda recipe $RECIPES_DIR/small_python_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/small-executable
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/track_feature
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/unsatisfiable --no-test
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/versioned
CONDA_SUBDIR=linux-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/virtualdep-package
CONDA_SUBDIR=osx-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/virtualdep-package
CONDA_SUBDIR=win-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/virtualdep-package

conda index "$TEST_RECIPES_DIR" \
  --subdir noarch \
  --subdir linux-fake \
  --subdir osx-fake \
  --subdir win-fake
