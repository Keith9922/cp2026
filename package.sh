#!/bin/bash

echo "======================================"
echo "准备提交文件打包"
echo "======================================"

# 获取用户名
read -p "请输入您的姓名（用于命名压缩包）: " NAME

if [ -z "$NAME" ]; then
    echo "错误: 姓名不能为空"
    exit 1
fi

# 创建临时目录
TEMP_DIR="${NAME}_submission"
mkdir -p "$TEMP_DIR"

echo ""
echo "正在复制文件..."

# 复制必要的文件
cp igem_crawler.py "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"
cp README.md "$TEMP_DIR/"
cp 技术报告.md "$TEMP_DIR/"

# 如果有运行结果，也复制
if [ -d "images" ]; then
    cp -r images "$TEMP_DIR/"
    echo "✓ 已复制 images 目录"
fi

if [ -f "dataset.json" ]; then
    cp dataset.json "$TEMP_DIR/"
    echo "✓ 已复制 dataset.json"
fi

if [ -f "crawler.log" ]; then
    cp crawler.log "$TEMP_DIR/"
    echo "✓ 已复制 crawler.log"
fi

# 生成PDF版本的技术报告（需要pandoc，如果没有则跳过）
if command -v pandoc &> /dev/null; then
    echo ""
    echo "正在生成PDF格式技术报告..."
    pandoc 技术报告.md -o "$TEMP_DIR/技术报告.pdf" --pdf-engine=xelatex -V mainfont="PingFang SC" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ PDF技术报告已生成"
    else
        echo "⚠ PDF生成失败，请手动转换Markdown为PDF"
        echo "  可以使用在线工具: https://www.markdowntopdf.com/"
    fi
else
    echo ""
    echo "⚠ 未安装pandoc，无法自动生成PDF"
    echo "  请手动将 技术报告.md 转换为PDF格式"
    echo "  推荐工具: Typora, 在线转换器等"
fi

# 创建压缩包
echo ""
echo "正在创建压缩包..."
ZIP_NAME="${NAME}.zip"
zip -r "$ZIP_NAME" "$TEMP_DIR" > /dev/null

# 清理临时目录
rm -rf "$TEMP_DIR"

echo ""
echo "======================================"
echo "打包完成！"
echo "======================================"
echo ""
echo "压缩包: $ZIP_NAME"
echo "大小: $(du -h "$ZIP_NAME" | cut -f1)"
echo ""
echo "压缩包内容:"
unzip -l "$ZIP_NAME" | grep -E '\.(py|txt|md|pdf|json|png|jpg)$' | head -20
echo ""
echo "请检查压缩包内容后提交！"
echo ""
