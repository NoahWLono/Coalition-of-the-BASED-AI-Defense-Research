#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export LAB_HOST_NETNS
LAB_HOST_NETNS=$(readlink /proc/self/ns/net)
exec timeout --signal=TERM --kill-after=8s 180s bwrap \
  --unshare-user --unshare-net --unshare-pid --unshare-ipc --unshare-uts --hostname failsafe-lab \
  --die-with-parent --new-session --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --bind "$LAB_ROOT" "$LAB_ROOT" --chdir "$LAB_ROOT" \
  --ro-bind "$LAB_ROOT/scripts/synthetic-machine-id" /etc/machine-id \
  --setenv PYTHONPATH "$LAB_ROOT/src" --setenv LAB_HOST_NETNS "$LAB_HOST_NETNS" \
  "$LAB_ROOT/.venv/bin/python" -m failsafelab.runner "$@"
