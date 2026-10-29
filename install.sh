#!/usr/bin/env bash
# 과제 폴더(현재 디렉터리)에 하네스를 깐다. 이미 있는 파일은 덮어쓰지 않는다.
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"
mkdir -p .harness .agents/skills
cp -rn "$H/tools" .harness/ 2>/dev/null || true
cp -n "$H/intake.md" .harness/ 2>/dev/null || true
cp -rn "$H/skills/." .agents/skills/ 2>/dev/null || true
for f in PLAN NOTES SUBMISSION; do
  [ -e "$f.md" ] && echo "skip $f.md (이미 있음)" || cp "$H/templates/$f.md" "$f.md"
done
if [ -e AGENTS.md ]; then
  grep -q "cofa-harness" AGENTS.md || { printf '\n\n' >> AGENTS.md; cat "$H/AGENTS.md" >> AGENTS.md; echo "AGENTS.md 뒤에 덧붙임"; }
else
  cp "$H/AGENTS.md" AGENTS.md
fi
[ -d .git ] || { git init -q && echo "git init"; }
python3 .harness/tools/profile.py --selftest | tail -1
# 이 기계에 무엇이 있나 — 스택을 정하기 전에 본다
echo "python $(python3 -V 2>&1 | cut -d' ' -f2) · node $(node -v 2>/dev/null || echo 없음) · git root $(git rev-parse --show-toplevel)"
for m in pandas numpy flask fastapi streamlit openpyxl matplotlib pytest; do python3 -c "import $m" 2>/dev/null && printf '%s ' "$m"; done; echo "(설치된 파이썬 패키지)"
echo "다음: .harness/intake.md 로 담당자에게 묻고 PLAN.md 를 채운다. Codex 를 다시 열고 /skills 로 4개가 보이는지 본다."
