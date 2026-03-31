"""
Ko-fi 후원 버튼 자동 삽입
===========================
생성된 모든 HTML 파일에 Ko-fi 후원 버튼을 자동으로 삽입합니다.
"""
import os, re
from pathlib import Path

KOFI_USERNAME = os.environ.get("KOFI_USERNAME", "")
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
BLOG_OUTPUT = Path(__file__).parent.parent / "blog" / "output"

KOFI_WIDGET = """
<div style="text-align:center;margin:20px 0;padding:15px;background:#f8f9fa;border-radius:8px;">
  <a href="https://ko-fi.com/{username}" target="_blank"
     style="background:#FF5E5B;color:#fff;padding:10px 20px;border-radius:5px;text-decoration:none;font-weight:bold;">
    ☕ Buy Me a Coffee on Ko-fi
  </a>
  <p style="margin:8px 0 0;color:#666;font-size:14px;">
    이 콘텐츠가 도움이 됐다면 커피 한 잔 사주세요! 더 좋은 콘텐츠를 만드는 데 씁니다.
  </p>
</div>
"""

def inject_kofi(html: str, username: str) -> str:
    widget = KOFI_WIDGET.format(username=username)
    # </body> 직전에 삽입
    if "</body>" in html:
        return html.replace("</body>", widget + "</body>", 1)
    return html + widget

def run():
    username = KOFI_USERNAME
    if not username:
        print("⏭ KOFI_USERNAME 미설정 — 건너뜀")
        return

    count = 0
    for html_dir in [DOCS_DIR, BLOG_OUTPUT]:
        if not html_dir.exists():
            continue
        for html_file in html_dir.rglob("*.html"):
            try:
                content = html_file.read_text(encoding="utf-8")
                if f"ko-fi.com/{username}" not in content:
                    html_file.write_text(inject_kofi(content, username), encoding="utf-8")
                    count += 1
            except Exception as e:
                print(f"  ⚠ {html_file.name}: {e}")
    print(f"✅ Ko-fi 버튼 삽입: {count}개 파일")

if __name__ == "__main__":
    run()
