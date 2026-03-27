/**
 * POST /api/generate
 * AutoContent Pro – 콘텐츠 생성 API
 *
 * Request body:
 *   { topic: string, contentTypes: string[], affiliateEnabled: boolean }
 *
 * Plans & Rate Limits (Supabase DB에서 확인):
 *   free:     5 req/월
 *   pro:      50 req/월
 *   business: 무제한
 */

import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { createClient } from "@supabase/supabase-js";
import { runContentPipeline } from "@/lib/pipeline";

const RequestSchema = z.object({
  topic: z.string().min(3).max(200),
  contentTypes: z
    .array(z.enum(["blog", "youtube_script", "social"]))
    .min(1)
    .max(3),
  affiliateEnabled: z.boolean().default(false),
});

const PLAN_LIMITS: Record<string, number> = {
  free: 5,
  pro: 50,
  business: Infinity,
};

// ── 사용량 체크 + 카운트 업 ────────────────────────────────────────────────────
async function checkAndIncrementUsage(userId: string, plan: string): Promise<boolean> {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  const now = new Date();
  const monthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  // 현재 월 사용량 조회
  const { data } = await supabase
    .from("usage")
    .select("count")
    .eq("user_id", userId)
    .eq("month", monthKey)
    .single();

  const currentCount: number = data?.count ?? 0;
  const limit = PLAN_LIMITS[plan] ?? PLAN_LIMITS.free;

  if (currentCount >= limit) return false;

  // 사용량 증가 (upsert)
  await supabase.from("usage").upsert(
    { user_id: userId, month: monthKey, count: currentCount + 1 },
    { onConflict: "user_id,month" }
  );

  return true;
}

export async function POST(req: NextRequest) {
  try {
    // 1. 인증 확인
    const authHeader = req.headers.get("Authorization");
    const token = authHeader?.replace("Bearer ", "");
    if (!token) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) {
      return NextResponse.json({ error: "Invalid token" }, { status: 401 });
    }

    // 2. 플랜 조회
    const { data: profile } = await supabase
      .from("profiles")
      .select("plan")
      .eq("id", user.id)
      .single();
    const plan: string = profile?.plan ?? "free";

    // 3. 요청 유효성 검사
    const body = RequestSchema.safeParse(await req.json());
    if (!body.success) {
      return NextResponse.json({ error: body.error.flatten() }, { status: 400 });
    }

    // 4. 사용량 제한 확인
    const allowed = await checkAndIncrementUsage(user.id, plan);
    if (!plan.includes("business") && !allowed) {
      return NextResponse.json(
        { error: `Monthly limit reached for ${plan} plan. Upgrade to continue.` },
        { status: 429 }
      );
    }

    // 5. 콘텐츠 생성
    const result = await runContentPipeline({
      topic: body.data.topic,
      contentTypes: body.data.contentTypes,
      affiliateEnabled: body.data.affiliateEnabled && plan !== "free",
    });

    // 6. 결과 DB 저장 (히스토리용)
    await supabase.from("generations").insert({
      user_id: user.id,
      topic: body.data.topic,
      content_types: body.data.contentTypes,
      result: result,
    });

    return NextResponse.json({ success: true, data: result });

  } catch (err) {
    console.error("Generation error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
