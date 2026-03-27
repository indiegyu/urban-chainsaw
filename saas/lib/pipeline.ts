/**
 * Phase 4 – AutoContent Pro 핵심 파이프라인
 * ==========================================
 * Phase 1~3에서 구축한 자동화 로직을 Next.js API로 감싸
 * 외부 사용자에게 SaaS로 제공합니다.
 *
 * 수익 모델:
 *   Free:     5 콘텐츠/월 (광고 포함)
 *   Pro $29/월: 50 콘텐츠/월 + YouTube 업로드 자동화
 *   Business $99/월: 무제한 + Affiliate 자동화 + 우선 지원
 */

import Groq from "groq-sdk";

// ── 타입 정의 ─────────────────────────────────────────────────────────────────
export interface ContentRequest {
  topic: string;
  contentTypes: ("blog" | "youtube_script" | "social")[];
  affiliateEnabled: boolean;
}

export interface ContentResult {
  blogPost?: { title: string; html: string; slug: string; metaDescription: string; tags: string[] };
  youtubeScript?: { title: string; script: string; description: string; tags: string[]; thumbnailPrompt: string };
  socialPosts?: { twitter: string; linkedin: string };
}

// ── Groq 클라이언트 ──────────────────────────────────────────────────────────
function getGroqClient(): Groq {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) throw new Error("GROQ_API_KEY is not set");
  return new Groq({ apiKey });
}

// ── 블로그 포스트 생성 ────────────────────────────────────────────────────────
export async function generateBlogPost(
  topic: string,
  affiliateEnabled: boolean
): Promise<ContentResult["blogPost"]> {
  const groq = getGroqClient();

  const affiliateInstruction = affiliateEnabled
    ? "Add 2-3 natural affiliate link placeholders as {{AFFILIATE:product_name}} where relevant."
    : "";

  const response = await groq.chat.completions.create({
    model: "llama-3.3-70b-versatile",
    temperature: 0.7,
    messages: [
      {
        role: "system",
        content: `You are an expert SEO content writer. Write an 800-1200 word blog post in HTML.
Include: H1 title, engaging intro, 3-4 H2 sections, conclusion with CTA.
${affiliateInstruction}
Output strict JSON: {"title":"...","slug":"...","html":"...","metaDescription":"...","tags":["..."]}`,
      },
      { role: "user", content: `Write about: ${topic}` },
    ],
  });

  const raw = response.choices[0].message.content ?? "{}";
  return JSON.parse(raw);
}

// ── YouTube 스크립트 생성 ─────────────────────────────────────────────────────
export async function generateYouTubeScript(
  topic: string
): Promise<ContentResult["youtubeScript"]> {
  const groq = getGroqClient();

  const response = await groq.chat.completions.create({
    model: "llama-3.3-70b-versatile",
    temperature: 0.8,
    messages: [
      {
        role: "system",
        content: `You are a YouTube scriptwriter for faceless channels.
Write a 1000-1200 word engaging script (7-8 min).
Output strict JSON: {"title":"...","script":"...","description":"...","tags":["..."],"thumbnailPrompt":"..."}`,
      },
      { role: "user", content: `Topic: ${topic}` },
    ],
  });

  const raw = response.choices[0].message.content ?? "{}";
  return JSON.parse(raw);
}

// ── SNS 포스팅 생성 ──────────────────────────────────────────────────────────
export async function generateSocialPosts(
  topic: string,
  blogTitle?: string
): Promise<ContentResult["socialPosts"]> {
  const groq = getGroqClient();

  const response = await groq.chat.completions.create({
    model: "llama-3.3-70b-versatile",
    temperature: 0.9,
    messages: [
      {
        role: "system",
        content: `Generate social media posts. Twitter: max 280 chars with hashtags. LinkedIn: 150 words professional tone.
Output JSON: {"twitter":"...","linkedin":"..."}`,
      },
      {
        role: "user",
        content: `Topic: ${topic}${blogTitle ? `. Blog title: ${blogTitle}` : ""}`,
      },
    ],
  });

  const raw = response.choices[0].message.content ?? "{}";
  return JSON.parse(raw);
}

// ── 통합 파이프라인 ──────────────────────────────────────────────────────────
export async function runContentPipeline(req: ContentRequest): Promise<ContentResult> {
  const result: ContentResult = {};

  await Promise.all([
    req.contentTypes.includes("blog") &&
      generateBlogPost(req.topic, req.affiliateEnabled).then((r) => { result.blogPost = r; }),
    req.contentTypes.includes("youtube_script") &&
      generateYouTubeScript(req.topic).then((r) => { result.youtubeScript = r; }),
    req.contentTypes.includes("social") &&
      generateSocialPosts(req.topic).then((r) => { result.socialPosts = r; }),
  ]);

  return result;
}
