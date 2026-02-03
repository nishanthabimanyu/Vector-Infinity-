#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# Vector Infinity Markdown Parser                    #
# Ported from Py-GPT (szczyglis-dev)                 #
# ================================================== #

import markdown
from bs4 import BeautifulSoup
from bs4.element import NavigableString

class Parser:
    def __init__(self):
        """
        Markdown parser core
        """
        self.md = None
        self.code_blocks = {}
        self.block_idx = 1

    def init(self):
        """
        Initialize markdown parser with extensions
        """
        if self.md is None:
            # fenced_code is essential for ```code``` blocks
            self.md = markdown.Markdown(extensions=['fenced_code', 'tables'])

    def reset(self):
        """
        Reset parser state (clear code blocks memory)
        """
        self.code_blocks = {}
        self.block_idx = 1

    def parse(self, text: str) -> str:
        """
        Parse markdown text to HTML
        :param text: markdown text
        :return: html formatted text
        """
        self.init()
        try:
            # Convert MD -> HTML
            html = self.md.convert(text.strip())
            
            # Post-process with BS4 for cleanup and enhancement
            soup = BeautifulSoup(html, 'html.parser')
            self.strip_whitespace_lists(soup)
            self.strip_whitespace_codeblocks(soup)
            self.parse_code_blocks(soup)  # Wrap code blocks with copy/header logic
            
            # TODO: format_images(soup) if we support inline images
            
            return str(soup)
        except Exception as e:
            print(f"[Parser] Error parsing markdown: {e}")
            return text # Fallback to raw text

    def strip_whitespace_lists(self, soup):
        for li in soup.find_all('li'):
            for item in li.contents:
                if isinstance(item, NavigableString) and item.strip() == '':
                    item.replace_with('')

    def strip_whitespace_codeblocks(self, soup):
        for el in soup.find_all('code'):
            if el.string:
                el.string = el.string.strip()

    def parse_code_blocks(self, soup):
        """
        Wraps <pre> blocks in a nice div structure for styling.
        """
        for el in soup.find_all('pre'):
            content = el.get_text(strip=True)
            self.code_blocks[self.block_idx] = content

            # Wrapper
            wrapper = soup.new_tag('div', **{'class': "code-wrapper"})
            
            # Header (Language + Copy)
            header = soup.new_tag('div', **{'class': "code-header"})
            code = el.find('code')
            language = "Code"
            if code and code.has_attr('class'):
                # class is usually ['language-python']
                for cls in code['class']:
                    if cls.startswith('language-'):
                        language = cls.replace('language-', '')
                        break
            
            lang_span = soup.new_tag('span', **{'class': "code-lang"})
            lang_span.string = language.upper()
            header.append(lang_span)
            
            wrapper.append(header)

            # Code Content
            new_pre = soup.new_tag('pre')
            new_code = soup.new_tag('code')
            new_code.string = content
            # Preserve coloring classes if handled by JS, but here we just keep structure
            new_pre.append(new_code)
            
            content_div = soup.new_tag('div', **{'class': "code-content"})
            content_div.append(new_pre)
            wrapper.append(content_div)
            
            el.replace_with(wrapper)
            self.block_idx += 1
