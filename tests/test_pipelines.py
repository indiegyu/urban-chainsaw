"""
파이프라인 스크립트 스모크 테스트
=================================
실제 스크립트를 가짜 LLM 서버에 붙여서 실행합니다(서브프로세스).
  - 정상일 때 산출물이 실제로 생기고 exit 0
  - LLM이 죽었을 때 exit 1 (거짓 성공 방지)
  - Pod: 0/5 디자인인데 초록불이던 문제 회귀 방지

각 테스트는 임시 디렉터리에 scripts/ 를 복사해 실행하므로 저장소를 오염시키지 않습니다.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, paths := str(ROOT / "tests"))

from mock_llm import MockLLM, gemini_ok  # noqa: E402

ENV_KEYS = [
    "GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_API_BASE", "GEMINI_MIN_INTERVAL",
    "GROQ_API_KEY", "GROQ_API_BASE", "OPENROUTER_API_KEY",
    "LLM_PROVIDER_ORDER", "LLM_MAX_RETRIES", "LLM_MAX_BACKOFF",
    "YOUTUBE_CHANNEL_URL", "GITHUB_STEP_SUMMARY", "HEALTH_LOG_PATH",
]

IGNORE = shutil.ignore_patterns(
    "output", "output_shorts", "notion_templates", "__pycache__", "*.mp4", "*.mp3", "*.png"
)


class PipelineTestBase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ENV_KEYS}
        for key in ENV_KEYS:
            os.environ.pop(key, None)
        self.tmp = Path(tempfile.mkdtemp(prefix="uc-test-"))
        shutil.copytree(ROOT / "scripts", self.tmp / "scripts", ignore=IGNORE)
        (self.tmp / "docs").mkdir()
        self.servers: list[MockLLM] = []

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for server in self.servers:
            server.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def mock(self, responses) -> MockLLM:
        server = MockLLM(responses)
        self.servers.append(server)
        os.environ["GEMINI_API_KEY"] = "test-key-abcdef"
        os.environ["GEMINI_API_BASE"] = server.url
        os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
        os.environ["GEMINI_MIN_INTERVAL"] = "0"
        os.environ["LLM_MAX_BACKOFF"] = "1"
        return server

    def run_script(self, rel_path: str, *args: str, timeout: int = 120):
        env = {**os.environ}
        env["PYTHONPATH"] = str(self.tmp / "scripts")
        return subprocess.run(
            [sys.executable, str(self.tmp / rel_path), *args],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )


class PodTests(PipelineTestBase):
    def test_zero_designs_fails_loudly(self):
        self.mock({"*": [(401, {"error": {"message": "Unauthorized"}})]})
        result = self.run_script("scripts/pod/generate_designs.py", "2")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("0/2", result.stdout)

    def test_designs_created(self):
        payload = {
            "main_text": "COFFEE FIRST",
            "sub_text": "questions later",
            "title": "Coffee Lover Funny T-Shirt Gift",
            "tags": ["coffee", "funny"],
            "description": "A funny coffee shirt. Great gift. Ships fast.",
        }
        self.mock({"*": [(200, gemini_ok(json.dumps(payload)))]})
        result = self.run_script("scripts/pod/generate_designs.py", "2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        files = list((self.tmp / "scripts" / "pod" / "output").glob("*.png"))
        self.assertEqual(len(files), 2, result.stdout)
        self.assertIn("2/2", result.stdout)


class BlogTests(PipelineTestBase):
    def test_blog_generates_files(self):
        meta = {"title": "7 AI Side Hustles", "slug": "ai-side-hustles",
                "meta_description": "desc", "tags": ["ai", "money"]}
        self.mock({"*": [(200, gemini_ok(json.dumps(meta))),
                         (200, gemini_ok("<p>Body text for the post.</p>"))]})
        result = self.run_script("scripts/blog/generate_post.py", "AI side hustles")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        html_files = list((self.tmp / "scripts" / "blog" / "output").glob("*.html"))
        self.assertEqual(len(html_files), 1, result.stdout)
        html = html_files[0].read_text()
        self.assertIn("Body text", html)
        # 죽은 채널 링크가 들어가지 않아야 함
        self.assertNotIn("psg9806", html)
        self.assertNotIn("@AIIncomeDaily", html)

    def test_blog_fails_when_llm_dead(self):
        self.mock({"*": [(500, {"error": {"message": "boom"}})]})
        os.environ["LLM_MAX_RETRIES"] = "0"
        result = self.run_script("scripts/blog/generate_post.py", "anything")
        self.assertNotEqual(result.returncode, 0)


class VideoTests(PipelineTestBase):
    def test_video_script_generation_with_mock(self):
        meta = {"title": "Make $500 with AI", "description": "d",
                "tags": ["ai"], "thumbnail_text": "$500 AI"}
        self.mock({"*": [(200, gemini_ok(json.dumps(meta))),
                         (200, gemini_ok("Spoken narration here."))]})
        code = (
            "import sys; sys.path.insert(0, r'%s')\n"
            "from video.assemble_video import generate_script\n"
            "m = generate_script('Make money with AI')\n"
            "assert m['title'] == 'Make $500 with AI', m\n"
            "assert m['script'] == 'Spoken narration here.', m\n"
            "print('VIDEO_OK')\n" % str(self.tmp / "scripts")
        )
        env = {**os.environ, "PYTHONPATH": str(self.tmp / "scripts")}
        result = subprocess.run([sys.executable, "-c", code], cwd=str(self.tmp),
                                capture_output=True, text=True, timeout=120, env=env)
        self.assertIn("VIDEO_OK", result.stdout, result.stdout + result.stderr)

    def test_short_script_generation_with_mock(self):
        meta = {"title": "Free AI money hack 🤯 #Shorts", "thumbnail_text": "FREE AI MONEY",
                "tags": ["Shorts", "AI"]}
        self.mock({"*": [(200, gemini_ok(json.dumps(meta))),
                         (200, gemini_ok("Here is the shorts narration."))]})
        code = (
            "import sys; sys.path.insert(0, r'%s')\n"
            "from video.assemble_shorts import generate_shorts_script\n"
            "m = generate_shorts_script()\n"
            "assert '#Shorts' in m['title'], m\n"
            "assert 'Shorts' in m['description']\n"
            "print('SHORTS_OK')\n" % str(self.tmp / "scripts")
        )
        env = {**os.environ, "PYTHONPATH": str(self.tmp / "scripts")}
        result = subprocess.run([sys.executable, "-c", code], cwd=str(self.tmp),
                                capture_output=True, text=True, timeout=120, env=env)
        self.assertIn("SHORTS_OK", result.stdout, result.stdout + result.stderr)


TOOL_DESCRIPTIONS = json.dumps([
    {"name": "Ideogram", "description": "Free AI image tool for POD designs. Start a shirt shop with zero cost.",
     "money_use_case": "$20/mo selling AI art prints", "best_for": "POD beginners"},
    {"name": "Groq", "description": "Fast free LLM API for automation. Great for content pipelines.",
     "money_use_case": "$500/mo automating client blogs", "best_for": "automation builders"},
])


class SiteLinkTests(PipelineTestBase):
    def test_no_channel_link_without_config(self):
        self.mock({"*": [(200, gemini_ok(TOOL_DESCRIPTIONS))]})
        result = self.run_script("scripts/publish/tools_directory.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        html = (self.tmp / "docs" / "ai-tools.html").read_text()
        self.assertNotIn("psg9806", html)
        self.assertNotIn("youtube.com/@", html)

    def test_channel_link_used_when_configured(self):
        os.environ["YOUTUBE_CHANNEL_URL"] = "https://www.youtube.com/@myrealchannel"
        self.mock({"*": [(200, gemini_ok(TOOL_DESCRIPTIONS))]})
        result = self.run_script("scripts/publish/tools_directory.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        html = (self.tmp / "docs" / "ai-tools.html").read_text()
        self.assertIn("https://www.youtube.com/@myrealchannel", html)


if __name__ == "__main__":
    unittest.main()
