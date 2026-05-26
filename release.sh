#!/usr/bin/env bash
set -euo pipefail

MODE=""
PYTHON_EXE="${PYTHON_EXE:-${HOME}/uv_envs/arm64/uv_312_flappy_dev/Scripts/python.exe}"
TAG_FLAG=""
ANY_BRANCH=""
ALLOW_DIRTY=""
CREATED_TAG=""
RELEASE_TAG=""
RELEASE_VERSION=""

usage() {
  echo "Usage:"
  echo "  $0 [all|build|send|build-pip|send-pip] [--tag] [--any-branch] [--allow-dirty]"
  echo "  all/build/build-pip: build pip artifacts locally"
  echo "  send/send-pip: publish pip artifacts with twine"
  echo "  --tag: create and verify a new local git tag before running"
  echo "  --any-branch: skip the main-branch check"
  echo "  --allow-dirty: allow build-pip/build/all from a dirty tree"
  echo
  echo "Environment:"
  echo "  PYTHON_EXE defaults to: $PYTHON_EXE"
}

for arg in "$@"; do
  case "$arg" in
    -h|--help|help) usage; exit 0 ;;
    --tag) TAG_FLAG="--tag" ;;
    --any-branch) ANY_BRANCH="--any-branch" ;;
    --allow-dirty) ALLOW_DIRTY="--allow-dirty" ;;
    all|build|send|build-pip|send-pip|build-conda|send-conda)
      if [[ -n "$MODE" ]]; then
        echo "ERROR: multiple release modes supplied: '$MODE' and '$arg'." >&2
        usage
        exit 2
      fi
      MODE="$arg"
      ;;
    *) usage; exit 2 ;;
  esac
done
MODE="${MODE:-build-pip}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

case "$MODE" in
  all|build|send|build-pip|send-pip) ;;
  build-conda|send-conda)
    echo "ERROR: ionbus_flapi has no conda-recipe directory; conda release modes are not supported." >&2
    exit 2
    ;;
  *) usage; exit 2 ;;
esac

if [[ ! -x "$PYTHON_EXE" ]]; then
  echo "ERROR: could not find executable Python at $PYTHON_EXE" >&2
  echo "Set PYTHON_EXE to the flapi uv environment's python." >&2
  exit 1
fi

if [[ -n "$ALLOW_DIRTY" ]]; then
  case "$MODE" in
    all|build|build-pip) ;;
    *)
      echo "ERROR: --allow-dirty is only supported with build-pip/build/all." >&2
      exit 2
      ;;
  esac
fi
if [[ -n "$ALLOW_DIRTY" && -n "$TAG_FLAG" ]]; then
  echo "ERROR: --allow-dirty cannot be combined with --tag." >&2
  exit 2
fi

verify_main_branch() {
  local branch

  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [[ "$branch" != "main" ]]; then
    echo "ERROR: not on main branch (currently on '$branch')." >&2
    echo "Use --any-branch to override." >&2
    exit 1
  fi
}

verify_clean_tree() {
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "ERROR: release requires a clean git tree." >&2
    git status --short >&2
    exit 1
  fi
}

verify_head_tag() {
  local expected_tag="${1:-}"
  local current_tag

  current_tag="$(git describe --tags --exact-match 2>/dev/null || true)"
  if [[ -z "$current_tag" ]]; then
    echo "ERROR: HEAD is not tagged." >&2
    exit 1
  fi
  if [[ -n "$expected_tag" && "$current_tag" != "$expected_tag" ]]; then
    echo "ERROR: expected HEAD tag '$expected_tag' but found '$current_tag'" >&2
    exit 1
  fi
}

get_next_tag_name() {
  local output tag

  output="$("$PYTHON_EXE" -m ionbus_utils.git_utils.auto_tag . --name-only 2>&1)"
  tag="$(
    printf '%s\n' "$output" \
      | sed -nE "s/.*tag='([^']+)'.*/\1/p" \
      | tail -n 1
  )"
  if [[ -z "$tag" ]]; then
    tag="$(printf '%s\n' "$output" | awk 'NF { print }' | tail -n 1)"
  fi
  printf '%s\n' "$tag"
}

maybe_tag_release() {
  if [[ "$TAG_FLAG" == "--tag" ]]; then
    verify_clean_tree
    CREATED_TAG="$(get_next_tag_name)"
    if [[ -z "$CREATED_TAG" ]]; then
      echo "ERROR: failed to compute new tag name" >&2
      exit 1
    fi
    if git rev-parse -q --verify "refs/tags/$CREATED_TAG" >/dev/null; then
      echo "ERROR: tag '$CREATED_TAG' already exists locally" >&2
      exit 1
    fi
    git tag -a "$CREATED_TAG" -m "auto-tag $CREATED_TAG"
    verify_head_tag "$CREATED_TAG"
    echo "Created local tag: $CREATED_TAG"
  fi
}

read_project_version() {
  printf '%s\n' "${RELEASE_TAG#v}"
}

verify_tag_matches_project_version() {
  return 0
}

ensure_release_context() {
  if [[ -z "$ALLOW_DIRTY" ]]; then
    verify_clean_tree
  else
    echo "WARNING: building local test artifact from a dirty tree." >&2
  fi
  verify_head_tag
  RELEASE_TAG="$(git describe --tags --exact-match)"
  RELEASE_VERSION="$(read_project_version)"
  verify_tag_matches_project_version "$RELEASE_TAG" "$RELEASE_VERSION"
}

cleanup_python_artifacts() {
  rm -rf build dist
  find . -maxdepth 1 -name "*.egg-info" -exec rm -rf {} +
}

verify_python_artifacts() {
  local version="$1"

  "$PYTHON_EXE" - "$version" <<'PY' || {
import pathlib
import sys

version = sys.argv[1]
dist = pathlib.Path("dist")
files = sorted(dist.iterdir()) if dist.is_dir() else []
wheel = [path for path in files if path.suffix == ".whl" and version in path.name]
sdist = [
    path
    for path in files
    if path.name.endswith(".tar.gz") and version in path.name
]
sys.exit(0 if wheel and sdist else 1)
PY
    echo "ERROR: expected wheel and sdist for version $version in dist/" >&2
    exit 1
  }
}

verify_built_package_versions() {
  local version="$1"

  "$PYTHON_EXE" - "$version" <<'PY' || {
import email.parser
import io
import pathlib
import sys
import tarfile
import zipfile

version = sys.argv[1]
wheels = sorted(pathlib.Path("dist").glob(f"*{version}*.whl"))
if len(wheels) != 1:
    raise SystemExit(f"expected exactly one wheel for {version}, found {len(wheels)}")

sdists = sorted(pathlib.Path("dist").glob(f"*{version}*.tar.gz"))
if len(sdists) != 1:
    raise SystemExit(f"expected exactly one sdist for {version}, found {len(sdists)}")


def parse_metadata_version(text):
    metadata = email.parser.Parser().parsestr(text)
    return metadata["Version"]


with zipfile.ZipFile(wheels[0]) as zf:
    metadata_names = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
    if len(metadata_names) != 1:
        raise SystemExit(
            f"expected exactly one wheel METADATA file, found {len(metadata_names)}"
        )
    wheel_version = parse_metadata_version(zf.read(metadata_names[0]).decode("utf-8"))

with tarfile.open(sdists[0], "r:gz") as tf:
    names = tf.getnames()
    pkg_info_names = [
        n for n in names if n.count("/") == 1 and n.endswith("/PKG-INFO")
    ]
    if len(pkg_info_names) != 1:
        raise SystemExit(
            f"expected exactly one sdist PKG-INFO file, found {len(pkg_info_names)}"
        )
    member = tf.extractfile(pkg_info_names[0])
    if member is None:
        raise SystemExit(f"could not read {pkg_info_names[0]}")
    sdist_version = parse_metadata_version(
        io.TextIOWrapper(member, encoding="utf-8").read()
    )

if wheel_version != version:
    raise SystemExit(f"wheel version {wheel_version!r} does not match {version!r}")
if sdist_version != version:
    raise SystemExit(f"sdist version {sdist_version!r} does not match {version!r}")
PY
    echo "ERROR: built package metadata verification failed" >&2
    exit 1
  }
}

build_pip_artifacts() {
  ensure_release_context
  cleanup_python_artifacts

  if ! "$PYTHON_EXE" -c "import build" >/dev/null 2>&1; then
    echo "ERROR: Python environment is missing 'build'. Install it in the flapi uv env." >&2
    exit 1
  fi

  "$PYTHON_EXE" -m build --no-isolation --skip-dependency-check

  if "$PYTHON_EXE" -c "import twine" >/dev/null 2>&1; then
    "$PYTHON_EXE" -m twine check dist/*
  else
    echo "WARNING: twine is not installed; skipping twine check" >&2
  fi

  verify_python_artifacts "$RELEASE_VERSION"
  verify_built_package_versions "$RELEASE_VERSION"
  echo "Built pip artifacts in: $ROOT_DIR/dist"
  echo "Version/tag used: $RELEASE_TAG"
}

send_pip_artifacts() {
  ensure_release_context
  verify_python_artifacts "$RELEASE_VERSION"
  verify_built_package_versions "$RELEASE_VERSION"

  if ! "$PYTHON_EXE" -c "import twine" >/dev/null 2>&1; then
    echo "ERROR: Python environment is missing 'twine'. Install it in the flapi uv env." >&2
    exit 1
  fi

  "$PYTHON_EXE" -m twine upload dist/*
}

[[ -n "$ANY_BRANCH" ]] || verify_main_branch
maybe_tag_release

case "$MODE" in
  all|build|build-pip) build_pip_artifacts ;;
  send|send-pip) send_pip_artifacts ;;
esac
