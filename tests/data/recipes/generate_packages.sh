# exit if any command fails
set -e

RECIPES_DIR=$(dirname $0)
TEST_RECIPES_DIR=$(dirname $RECIPES_DIR)/test-recipes

conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/activate_deactivate_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/another_dependent
CONDA_SUBDIR=linux-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/arch-package
CONDA_SUBDIR=osx-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/arch-package
CONDA_SUBDIR=win-fake conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/arch-package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/b_post_link_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/buildstring
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/c_post_link_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/clobber-a
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/clobber-b
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/d_post_link_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/dependent
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/e_post_link_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/failing_post_link
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/feature
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/other_dependent
CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/pip
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/post_link_run_in_env_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/pre_link_messages_package
conda build --output-folder $TEST_RECIPES_DIR $RECIPES_DIR/private-package
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
