#!/usr/bin/env python3
"""Generate '50 ChatGPT Prompts for YouTube Creators' PDF product"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

OUTPUT = "/Users/smp/projects/urban-chainsaw/products/50-chatgpt-prompts-youtube.pdf"

prompts = [
    # === NICHE & STRATEGY (1-8) ===
    ("1", "Niche Finder",
     'Act as a YouTube niche consultant. List 10 profitable faceless YouTube niches for 2026 that have: high RPM (>$5), low competition, and evergreen content potential. For each niche, give: niche name, example channel name, content angle, and estimated monthly earnings at 100K views.'),
    ("2", "Competitor Analysis",
     'Analyze the YouTube niche "[NICHE]". List the top 5 channels, their upload frequency, average views per video, content style, and identify 3 content gaps I could exploit as a new creator.'),
    ("3", "Channel Name Generator",
     'Generate 15 memorable YouTube channel names for a faceless channel in the "[NICHE]" space. Names should be: easy to spell, brandable, available as .com domain likely, and suggest authority/value.'),
    ("4", "Content Pillar Strategy",
     'Create a 4-pillar content strategy for a YouTube channel about "[NICHE]". For each pillar: name, goal, 5 video ideas, and how it fits the monetization funnel (awareness → trust → sale).'),
    ("5", "30-Day Content Calendar",
     'Build a 30-day YouTube content calendar for a faceless channel in "[NICHE]". Include: video title, thumbnail concept (1 sentence), target keyword, and whether it is evergreen or trending. Format as a table.'),
    ("6", "Viral Hook Formula",
     'Give me 20 proven YouTube video hook templates that get viewers to watch past the first 30 seconds. For each hook: the template, a fill-in example for the "[NICHE]" niche, and why it works psychologically.'),
    ("7", "Title Optimizer",
     'I have this YouTube video title: "[TITLE]". Rewrite it 10 different ways optimized for: click-through rate, SEO, and curiosity. Mark the top 3 with reasons why they outperform the original.'),
    ("8", "Thumbnail Concept Generator",
     'Create 5 thumbnail concepts for a YouTube video titled "[TITLE]". For each concept describe: background color scheme, main visual element, text overlay (max 4 words), and the emotion it triggers in the viewer.'),

    # === SCRIPT WRITING (9-18) ===
    ("9", "Full Video Script",
     'Write a complete YouTube video script for a 10-minute faceless video titled "[TITLE]". Structure: Hook (0-30s) → Problem Agitation (30s-2min) → Solution Overview (2-4min) → Step-by-Step Tutorial (4-9min) → CTA (9-10min). Use conversational language, short sentences, no filler words.'),
    ("10", "Hook Writer",
     'Write 10 different video hooks for the title "[TITLE]". Each hook should be 2-3 sentences max, create curiosity or urgency, and make the viewer feel the video is made specifically for them. Label each with the psychological trigger used.'),
    ("11", "Script to Bullet Points",
     'Convert this rough script into clean bullet points for a teleprompter. Keep the natural conversational flow but remove filler words, repetition, and off-topic tangents. Target: 150 words per minute pace.\n\n[PASTE SCRIPT HERE]'),
    ("12", "Storytelling Arc Builder",
     'I am making a YouTube video about "[TOPIC]". Create a compelling story arc that: starts with a relatable struggle, builds tension, delivers a surprising insight, and ends with an actionable takeaway. The story should work for a faceless narration style.'),
    ("13", "FAQ Video Script",
     'Write a 7-minute YouTube script answering the top 10 most asked questions about "[TOPIC]". For each question: give a direct answer (2-3 sentences), a memorable analogy, and a practical example. Tone: friendly expert.'),
    ("14", "Comparison Video Script",
     'Write a YouTube script comparing [OPTION A] vs [OPTION B] for "[AUDIENCE]". Structure: brief intro → criteria setup (4 criteria) → head-to-head comparison → verdict with nuance → viewer action. Be balanced but give a clear recommendation.'),
    ("15", "Listicle Script",
     'Write a YouTube script for "Top 10 [TOPIC] in 2026". Each item should have: a punchy title, 2-3 sentences of explanation, one specific stat or example, and a transition to the next item. Total length: 8 minutes. Add a suspense tease for #1 at the start.'),
    ("16", "Tutorial Script",
     'Write a step-by-step tutorial YouTube script for "[HOW TO DO X]". Target audience: complete beginners. Include: what they will need, numbered steps with screen action cues [marked in brackets], common mistakes to avoid, and a results expectation. Length: 12 minutes.'),
    ("17", "Controversial Opinion Video",
     'Write a nuanced YouTube script where I argue that "[CONTROVERSIAL STATEMENT ABOUT NICHE]" is actually true. Structure: acknowledge the mainstream view → present 3 data-backed counterpoints → show real examples → give a balanced conclusion. Tone: thoughtful, not clickbait.'),
    ("18", "Story-Driven Case Study",
     'Write a YouTube script as a case study of "[PERSON/CHANNEL/BUSINESS]" achieving "[RESULT]" in "[TIMEFRAME]". Use the narrative structure: starting point → key decisions → obstacles → breakthrough → current results → lessons the viewer can steal. Length: 15 minutes.'),

    # === SEO & OPTIMIZATION (19-26) ===
    ("19", "Keyword Research",
     'Act as a YouTube SEO expert. For the topic "[TOPIC]", provide: 5 high-volume main keywords, 10 long-tail keywords (lower competition), 5 question-based keywords, and the search intent behind each. Estimate relative competition as Low/Medium/High.'),
    ("20", "Description Writer",
     'Write a YouTube video description for a video titled "[TITLE]". Include: a 2-sentence hook (first 125 characters are critical for SEO), 3-paragraph summary with natural keyword placement, timestamps (create realistic ones), 5 relevant hashtags, and a soft CTA to subscribe. Target keyword: "[KEYWORD]".'),
    ("21", "Tags Generator",
     'Generate the optimal YouTube tags list for a video about "[TOPIC]" targeting the keyword "[KEYWORD]". Provide: 5 exact-match tags, 5 broad-match tags, 5 competitor channel name tags (if relevant), and 5 niche community tags. Explain the tagging strategy.'),
    ("22", "Chapter Timestamps",
     'I have a YouTube video script about "[TOPIC]" with these main sections: [LIST SECTIONS]. Create YouTube chapter timestamps that maximize retention. Each chapter title should be: curiosity-driven, under 30 characters, and hint at value without spoiling it.'),
    ("23", "A/B Title Test",
     'I want to A/B test YouTube titles for my video about "[TOPIC]". Create 2 title variants: Version A optimized for SEO (includes keyword early), Version B optimized for CTR (curiosity-driven). For each: predicted CTR psychology, best audience segment, and when to use it.'),
    ("24", "End Screen Script",
     'Write the last 30 seconds of a YouTube video script that maximizes: subscribe rate, click-through to another video, and email list opt-in. The channel is about "[NICHE]". Include specific verbal CTAs timed to visual end-screen elements.'),
    ("25", "Community Post Ideas",
     'Generate 20 YouTube Community post ideas for a channel about "[NICHE]". Mix of: polls (5), text updates (5), image post concepts (5), and behind-the-scenes type posts (5). Each should drive comments and strengthen the viewer-creator relationship.'),
    ("26", "Playlist Strategy",
     'Design a YouTube playlist strategy for a channel in "[NICHE]". Recommend 6 playlist names, the theme of each, which 5 video types go in each, and how they guide viewers from discovery → subscriber → customer. Explain the watch-time benefit.'),

    # === MONETIZATION (27-34) ===
    ("27", "Digital Product Ideas",
     'I have a YouTube channel about "[NICHE]" with [X] subscribers. Suggest 10 digital products I could sell to my audience, ranked by: effort to create, price point, and probability of selling. For each: product type, title, price, and which video content leads to it naturally.'),
    ("28", "Affiliate Integration",
     'I am making a YouTube video about "[TOPIC]". Suggest 5 affiliate products that naturally fit this content. For each: product name, commission rate (research or estimate), how to naturally mention it in the script (exact line), and the ideal placement in the video timeline.'),
    ("29", "Sponsorship Pitch Email",
     'Write a cold outreach email to sponsor "[BRAND NAME]" for my YouTube channel about "[NICHE]". My channel stats: [SUBSCRIBERS] subscribers, [VIEWS] average views, [DEMOGRAPHICS]. The email should: open with their benefit (not mine), show audience-brand fit, propose a specific collaboration, and include a soft CTA. Length: under 200 words.'),
    ("30", "Membership Tier Design",
     'Design a YouTube Membership tier structure for a channel about "[NICHE]" with [X] subscribers. Create 3 tiers: entry ($2.99), mid ($7.99), premium ($19.99). For each tier: name, 4-5 perks, how to deliver each perk, and the psychological hook that makes each tier feel like a "deal".'),
    ("31", "Product Launch Script",
     'Write a 5-minute YouTube video script announcing my new digital product "[PRODUCT NAME]" priced at $[PRICE]. Structure: establish the problem → agitate with a story → introduce the product → show social proof → handle 3 objections → urgency close → link in description CTA. No sleazy sales language.'),
    ("32", "Niche Site Monetization Map",
     'Create a complete monetization map for a YouTube channel about "[NICHE]". Show every revenue stream possible: AdSense (estimate RPM), affiliate (3 programs), digital products (3 ideas), sponsorships (typical rates for channel size), memberships, and consulting/services. Prioritize by passive income potential.'),
    ("33", "Lead Magnet Script",
     'I want to grow my email list through my YouTube channel about "[NICHE]". Create a lead magnet offer: name the freebie, describe what is inside (specific), write the verbal script I use to mention it in videos (30 seconds), and design the landing page headline and 3 bullet points.'),
    ("34", "Patreon vs YouTube Membership",
     'Compare Patreon vs YouTube Memberships for a creator in the "[NICHE]" space with [X] subscribers. Consider: fees, features, audience friction, discoverability, and perk delivery. Give a clear recommendation with a transition plan.'),

    # === AUTOMATION & TOOLS (35-42) ===
    ("35", "AI Voiceover Prompt",
     'I need to record a voiceover using ElevenLabs AI for a YouTube video about "[TOPIC]". Write the script in a style optimized for AI text-to-speech: short sentences (under 15 words), no complex punctuation, natural breathing pauses marked as [...], and emphasis words CAPITALIZED. Length: 8 minutes (approximately 1,200 words).'),
    ("36", "B-Roll Shot List",
     'Create a detailed B-roll shot list for a 10-minute YouTube video about "[TOPIC]". For each section of the script, list: 3 Pexels/Pixabay search terms to find relevant footage, the shot duration needed, and a description of the visual transition. Total: 30 B-roll suggestions.'),
    ("37", "Automation Stack Design",
     'Design a complete automation stack for a faceless YouTube channel in "[NICHE]". Map every step from idea → published video, identifying: free tools for each step, time each step takes manually vs automated, and which steps absolutely require human review. Output as a flowchart description.'),
    ("38", "Repurposing Plan",
     'I just published a YouTube video about "[TOPIC]". Create a full content repurposing plan: 1 blog post (outline), 3 YouTube Shorts concepts, 5 Twitter/X threads, 2 LinkedIn posts, 1 email newsletter, and 1 Reddit post. For each, note the platform-specific angle and optimal posting time.'),
    ("39", "Shorts Script",
     'Write 5 YouTube Shorts scripts based on the concept "[TOPIC]". Each short should be: 45-60 seconds, open with a pattern-interrupt first line, deliver one insight or tip, and end with a subscribe hook. Format: [Hook], [Content], [CTA].'),
    ("40", "Batch Recording Session Plan",
     'I have 4 hours to batch record 8 YouTube videos for my channel about "[NICHE]". Create an optimized recording session plan: script order to minimize mental fatigue, preparation checklist, recording tips for AI voiceover vs screen capture, quality check list, and a realistic timeline.'),
    ("41", "Channel Analytics Review Prompt",
     'I will paste my YouTube analytics data below. Analyze it and tell me: my top 3 performing content types and why, my 3 worst performers and what to change, the optimal upload day/time based on the data, one counterintuitive insight, and my single highest-leverage action for next month.\n\n[PASTE ANALYTICS DATA]'),
    ("42", "n8n Workflow Design",
     'Design an n8n automation workflow for a YouTube content pipeline. The workflow should: trigger on a schedule → generate a video topic using an AI API → create a script → generate a thumbnail prompt → save all to a Google Sheet for review. Describe each node, its configuration, and the data it passes forward.'),

    # === GROWTH & COMMUNITY (43-50) ===
    ("43", "Comment Response Templates",
     'Create 15 YouTube comment response templates for a channel about "[NICHE]". Include responses for: genuine praise (3), constructive criticism (3), questions about your content (3), negative/troll comments (3, non-defensive), and collaboration requests (3). Tone: authentic, not corporate.'),
    ("44", "Collab Pitch Script",
     'Write a DM/email script to propose a YouTube collaboration with a creator in the "[NICHE]" space who has [X] subscribers (similar to my [Y] subscribers). Structure: genuine compliment → specific overlap → clear collaboration format → mutual benefit → easy yes/no ask. Under 150 words.'),
    ("45", "Sub 1000 Growth Hack",
     'I have a brand new YouTube channel about "[NICHE]" with 0 subscribers. Give me a week-by-week 90-day action plan to reach 1,000 subscribers. Focus only on organic, free strategies. Include: content strategy, community engagement tactics, cross-platform moves, and one unconventional tactic most new creators miss.'),
    ("46", "Viewer Retention Script Fix",
     'My YouTube video has a 35% average view duration. Here is the script section where viewers are dropping off: "[PASTE SECTION]". Rewrite this section to: re-hook the viewer, deliver the promised value faster, eliminate fluff, and add a curiosity bridge to the next section.'),
    ("47", "Channel Audit Prompt",
     'Perform a YouTube channel audit for a channel with these characteristics: niche = "[NICHE]", subscribers = [X], average views = [Y], upload frequency = [Z]. Identify the top 3 bottlenecks preventing growth, give 5 specific actionable improvements, and prioritize them by impact/effort ratio.'),
    ("48", "Viral Short-Form Hook Bank",
     'Create a bank of 30 viral YouTube Shorts opening lines for the niche "[NICHE]". Categorize them into: curiosity gaps (10), shocking stats (10), and controversial opinions (10). Each opening line should work in under 3 seconds and make viewers want to watch the full short.'),
    ("49", "Subscriber Milestone Plan",
     'I am at [X] YouTube subscribers. Create a subscriber milestone roadmap: 100 → 1K → 10K → 100K → 1M. For each milestone: key metrics to optimize, content strategy shift, monetization unlocked, time estimate (realistic), and the single biggest mistake creators make at that stage.'),
    ("50", "Full Channel Launch Plan",
     'I want to launch a faceless YouTube channel about "[NICHE]" from scratch. Create a complete 90-day launch plan: Week 1-2 (setup and preparation), Week 3-4 (first 4 videos strategy), Month 2 (consistency and optimization), Month 3 (growth hacks and monetization prep). Include specific tools, daily time commitment, and success metrics for each phase.'),
]

def build_pdf():
    doc = SimpleDocTemplate(OUTPUT, pagesize=letter,
                            rightMargin=0.8*inch, leftMargin=0.8*inch,
                            topMargin=0.8*inch, bottomMargin=0.8*inch)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=26, textColor=colors.HexColor('#1e1b4b'),
                                  spaceAfter=6, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                     fontSize=13, textColor=colors.HexColor('#6366f1'),
                                     spaceAfter=20, alignment=TA_CENTER)
    category_style = ParagraphStyle('Category', parent=styles['Heading1'],
                                     fontSize=14, textColor=colors.HexColor('#fff'),
                                     backColor=colors.HexColor('#312e81'),
                                     spaceBefore=20, spaceAfter=10,
                                     leftIndent=-6, rightIndent=-6,
                                     borderPad=8)
    num_style = ParagraphStyle('Num', parent=styles['Normal'],
                                fontSize=10, textColor=colors.HexColor('#6366f1'),
                                fontName='Helvetica-Bold')
    prompt_title_style = ParagraphStyle('PromptTitle', parent=styles['Normal'],
                                         fontSize=12, fontName='Helvetica-Bold',
                                         textColor=colors.HexColor('#0f172a'),
                                         spaceBefore=8, spaceAfter=4)
    prompt_body_style = ParagraphStyle('PromptBody', parent=styles['Normal'],
                                        fontSize=9.5, textColor=colors.HexColor('#334155'),
                                        spaceAfter=12, leading=14,
                                        backColor=colors.HexColor('#f8fafc'),
                                        leftIndent=10, rightIndent=10,
                                        borderPad=6)
    footer_note_style = ParagraphStyle('FooterNote', parent=styles['Normal'],
                                        fontSize=9, textColor=colors.HexColor('#94a3b8'),
                                        alignment=TA_CENTER, spaceBefore=30)

    story = []

    # Cover
    story.append(Spacer(1, 0.4*inch))
    story.append(Paragraph("50 ChatGPT Prompts", title_style))
    story.append(Paragraph("for YouTube Creators", title_style))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Copy-paste prompts to script, optimize, monetize & grow your faceless channel in 2026", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#6366f1'), spaceAfter=16))

    intro_style = ParagraphStyle('Intro', parent=styles['Normal'],
                                  fontSize=10.5, textColor=colors.HexColor('#334155'),
                                  leading=16, spaceAfter=8)
    story.append(Paragraph(
        "These 50 battle-tested ChatGPT prompts cover every stage of the YouTube creator workflow — "
        "from niche research and scriptwriting to SEO, monetization, and automation. "
        "Replace the <b>[BRACKETS]</b> with your specific details for instant results.", intro_style))
    story.append(Paragraph(
        "Works with: ChatGPT (GPT-4o), Claude, Gemini, and any instruction-following AI.", intro_style))
    story.append(Spacer(1, 0.1*inch))

    # Table of contents summary
    toc_data = [
        ["Section", "Prompts", "Pages"],
        ["🎯 Niche & Strategy", "#1–8", "Strategy, calendars, titles, thumbnails"],
        ["✍️ Script Writing", "#9–18", "Full scripts, hooks, tutorials, case studies"],
        ["📈 SEO & Optimization", "#19–26", "Keywords, descriptions, tags, chapters"],
        ["💰 Monetization", "#27–34", "Products, affiliates, memberships, sponsors"],
        ["🤖 Automation & Tools", "#35–42", "Voiceover, B-roll, repurposing, n8n"],
        ["🚀 Growth & Community", "#43–50", "Collab, audits, milestone plans"],
    ]
    toc_table = Table(toc_data, colWidths=[1.5*inch, 0.9*inch, 4.1*inch])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e1b4b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 0.2*inch))

    # Categories
    categories = [
        ("🎯 SECTION 1: Niche & Strategy (Prompts 1–8)", range(0, 8)),
        ("✍️ SECTION 2: Script Writing (Prompts 9–18)", range(8, 18)),
        ("📈 SECTION 3: SEO & Optimization (Prompts 19–26)", range(18, 26)),
        ("💰 SECTION 4: Monetization (Prompts 27–34)", range(26, 34)),
        ("🤖 SECTION 5: Automation & Tools (Prompts 35–42)", range(34, 42)),
        ("🚀 SECTION 6: Growth & Community (Prompts 43–50)", range(42, 50)),
    ]

    for cat_title, prange in categories:
        story.append(Paragraph(cat_title, category_style))
        for i in prange:
            num, ptitle, body = prompts[i]
            story.append(Paragraph(f"<b>#{num} — {ptitle}</b>", prompt_title_style))
            story.append(Paragraph(body.replace('\n', '<br/>'), prompt_body_style))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=10))
    story.append(Paragraph(
        "© 2026 AI Income Daily | YouTube Automation Playbook Bundle\n"
        "For personal use. Share this PDF = share the knowledge. 🙌", footer_note_style))

    doc.build(story)
    print(f"PDF generated: {OUTPUT}")

if __name__ == "__main__":
    build_pdf()
