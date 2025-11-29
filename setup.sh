#!/bin/bash

echo "======================================"
echo "iGEM Wiki 爬虫环境配置脚本"
echo "======================================"

# 检查Python版本
echo "检查Python版本..."
python3 --version

# 创建虚拟环境
echo ""
echo "创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo ""
echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo ""
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "安装依赖包..."
pip install -r requirements.txt

# 显示安装的包
echo ""
echo "已安装的依赖包："
pip list

echo ""
echo "======================================"
echo "环境配置完成！"
echo "======================================"
echo ""
echo "使用说明："
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 运行爬虫: python igem_crawler.py"
echo "3. 退出虚拟环境: deactivate"
echo ""
