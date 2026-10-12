#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT}/output/primitives"
SCRIPT="${ROOT}/scripts/generate_primitive_shapes.py"

FREECAD_CMD="${FREECAD_CMD:-}"
if [[ -z "${FREECAD_CMD}" ]]; then
  for candidate in \
    "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd" \
    "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd" \
    "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
  do
    if [[ -x "${candidate}" ]]; then
      FREECAD_CMD="${candidate}"
      break
    fi
  done
fi

if [[ -z "${FREECAD_CMD}" ]]; then
  echo "FreeCADCmd not found. Install FreeCAD or set FREECAD_CMD." >&2
  exit 1
fi

# Default: 20 variants × 6 families = 120 files.
if (($# > 0)); then
  USER_ARGS=("$@")
else
  USER_ARGS=(--output-dir "${OUTPUT_DIR}" --count 20)
fi

PYTHON_CODE="$(python3 - "${SCRIPT}" "${USER_ARGS[@]}" <<'PY'
import json
import sys

script = sys.argv[1]
argv = ["generate_primitive_shapes", *sys.argv[2:]]
print(
    f"import sys\n"
    f"sys.path.insert(0, {json.dumps(str(__import__('pathlib').Path(script).resolve().parent))})\n"
    f"sys.argv = {json.dumps(argv)}\n"
    f"exec(compile(open({json.dumps(script)}, encoding='utf-8').read(), "
    f"{json.dumps(script)}, 'exec'), "
    f"{{'__name__': '__main__', '__file__': {json.dumps(script)}}})"
)
PY
)"

exec "${FREECAD_CMD}" -c "${PYTHON_CODE}"
