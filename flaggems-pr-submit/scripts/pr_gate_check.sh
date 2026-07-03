#!/bin/bash
# PR Gate Check — 在手动 git commit / git push / gh pr create 前强制验证
# 被 .codex/config.toml 的 PreToolUse hook 调用
#
# 检查逻辑：
# 1. 当前分支是否是 pr/<op> 格式
# 2. 读取本次 Bash 命令，只拦截手动提交相关危险命令
# 3. submit_operator.py 是正规主流程入口，允许启动，但禁止 skip 测试/benchmark
# 4. 危险命令执行前检查 .pr_gate/<op_id>.passed 标记文件
# 5. 如果没通过，输出 JSON 阻止操作

REPO_DIR="/data/dxd/FlagGems_minimax_2_7_pr"
SCRIPTS_DIR="/data/dxd/.codex/skills/flaggems-pr-submit/scripts"
GATE_DIR="$REPO_DIR/.pr_gate"

HOOK_INPUT="$(cat)"
COMMAND=$(printf '%s' "$HOOK_INPUT" | python -c '
import json
import sys


def find_command(value):
    if isinstance(value, dict):
        tool_input = value.get("tool_input") or value.get("toolInput") or {}
        if isinstance(tool_input, dict):
            command = tool_input.get("command") or tool_input.get("cmd")
            if isinstance(command, str):
                return command

        for key in ("command", "cmd"):
            command = value.get(key)
            if isinstance(command, str):
                return command

        for item in value.values():
            command = find_command(item)
            if command:
                return command

    if isinstance(value, list):
        for item in value:
            command = find_command(item)
            if command:
                return command

    return ""


try:
    data = json.load(sys.stdin)
except Exception:
    print("")
else:
    print(find_command(data))
')

deny() {
    local reason="$1"
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "$reason"
  }
}
EOF
    exit 0
}

# 获取当前分支名
BRANCH=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

# 不是 pr/ 分支就放行
if [[ ! "$BRANCH" =~ ^pr/ ]]; then
    exit 0
fi

OP_NAME="${BRANCH#pr/}"
OP_ID="${OP_NAME#"${OP_NAME%%[!_]*}"}"
GATE_FILE="$GATE_DIR/$OP_ID.passed"

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# submit_operator.py 是生成 gate 的正规入口，必须允许启动；但不允许跳过测试/benchmark。
if [[ "$COMMAND" == *"submit_operator.py"* ]]; then
    if [[ "$COMMAND" == *"--skip-test"* || "$COMMAND" == *"--skip-benchmark"* ]]; then
        deny "PR Gate: submit_operator.py 不允许使用 --skip-test 或 --skip-benchmark。请运行完整验证流程。"
    fi
    exit 0
fi

IS_DANGEROUS=0
if [[ "$COMMAND" =~ (^|[[:space:];&|])git[[:space:]]+commit([[:space:]]|$) ]]; then
    IS_DANGEROUS=1
fi
if [[ "$COMMAND" =~ (^|[[:space:];&|])git[[:space:]]+push([[:space:]]|$) ]]; then
    IS_DANGEROUS=1
fi
if [[ "$COMMAND" =~ (^|[[:space:];&|])gh[[:space:]]+pr[[:space:]]+create([[:space:]]|$) ]]; then
    IS_DANGEROUS=1
fi

if [[ "$IS_DANGEROUS" -eq 0 ]]; then
    exit 0
fi

# 检查 gate 标记
if [[ -f "$GATE_FILE" ]]; then
    FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$GATE_FILE" 2>/dev/null || echo 0) ))
    if [[ $FILE_AGE -lt 3600 ]]; then
        # 确认测试已通过（不允许 test=skip 绕过）
        if grep -q "test=pass" "$GATE_FILE"; then
            exit 0  # 放行
        fi
    fi
fi

deny "PR Gate: check_operator.py 未通过。请先运行: python $SCRIPTS_DIR/submit_operator.py $OP_NAME --repo-dir $REPO_DIR"
