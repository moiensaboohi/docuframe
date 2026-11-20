# Platform policies — checked 2026-11-20

These rules change often. Re-check before each release; the skill's defaults below are built from this file.

## YouTube

**Monetisation — "inauthentic" / generic or repetitive content**
- July 15, 2025: YouTube renamed "repetitious content" to "inauthentic content" and clarified it covers mass-produced or repetitive content. (support.google.com/youtube/answer/1311392)
- July 2026: guidance re-cut into three non-monetisable categories — (1) generic or repetitive content, (2) unsatisfying or off-putting content, (3) AI personas on sensitive topics. YouTube says the rules themselves did not change. (Tubefilter 2026-07-13; TechCrunch 2026-07-20)
- The help page: generic or repetitive content includes content that looks template-made or feels repetitive after watching several videos from the same channel. **The policy applies to the channel as a whole.** Reviewers look at videos, channel description, titles.
- Narrated stories/slideshows with only superficial differences are the classic example.

**AI / synthetic disclosure**
- Creators must disclose realistic altered or synthetic content (something a viewer could mistake for a real person, place, scene or event) in the upload flow. Unrealistic/animated content and minor edits need no disclosure. (support.google.com/youtube/answer/14328491)
- May 2026: label moved to a more prominent position on the player for photorealistic content; YouTube also detects AI content automatically and may label it; for unrealistic/animated content the disclosure sits in the expanded description. Disclosure does not affect monetisation. (blog.youtube, 2026-05-27)

**What this means for docuframe defaults**
1. **Variation engine on by default:** series mode varies layout seeds, scene mix, colour accents, intro structure and pacing within the style; refuse to ship two episodes whose beat tables are > 70% identical in structure.
2. **Real creative input:** quick mode still asks for (or proposes and confirms) the angle/hook; director mode makes the user approve script and storyboard. Manifest records human approvals.
3. **Disclosure reminder:** if the film uses a synthetic voice cloned from a real person, a generated photoreal image, or a re-voiced (dubbed) real speaker, the YouTube package includes a "turn on altered/synthetic content: Yes" checklist item. Default local TTS narration over code-drawn graphics is not realistic depiction of a real person — reminder says "probably not required; your call".
4. **No AI persona presenters** on health/finance/news topics by default.
5. Archive photo **re-enactments** (generated "historical" photos) are off by default and, if enabled, always labelled on screen.

## TikTok
- Requires labels on AI-generated content containing realistic images, audio or video; encourages labelling fully generated or significantly edited content. (support.tiktok.com AI-generated content page)
- Reads C2PA Content Credentials to auto-label; testing invisible watermarking (TikTok newsroom, 2026-03-10).
- Ads: from July 21, 2026, disclosure labels required on realistic AI-generated content in ads (Common Thread Collective, 2026-07-24).
- **Default:** shorts export reminder mirrors YouTube's; never strip metadata in a way meant to evade labels.

## Instagram / Facebook (Meta)
- "AI info" label for content Meta detects or users mark as AI-made/edited; for AI-edited content it sits in the post menu.
- Aug 31, 2026: "AI creator" profile label replaced by "AI-generated profile"; profiles featuring an AI-generated person without the label get reach limited. Using AI to edit, make graphics or captions does not need the profile label. (TechCrunch 2026-08-31)
- **Default:** no action unless the user builds an AI persona channel; then remind.

## LinkedIn
- Shows a Content Credentials ("CR") label on images/video carrying C2PA metadata; says the label doesn't affect ranking. (linkedin.com/help a6282984)
- **Default:** optional C2PA manifest export is a later improvement; not required.

## Copyright-adjacent platform rules we enforce
- Content ID: music must be our own synthesised score, user-supplied, or explicitly licensed for monetised YouTube use; manifest records which.
- Archive footage: only items whose licence allows commercial use; attribution written into the description automatically.

## Sources (read 2026-11-20)
- YouTube channel monetisation policies — https://support.google.com/youtube/answer/1311392
- YouTube altered/synthetic disclosure — https://support.google.com/youtube/answer/14328491
- YouTube blog, improving AI labels — https://blog.youtube/news-and-events/improving-ai-labels-viewers-creators/
- Tubefilter, 2026-07-13 — https://www.tubefilter.com/2026/07/13/youtube-inauthentic-content-monetization-policy-update/
- TechCrunch, 2026-07-20 — https://techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/
- TikTok AI-generated content — https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content
- TikTok newsroom 2026-03-10 — https://newsroom.tiktok.com/tiktok-ssa-shares-more-ways-to-spot-shape-and-understand-ai-generated-content?lang=en-ZA
- TikTok ads disclosure (secondary) — https://commonthreadco.com/blogs/coachs-corner/tiktok-ai-ad-disclosure-rules-ecommerce-2026
- Instagram AI-generated profile label — https://techcrunch.com/2026/08/31/instagram-puts-new-limits-on-undisclosed-ai-profiles/
- LinkedIn Content Credentials — https://www.linkedin.com/help/linkedin/answer/a6282984

Not yet researched (do before launch): YouTube Shorts remix/reused-clip specifics; app store rules (only relevant if we ship a desktop app); EU AI Act Art. 50 machine-readable marking obligations and their 2026 application dates.
