#!/usr/bin/env bash
set -euo pipefail
cd /root/codes/x-kernel-worktrees/ai-review-book
run=research/evidence/runs/2026-11-17-kani-preflight-01
export KANI_HOME="$PWD/.build/kani-home"
timeout 600 cargo +1.95.0 install --locked kani-verifier --version 0.68.0 --root "$PWD/.build/kani-installer-0.68.0"
timeout 600 .build/kani-installer-0.68.0/bin/cargo-kani setup
python3 scripts/check_kani_installation.py --run 2026-11-17-kani-preflight-01
