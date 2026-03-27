"""
Ko-fi 후원 버튼 자동 삽입
===========================
docs/ 및 scripts/blog/output/ 의 HTML 파일에 Ko-fi 위젯을 삽입합니다.

필요한 환경변수:
  KOFI_USERNAME — Ko-fi 유저명 (예: yourname)
               → https://ko-fi.com/yourname 에서 확인

이미 삽입된 파일은 스킵합니다.
"""

import os
from pathlib import Path

KOFI_USERNAME = os.environ.get("KOFI_USERNAME", "").strip()

KOFI_WIDGET = """
<!-- Ko-fi donation button (auto-injected) -->
<div style="position:fixed;bottom:24px;right:24px;z-index:9999">
  <a href="https://ko-fi.com/{username}" target="_blank" rel="noopener"
     style="display:inline-flex;align-items:center;gap:8px;
            background:#ff5e5b;color:#fff;padding:10px 18px;
            border-radius:24px;text-decoration:none;font-weight:700;
            font-size:14px;font-family:-apple-system,sans-serif;
            box-shadow:0 4px 14px rgba(255,94,91,.45);
            transition:transform .15s,box-shadow .15s"
     onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(255,94,91,.55)'"
     onmouseout="this.style.transform='';this.style.boxShadow='0 4px 14px rgba(255,94,91,.45)'">
    ☕ Buy me a coffee
  </a>
</div>
<!-- /Ko-fi -->
"""

MARKER = "<!-- Ko-fi donation button (auto-injected) -->"


def inject_kofi(html_path: Path) -> bool:
    """HTML 파일에 Ko-fi 버튼 삽입. 이미 있으면 스킵. 반환: 삽입 여부."""
    try:
        content = html_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ✗ 읽기 실패 {html_path.name}: {e}")
        return False

    if MARKER in content:
        return False  # 이미 삽입됨

    widget = KOFI_WIDGET.format(username=KOFI_USERNAME)

    # </body> 바로 앞에 삽입
    if "</body>" in content:
        new_content = content.replace("</body>", widget + "\n</body>", 1)
    else:
        new_content = content + widget

    try:
        html_path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"  ✗ 쓰기 실패 {html_path.name}: {e}")
        return False


def run():
    if not KOFI_USERNAME:
        print("KOFI_USERNAME not set — skipping Ko-fi injection")
        print("  Set KOFI_USERNAME secret to your Ko-fi username (e.g. 'yourname')")
        return

    print(f"\n☕ Ko-fi 버튼 삽입 중... (username: {KOFI_USERNAME})")

    targets = [
        Path("docs"),
        Path("scripts/blog/output"),
    ]

    total = 0
    skipped = 0
    for directory in targets:
        if not directory.exists():
            continue
        for html_file in directory.glob("**/*.html"):
            injected = inject_kofi(html_file)
            if injected:
                print(f"  ✓ {html_file}")
                total += 1
            else:
                skipped += 1

    print(f"\n✅ Ko-fi 삽입 완료: {total}개 파일 업데이트, {skipped}개 이미 삽입됨")


if __name__ == "__main__":
    run()
