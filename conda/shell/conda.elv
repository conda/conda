# Conda integration for Elvish
#
# INSTALL
#
#     Run 'conda init elvish' and restart your shell.

# The following environment variables are recognized to control the position and
# style of the conda prompt indicator:
# - E:CONDA_LEFT_PROMPT - if the variable exists (regardless of value), the
#   indicator is added to the left prompt. By default, it is added to the right
#   prompt.
# - E:CONDA_PROMPT_MODIFIER_STYLE - by default "green" is used. Multiple
#   attributes can be separated by spaces, e.g. "red bold". See
#   https://elv.sh/ref/builtin.html#styled for documentation of style
#   transformers.

use path
use str
use re

###########################################################################
# General setup - initialize CONDA_SHLVL and add condabin to the PATH

if (not (has-env CONDA_SHLVL)) {
  E:CONDA_SHLVL = 0
}
var -conda-root = (path:dir (path:dir $E:CONDA_EXE))
set paths = [$-conda-root/condabin $@paths]

###########################################################################
# Entry point for conda command
fn conda [@args]{
  if (eq $args []) {
    -conda-exe
  } else {
    var cmd = $args[0]
    var cmd-args = $args[1..]
    if (has-value [activate deactivate reactivate] $cmd) {
      eval (-conda-exe shell.elvish $cmd $@cmd-args | slurp)
    } elif (has-value [install update upgrade remove uninstall config] $cmd) {
      -conda-exe $cmd $@cmd-args
      conda reactivate
    } else {
      -conda-exe $cmd $@cmd-args
    }
  }
}

# Add the conda function to the interactive namespace
edit:add-var conda~ $conda~

###########################################################################
# Prompt indicator

fn conda-prompt-indicator {
  if (!=s $E:CONDA_PROMPT_MODIFIER '') {
    style = green
    if (has-env CONDA_PROMPT_MODIFIER_STYLE) {
      style = $E:CONDA_PROMPT_MODIFIER_STYLE
    }
    styled $E:CONDA_PROMPT_MODIFIER $style
  }
}

# We add conda-prompt-indicator to the interactive namespace, so you can also
# use it in your own prompt definitions if you don't like the default (e.g. to
# change its position within the prompt).
edit:add-var conda-prompt-indicator~ $conda-prompt-indicator~

# Save the current prompt definitions
var -conda-original-prompt-fn~ = $edit:prompt
var -conda-original-rprompt-fn~ = $edit:rprompt

# Redefine them to include the conda indicator based on the value of
# CONDA_LEFT_PROMPT (default is to show in the right prompt).
edit:prompt = {
  if (has-env CONDA_LEFT_PROMPT) {
    conda-prompt-indicator
  }
  -conda-original-prompt-fn
}

edit:rprompt = {
  if (not (has-env CONDA_LEFT_PROMPT)) {
    conda-prompt-indicator
  }
  -conda-original-rprompt-fn
}

###########################################################################
# Completions

######################################################################
# We inline the `comp` module to make this file standalone.
# Slightly trimmed to remove unused functionality in this context.
# Original module at https://github.com/zzamboni/elvish-completions

var debug = $false

fn -debugmsg [@args &color=blue]{
  if $debug {
    echo (styled (echo ">>> " $@args) $color) >/dev/tty
  }
}

fn empty { nop }

fn files [arg &regex='' &dirs-only=$false &transform=$nil]{
  edit:complete-filename $arg | each [c]{
    x = $c[stem]
    if (or (path:is-dir $x) (and (not $dirs-only) (or (eq $regex '') (re:match $regex $x)))) {
      if $transform {
        edit:complex-candidate ($transform $x)
      } else {
        put $c
      }
    }
  }
}

fn dirs [arg &regex='' &transform=$nil]{
  files $arg &regex=$regex &dirs-only=$true &transform=$transform
}

fn extract-opts [@cmd
  &regex='^\s*(?:-(\w),?\s*)?(?:--?([\w-]+))?(?:\[=(\S+)\]|[ =](\S+))?\s*?\s\s(\w.*)$'
  &regex-map=[&short=1 &long=2 &arg-optional=3 &arg-required=4 &desc=5]
  &fold=$false
  &first-sentence=$false
  &opt-completers=[&]
]{
  -line = ''
  capture = $all~
  if $fold {
    capture = { each [l]{
        if (re:match '^\s{8,}\w' $l) {
          var folded = $-line$l
          # -debugmsg "Folded line: "$folded
          put $folded
          -line = ''
        } else {
          # -debugmsg "Non-folded line: "$-line
          put $-line
          -line = $l
        }
      }
    }
  }
  $capture | each [l]{
    -debugmsg "Got line: "$l
    re:find $regex $l
  } | each [m]{
    -debugmsg "Matches: "(to-string $m) &color=red
    g = $m[groups]
    opt = [&]
    keys $regex-map | each [k]{
      if (has-key $g $regex-map[$k]) {
        field = (str:trim-space $g[$regex-map[$k]][text])
        if (not-eq $field '') {
          if (has-value [arg-optional arg-required] $k) {
            opt[$k] = $true
            opt[arg-desc] = $field
            if (has-key $opt-completers $field) {
              opt[arg-completer] = $opt-completers[$field]
            } else {
              opt[arg-completer] = $edit:complete-filename~
            }
          } else {
            opt[$k] = $field
          }
        }
      }
    }
    if (or (has-key $opt short) (has-key $opt long)) {
      if (and (has-key $opt desc) $first-sentence) {
        opt[desc] = (re:replace '\. .*$|\.\s*$|\s*\(.*$' '' $opt[desc])
      }
      opt[desc] = (re:replace '\s+' ' ' $opt[desc])
      put $opt
    }
  }
}

fn -handler-arity [func]{
  fnargs = [ (to-string (count $func[arg-names])) (== $func[rest-arg] -1)]
  if     (eq $fnargs [ 0 $true ])  { put no-args
  } elif (eq $fnargs [ 1 $true ])  { put one-arg
  } elif (eq $fnargs [ 1 $false ]) { put rest-arg
  } else {                           put other-args
  }
}

fn -expand-item [def @cmd]{
  arg = $cmd[-1]
  what = (kind-of $def)
  if (eq $what 'fn') {
    [ &no-args=  { $def }
      &one-arg=  { $def $arg }
      &rest-arg= { $def $@cmd }
      &other-args= { put '<expand-item-completion-fn-arity-error>' }
    ][(-handler-arity $def)]
  } elif (eq $what 'list') {
    all $def
  } else {
    echo (styled "-expand-item: invalid item of type "$what": "(to-string $def) red) >/dev/tty
  }
}

fn -expand-sequence [seq @cmd &opts=[]]{

  final-opts = [(
      -expand-item $opts $@cmd | each [opt]{
        -debugmsg "In final-opts: opt before="(to-string $opt) &color=yellow
        if (eq (kind-of $opt) map) {
          if (has-key $opt arg-completer) {
            -debugmsg &color=yellow "Assigning opt[completer] = [_]{ -expand-item "(to-string $opt[arg-completer]) $@cmd "}"
            opt[completer] = [_]{ -expand-item $opt[arg-completer] $@cmd }
          }
          -debugmsg "In final-opts: opt after="(to-string $opt) &color=yellow
          put $opt
        } else {
          put [&long= $opt]
        }
      }
  )]

  final-handlers = [(
      all $seq | each [f]{
        if (eq (kind-of $f) 'fn') {
          put [
            &no-args=  [_]{ $f }
            &one-arg=  $f
            &rest-arg= [_]{ $f $@cmd }
            &other-args= [_]{ put '<expand-sequence-completion-fn-arity-error>' }
          ][(-handler-arity $f)]
        } elif (eq (kind-of $f) 'list') {
          put [_]{ all $f }
        } elif (and (eq (kind-of $f) 'string') (eq $f '...')) {
          put $f
        }
      }
  )]

  -debugmsg Calling: edit:complete-getopt (to-string $cmd[1..]) (to-string $final-opts) (to-string $final-handlers)
  edit:complete-getopt $cmd[1..] $final-opts $final-handlers
}

fn -expand-subcommands [def @cmd &opts=[]]{

  subcommands = [(keys $def)]
  n = (count $cmd)
  kw = [(range 1 $n | each [i]{
        if (has-value $subcommands $cmd[$i]) { put $cmd[$i] $i }
  })]

  if (and (not-eq $kw []) (not-eq $kw[1] (- $n 1))) {
    sc sc-pos = $kw[0 1]
    if (eq (kind-of $def[$sc]) 'string') {
      cmd[$sc-pos] = $def[$sc]
      -expand-subcommands &opts=$opts $def $@cmd
    } else {
      $def[$sc] (all $cmd[{$sc-pos}..])
    }

  } else {
    top-def = [ { put $@subcommands } ]
    -expand-sequence &opts=$opts $top-def $@cmd
  }
}

fn item [item &pre-hook=$nop~ &post-hook=$nop~]{
  put [@cmd]{
    $pre-hook $@cmd
    result = [(-expand-item $item $@cmd)]
    $post-hook $result $@cmd
    put $@result
  }
}

fn sequence [sequence &opts=[] &pre-hook=$nop~ &post-hook=$nop~]{
  put [@cmd &inspect=$false]{
    if $inspect {
      echo "sequence definition: "(to-string $sequence)
      echo "opts: "(to-string $opts)
    } else {
      $pre-hook $@cmd
      result = [(-expand-sequence &opts=$opts $sequence $@cmd)]
      $post-hook $result $@cmd
      put $@result
    }
  }
}

fn subcommands [def &opts=[] &pre-hook=$nop~ &post-hook=$nop~]{
  put [@cmd &inspect=$false]{
    if $inspect {
      echo "Completer definition: "(to-string $def)
      echo "opts: "(to-string $opts)
    } else {
      $pre-hook $@cmd
      if (and (eq $opts []) (has-key $def -options)) {
        opts = $def[-options]
      }
      del def[-options]
      result = [(-expand-subcommands &opts=$opts $def $@cmd)]
      $post-hook $result $@cmd
      put $@result
    }
  }
}

# End of comp module
######################################################################

# Conda-specific completion functions and definitions

# Cache top-level commands
var conda-commands = $nil
# Cache command option completions
var conda-opt-completions-cache = [&]
# Cache list of shells supported by conda
var conda-shells = $nil
# Cache list of valid config keys
var conda-config-keys = $nil

# Fetch and cache top-level commands
fn init-conda-commands {
  if (not $conda-commands) {
    # `activate` and `deactivate` are not in the commands output so we add them
    # by hand.
    conda-commands = [(conda shell.elvish commands) activate deactivate]
  }
}

# Completer functions for different elements in the conda ecosystem

fn ENVIRONMENTS {
  echo base
  e:ls -1 $E:CONDA_PREFIX/envs
}

fn PACKAGES {
  put (all (conda list --json | from-json))[name]
}

fn SHELLS {
  if (not $conda-shells) {
    conda-shells = [(python -c 'from conda.base.constants import COMPATIBLE_SHELLS; print("\n".join(COMPATIBLE_SHELLS))')]
  }
  all $conda-shells
}

fn COMMANDS {
  init-conda-commands
  all $conda-commands
}

fn CONFIG-KEYS {
  if (not $conda-config-keys) {
    conda-config-keys = [(python -c 'from conda.base.context import context; print ("\n".join(context.list_parameters()))')]
  }
  all $conda-config-keys
}

# Completers for positional arguments of top-level commands. We only define the
# completers for the commands that take positional arguments, the default in
# `completer-of` is to take no arguments (which is the case for most conda
# commands).
var conda-completers = [
  &activate=  [ [stem]{ ENVIRONMENTS; if (re:match '^[./]' $stem) { dirs $stem } } ]
  &compare=   [ $files~ ]
  &develop=   [ $dirs~ ... ]
  &env= [
    &create= []
    &export= []
    &list=   []
    &remove= []
    &update= []
    &config= []
  ]
  &help=      [ $COMMANDS~ ]
  &index=     [ $dirs~ ... ]
  &init=      [ $SHELLS~ ... ]
  &inspect=   [
    &linkages= [ $PACKAGES~ ... ]
    &objects=  [ $PACKAGES~ ... ]
    &channels= []
    &prefix-lengths= [ $PACKAGES~ ... ]
    &hash-inputs= [ $PACKAGES~ ... ]
  ]
  &remove=    [ $PACKAGES~ ... ]
  &render=    [ $dirs~ ]
  &run=       [ [arg]{ edit:complete-sudo run $arg } ]
  &skeleton=  [
    &cpan= []
    &cran= []
    &luarocks= []
    &pypi= []
    &rpm= []
  ]
  &uninstall= remove
  &update=    [ $PACKAGES~ ... ]
  &upgrade=   update
  # By default a command has no positional arguments
  &-DEFAULT=  []
]

# Completers for option arguments. The indices are the description of the
# arguments as they appear in the corresponding help output. Note that we can
# only provide completion for the first argument of an option.
var conda-opt-completers = [
  &ENV=                           $ENVIRONMENTS~
  &ENVIRONMENT=                   $ENVIRONMENTS~
  &PATH=                          $dirs~
  &TEMPFILES=                     $dirs~
  &'TEMPFILES [TEMPFILES ...]'=   $dirs~
  &CWD=                           $dirs~
  &CROOT=                         $dirs~
  &OUTPUT_FOLDER=                 $dirs~
  &OUTPUT_DIR=                    $dirs~
  &FILE=                          $files~
  &STATS_FILE=                    $files~
  &CONFIG_FILE=                   $files~
  &KEY=                           $CONFIG-KEYS~
  &'KEY VALUE'=                   $CONFIG-KEYS~
  &'[KEY [KEY ...]]'=             $CONFIG-KEYS~
  &'[DESCRIBE [DESCRIBE ...]]'=   $CONFIG-KEYS~
  &'[SHOW [SHOW ...]]'=           $CONFIG-KEYS~
  &'EXTRA_DEPS [EXTRA_DEPS ...]'= $PACKAGES~
  &PACKAGE=                       $PACKAGES~
  # This is for an option of `conda skeleton rpm`
  &DISTRO=                        { put centos5 centos6 centos7 clefos suse_leap_rpi3 raspbian_rpi2 }
]

# There are a few options that are formatted differently in the conda help
# outputs, so they are hard to grab automatically. For these we just define
# their completers here by hand, indexed by command name.
var conda-opt-manual-completions = [
  &config= [
    [ &long=prepend &arg-desc='KEY VALUE' &arg-required=$true
      &desc='Add one configuration value to the beginning of a list key'
      &arg-completer=$conda-opt-completers['KEY VALUE'] ]
    [ &long=add &arg-desc='KEY VALUE' &arg-required=$true
      &desc='Add one configuration value to the beginning of a list key'
      &arg-completer=$conda-opt-completers['KEY VALUE'] ]
  ]
  &search= [
    [ &long=subdir &arg-desc='SUBDIR' &arg-required=$true
      &desc='Search the given subdir' &arg-completer=$empty~
    ]
    [ &long=platform &arg-desc='SUBDIR' &arg-required=$true
      &desc='Search the given subdir' &arg-completer=$empty~
    ]
  ]
  &convert= [
    [ &long=dependencies &short=d &arg-desc='[DEPENDENCIES [DEPENDENCIES ...]]' &arg-required=$true
      &desc='Search the given subdir' &arg-completer=$conda-opt-completers[PACKAGE]
    ]
  ]
  &inspect= [
    &linkages= [
      [
        &long=groupby &arg-desc='{package,dependency}' &arg-required=$true
        &desc='Attribute to group by (default: package)' &arg-completer={ put package dependency }
      ]
    ]
    &objects= [
      [
        &long=groupby &arg-desc='{filename,filetype,rpath}' &arg-required=$true
        &desc='Attribute to group by (default: filename)' &arg-completer={ put filename filetype rpath }
      ]
    ]
    &prefix-lengths= [
      [
        &long=min-prefix-length &short=m &arg-desc='MIN_PREFIX_LENGTH' &arg-required=$true
        &desc='Minimum length' &arg-completer=$empty~
      ]
    ]
  ]
  &skeleton= [
    &cran= [
      [
        &long=use-when-no-binary &arg-desc='{src,old,src-old,old-src,error}' &arg-required=$true
        &desc='Fallback when binaries not available' &arg-completer={ put src old src-old old-src error }
      ]
      [
        &long=update-policy &arg-desc='UPDATE_POLICY' &arg-required=$true
        &desc='Policy when existing packages are encountered'
        &arg-completer={ put error skip-up-to-date skip-existing overwrite merge-keep-build-num merge-incr-build-num }
      ]
    ]
    &pypi= [
      [
        &long=python-version &arg-desc='{2.7,3.5,3.6,3.7,3.8}' &arg-required=$true
        &desc='Version of Python to use to run setup.py' &arg-completer={ put 2.7 3.5 3.6 3.7 3.8 }
      ]
    ]
  ]
]

# Find an element within nested map structure $obj, following the keys contained
# in the list $path. If not found, return &default.
# E.g.:
#    path-in [&a=[&b=foo]] [a b]   => foo
fn path-in [obj path &default=$nil]{
  each [k]{
    try {
      obj = $obj[$k]
    } except {
      obj = $default
      break
    }
  } $path
  put $obj
}

# Return the positional completers of the given command.
fn completer-of [@cmd]{
  or (path-in $conda-completers $cmd) $conda-completers[-DEFAULT]
}

# Fetch command options for a command from its help text.
fn conda-opts [@cmd]{
  var opts
  var cmd-str = (str:join ' ' $cmd)
  if (has-key $conda-opt-completions-cache $cmd-str) {
    # If the options are cached already, return them
    opts = $conda-opt-completions-cache[$cmd-str]
  } else {
    # Otherwise, parse them from the command's --help output.

    # UGLY regex to match options and their descriptions, of the form:
    #    -x [ARG], --long [ARG]   Option description
    # Which get captured into the corresponding data structure.
    var opts-regex = '^  (?:-(\w)(?: \[[A-Z\[][A-Z_ \[\]\.]+\]| [A-Z][A-Z_ \[\]\.]+)?,?\s*)?(?:--?([\w-]+))(?: (\[[A-Z\[][A-Z_ \[\]\.]+\]|[A-Z][A-Z_ \[\]\.]+))?\s*?\s\s(\w.*)$'
    var opts-regex-map = [&short=1 &long=2 &arg-optional=9999 &arg-required=3 &desc=4]

    opts = [
      (_ = ?(conda $@cmd --help 2>&1; echo "") | ^
      extract-opts &fold &first-sentence &regex=$opts-regex &regex-map=$opts-regex-map &opt-completers=$conda-opt-completers)
    ]
    # Add manually-defined option completers, if any
    if (var manual-comps = (path-in $conda-opt-manual-completions $cmd)) {
      # We add only end nodes, not the intermediate maps
      if (eq (kind-of $manual-comps) list) {
        opts = [ $@opts $@manual-comps ]
      }
    }
    # Store in cache for future use
    conda-opt-completions-cache[$cmd-str] = $opts
  }
  -debugmsg "conda-opts "(to-string $cmd)": "(to-string $opts)
  all $opts
}

# Populate a map of subcommand completions using their definitions from
# $conda-completers. This is used for the top-level conda commands, and recurses
# through those that have subcommands of their own.
fn completion-structure [@c]{
  var completions = [&]
  each [cmd]{
    seq = (completer-of $@c $cmd)
    if (eq (kind-of $seq) string) {
      completions[$cmd] = $seq
    } elif (eq (kind-of $seq) map) {
      completions[$cmd] = (subcommands (keys $seq | completion-structure $@c $cmd) &opts={ conda-opts $@c $cmd })
    } else {
      completions[$cmd] = (sequence $seq &opts={ conda-opts $@c $cmd })
    }
  }
  put $completions
}

# Configure the completer function
fn init-completions {
  completions = (COMMANDS | completion-structure)
  var conda-completer = (subcommands $completions &opts={ conda-opts })
  edit:completion:arg-completer[conda] = $conda-completer
}

init-completions
