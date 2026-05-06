#!/bin/bash
# ============================================================
# Hermes Agent 一键安装脚本 (在 WSL2 Ubuntu 中运行)
# 使用方法：
#   1. 以管理员身份打开 PowerShell，运行: wsl --install
#   2. 重启电脑，打开 Ubuntu 终端
#   3. 运行: bash /mnt/d/Users/hez/Desktop/hithium/setup-hermes.sh
# ============================================================

set -e

echo "=========================================="
echo "  Hermes Agent 安装 — Hithium 仿真工作站"
echo "=========================================="

# 1. 安装 Hermes Agent
echo ""
echo "[1/5] 安装 Hermes Agent..."
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null || true

# 2. 复制预配置文件
echo ""
echo "[2/5] 部署配置文件..."

HERMES_HOME="${HOME}/.hermes"
WIN_HERMES="C:\\Users\\hez\\.hermes"
WSL_HERMES="/mnt/c/Users/hez/.hermes"

# 如果 Windows 侧已有配置，复制到 WSL
if [ -d "$WSL_HERMES" ]; then
    echo "  检测到 Windows 侧预配置文件，正在同步..."

    # config.yaml
    if [ -f "$WSL_HERMES/config.yaml" ]; then
        mkdir -p "$HERMES_HOME"
        cp "$WSL_HERMES/config.yaml" "$HERMES_HOME/config.yaml"
        echo "  ✓ config.yaml"
    fi

    # SOUL.md
    if [ -f "$WSL_HERMES/SOUL.md" ]; then
        cp "$WSL_HERMES/SOUL.md" "$HERMES_HOME/SOUL.md"
        echo "  ✓ SOUL.md"
    fi

    # Skills
    if [ -d "$WSL_HERMES/skills/battery-simulation" ]; then
        mkdir -p "$HERMES_HOME/skills/battery-simulation"
        cp -r "$WSL_HERMES/skills/battery-simulation/"* "$HERMES_HOME/skills/battery-simulation/"
        echo "  ✓ battery-simulation skill"
    fi

    # Cron jobs
    if [ -f "$WSL_HERMES/jobs.json" ]; then
        cp "$WSL_HERMES/jobs.json" "$HERMES_HOME/jobs.json"
        echo "  ✓ jobs.json (cron 定时任务)"
    fi
else
    echo "  未检测到预配置，将启动交互式配置..."
fi

# 3. 设置环境变量
echo ""
echo "[3/5] 配置环境变量..."
HITHIUM_PATH="/mnt/d/Users/hez/Desktop/hithium"

# 添加 Python 路径配置
if ! grep -q "HITHIUM" ~/.bashrc 2>/dev/null; then
    cat >> ~/.bashrc << 'ENVEOF'

# === Hermes Agent + Hithium 仿真环境 ===
export HITHIUM_ROOT="/mnt/d/Users/hez/Desktop/hithium"
export PYTHONPATH="${HITHIUM_ROOT}/BatteryProject:${HITHIUM_ROOT}/params:${PYTHONPATH}"
ENVEOF
    echo "  ✓ PYTHONPATH 已配置"
fi

# 4. 验证安装
echo ""
echo "[4/5] 验证安装..."
if command -v hermes &>/dev/null; then
    echo "  ✓ hermes 命令可用"
    hermes --version 2>/dev/null || echo "  (版本信息不可用)"
else
    echo "  ✗ hermes 未找到，请运行: source ~/.bashrc"
fi

# 5. 提示后续步骤
echo ""
echo "[5/5] 安装完成！后续步骤："
echo ""
echo "  # 重新加载 shell"
echo "  source ~/.bashrc"
echo ""
echo "  # 运行配置向导 (设置 API Key)"
echo "  hermes setup"
echo ""
echo "  # 推荐使用 OpenRouter，注册后获取 API Key:"
echo "  # https://openrouter.ai/keys"
echo ""
echo "  # 开始对话"
echo "  hermes"
echo ""
echo "  # 查看已安装的 Skills"
echo "  hermes skills list"
echo ""
echo "  # 配置 Telegram 网关 (可选)"
echo "  hermes gateway setup"
echo ""
echo "=========================================="
echo "  配置文件位置: ~/.hermes/"
echo "  项目目录: /mnt/d/Users/hez/Desktop/hithium"
echo "=========================================="
