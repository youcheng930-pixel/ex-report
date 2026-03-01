#!/bin/bash
cd /Users/bytedance/Desktop/files
/usr/bin/python3 report.py
ls -t fx_report_*.html | head -1 | xargs -I {} cp {} index.html
git add index.html
git commit -m "每日更新"
git push
