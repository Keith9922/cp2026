#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全自动iGEM Wiki爬虫
使用Playwright自动获取动态渲染的内容
"""

import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import logging
from pathlib import Path
from typing import List, Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class AutoCrawler:
    """全自动爬虫 - 使用Playwright"""
    
    def __init__(self, base_url: str, images_dir: str = "./images"):
        self.base_url = base_url
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.dataset: List[Dict[str, str]] = []
        
        logging.info(f"图片保存目录: {self.images_dir.absolute()}")
    
    def fetch_page_with_playwright(self, url: str, timeout: int = 60000) -> str:
        """使用Playwright获取动态渲染的页面"""
        logging.info(f"正在加载页面: {url}")
        
        # 重试3次
        for attempt in range(3):
            try:
                with sync_playwright() as p:
                    # 启动浏览器（无头模式）
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    
                    try:
                        # 访问页面，增加超时时间
                        page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                        
                        # 额外等待确保JavaScript渲染完成
                        page.wait_for_timeout(5000)  # 5秒
                        
                        # 获取渲染后的HTML
                        html = page.content()
                        
                        logging.info(f"✓ 成功加载页面 (HTML长度: {len(html)} 字符)")
                        
                        return html
                        
                    except PlaywrightTimeout:
                        if attempt < 2:
                            logging.warning(f"页面加载超时，重试 {attempt + 1}/3")
                            continue
                        else:
                            logging.error(f"页面加载超时: {url}")
                            raise
                    except Exception as e:
                        if attempt < 2:
                            logging.warning(f"加载失败，重试 {attempt + 1}/3: {str(e)}")
                            continue
                        else:
                            logging.error(f"加载页面失败: {str(e)}")
                            raise
                    finally:
                        browser.close()
            except Exception as e:
                if attempt < 2:
                    continue
                raise
    
    def extract_images_from_html(self, html: str, page_url: str) -> None:
        """从HTML中提取图片"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种可能的容器
        containers = []
        
        # 方法1: image-container类
        containers.extend(soup.find_all(class_='image-container'))
        
        # 方法2: figure标签
        if not containers:
            containers.extend(soup.find_all('figure'))
        
        # 方法3: 包含img和caption的div
        if not containers:
            for div in soup.find_all('div'):
                img = div.find('img')
                caption = div.find(['figcaption', 'p', 'span'])
                if img and caption:
                    containers.append(div)
        
        # 方法4: 直接找所有img（最后的兜底方案）
        if not containers:
            logging.warning("未找到标准容器，尝试直接提取所有<img>标签")
            imgs = soup.find_all('img')
            for img in imgs:
                # 过滤掉小图标和logo
                src = img.get('src', '')
                if any(x in src.lower() for x in ['logo', 'icon', 'favicon']):
                    continue
                containers.append(img.parent if img.parent else img)
        
        # 去重
        containers = list(dict.fromkeys(containers))
        
        logging.info(f"找到 {len(containers)} 个图片容器")
        
        for idx, container in enumerate(containers):
            try:
                self._process_container(container, page_url, idx)
            except Exception as e:
                logging.warning(f"处理容器 {idx} 失败: {str(e)}")
                continue
    
    def _process_container(self, container, page_url: str, idx: int) -> None:
        """处理单个图片容器"""
        # 查找img标签
        if container.name == 'img':
            img_tag = container
        else:
            img_tag = container.find('img')
        
        if not img_tag:
            return
        
        # 获取图片URL
        img_src = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-lazy-src')
        if not img_src:
            return
        
        # 过滤data:image格式的内联图片
        if img_src.startswith('data:'):
            return
        
        # 转换为绝对URL
        img_url = urljoin(page_url, img_src)
        
        # 提取描述
        caption = self._extract_caption(container, img_tag)
        
        # 生成文件名
        img_ext = os.path.splitext(urlparse(img_url).path)[1]
        if not img_ext or len(img_ext) > 5:
            img_ext = '.jpg'
        img_name = f"image_{len(self.dataset) + 1:04d}{img_ext}"
        
        # 下载图片
        try:
            img_path = self._download_image(img_url, img_name)
            
            self.dataset.append({
                "image": img_path,
                "caption": caption
            })
            
            logging.info(f"✓ 提取图片 {len(self.dataset)}: {caption[:60]}...")
            
        except Exception as e:
            logging.warning(f"下载图片失败 {img_url}: {str(e)}")
    
    def _extract_caption(self, container, img_tag) -> str:
        """提取图片描述"""
        # 方法1: figcaption
        figcaption = container.find('figcaption')
        if figcaption:
            text = figcaption.get_text(strip=True)
            if text:
                return text
        
        # 方法2: caption类
        caption_elem = container.find(class_=lambda x: x and 'caption' in str(x).lower())
        if caption_elem:
            text = caption_elem.get_text(strip=True)
            if text:
                return text
        
        # 方法3: alt属性
        alt = img_tag.get('alt', '').strip()
        if alt and len(alt) > 3:
            return alt
        
        # 方法4: title属性
        title = img_tag.get('title', '').strip()
        if title and len(title) > 3:
            return title
        
        # 方法5: 相邻的p或span
        next_sibling = container.find_next_sibling(['p', 'span', 'div'])
        if next_sibling:
            text = next_sibling.get_text(strip=True)
            if text and len(text) < 200:
                return text
        
        return "No description available"
    
    def _download_image(self, img_url: str, img_name: str) -> str:
        """下载图片到本地"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        response = session.get(img_url, timeout=30, stream=True)
        response.raise_for_status()
        
        img_path = self.images_dir / img_name
        with open(img_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return f"./images/{img_name}"
    
    def save_dataset(self, output_file: str = "dataset.json"):
        """保存数据集"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.dataset, f, ensure_ascii=False, indent=2)
        
        logging.info(f"数据集已保存: {output_file}，共 {len(self.dataset)} 条记录")
    
    def crawl_pages(self, urls: List[str]):
        """爬取多个页面"""
        logging.info(f"开始爬取 {len(urls)} 个页面...")
        
        for i, url in enumerate(urls, 1):
            try:
                logging.info(f"\n[{i}/{len(urls)}] 处理页面: {url}")
                
                # 获取页面HTML
                html = self.fetch_page_with_playwright(url)
                
                # 提取图片
                self.extract_images_from_html(html, url)
                
                # 避免请求过快
                if i < len(urls):
                    time.sleep(2)
                    
            except Exception as e:
                logging.error(f"处理页面 {url} 失败: {str(e)}")
                continue
        
        # 保存结果
        self.save_dataset()
        
        # 输出统计
        logging.info("\n" + "="*60)
        logging.info("✓ 爬取完成！")
        logging.info(f"  访问页面数: {len(urls)}")
        logging.info(f"  下载图片数: {len(self.dataset)}")
        logging.info(f"  图片保存位置: {self.images_dir.absolute()}")
        logging.info(f"  数据集文件: dataset.json")
        logging.info("="*60)


def main():
    """主函数"""
    print("="*60)
    print("全自动iGEM Wiki爬虫")
    print("="*60)
    print()
    
    BASE_URL = "https://2025.igem.wiki/jlu-cp/"
    
    # iGEM标准页面列表
    PAGES = [
        "https://2025.igem.wiki/jlu-cp/",
        "https://2025.igem.wiki/jlu-cp/description",
        "https://2025.igem.wiki/jlu-cp/design",
        "https://2025.igem.wiki/jlu-cp/experiments",
        "https://2025.igem.wiki/jlu-cp/results",
        "https://2025.igem.wiki/jlu-cp/engineering",
        "https://2025.igem.wiki/jlu-cp/notebook",
        "https://2025.igem.wiki/jlu-cp/team",
        "https://2025.igem.wiki/jlu-cp/attributions",
        "https://2025.igem.wiki/jlu-cp/safety",
        "https://2025.igem.wiki/jlu-cp/human-practices",
        "https://2025.igem.wiki/jlu-cp/contribution",
        "https://2025.igem.wiki/jlu-cp/model",
        "https://2025.igem.wiki/jlu-cp/implementation",
        "https://2025.igem.wiki/jlu-cp/proof-of-concept",
        "https://2025.igem.wiki/jlu-cp/parts",
    ]
    
    print(f"将爬取 {len(PAGES)} 个页面")
    print()
    print("优势:")
    print("  ✓ 完全自动化，无需手动操作")
    print("  ✓ 使用Playwright，自带浏览器驱动")
    print("  ✓ 可以获取JavaScript动态渲染的内容")
    print("  ✓ 稳定快速")
    print()
    print("开始爬取...")
    print()
    
    # 创建爬虫并运行
    crawler = AutoCrawler(BASE_URL)
    crawler.crawl_pages(PAGES)


if __name__ == "__main__":
    main()
