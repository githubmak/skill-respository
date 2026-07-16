---
name: cinematic-character-prompt
description: Generate cinematic AI image prompts for human or humanoid character portraits and scenes with selectable Eastern, Western, or hybrid aesthetics, detailed costume design, natural expressions, film lighting, camera language, color grading, composition, and negative prompts. Explicit slash commands include /角色, /角色生图, /角色提示词, /人物生图, /人物提示词, /cinematic-character-prompt, and /character-prompt. Use when the user asks for AI image prompts, character visuals, portrait prompts, movie-like人物画面, 角色生图提示词, cinematic stills, fashion/period character looks, or prompts for Midjourney, SD, Flux, Sora, Runway, 即梦, 可灵, or similar image/video generation tools.
---

# Cinematic Character Prompt

## Core Workflow

1. Extract the user's explicit requirements: character identity, age range, gender presentation, era, culture, mood, pose/action, scene, platform, language, aspect ratio, and any required aesthetic direction.
2. Guide the user to choose the desired image style and layout before writing the final prompt when these are not already specified.
   - Image style options should be concise and useful, such as: cinematic realistic portrait, refined Chinese fantasy/court, Western historical fantasy, modern editorial, dark epic, soft romantic, or hybrid East-West.
   - Layout options should include at least: single cinematic portrait/scene, close-up face portrait, full-body character design, and four-view character sheet.
   - If the user already provided enough direction, proceed directly and state the inferred style and layout briefly.
3. Choose an aesthetic lane:
   - **Eastern**: Chinese, Japanese, Korean, Central Asian, xianxia/wuxia, court, modern Asian, ink-wash restraint, silk texture, ritual symmetry.
   - **Western**: European historical, Hollywood, noir, fantasy, royal, modern editorial, Renaissance/Baroque/Gothic, naturalistic drama.
   - **Hybrid**: Combine structural elements from both, but keep a coherent hierarchy; name which tradition dominates.
   - If the user does not specify, infer from character context. If ambiguous, provide one recommended lane and mention that it can be swapped.
4. Build the prompt from concrete visual layers, not adjective piles:
   - Character anchor
   - Face and natural expression, including a memorable non-template facial signature
   - Hair, makeup, and grooming, including an elegant silhouette and intentional strand design
   - Body proportion and posture, including tasteful character-appropriate shoulder, waist, hip, leg, neck, and bearing design
   - Costume silhouette, fabric, craft, ornaments, and wear state
   - Pose/action and body language
   - Environment or background
   - Film lighting and color grade
   - Camera, lens, composition, depth of field
   - Rendering quality and realism
   - Negative prompt
5. Keep expression natural and specific. Prefer restrained micro-expressions over generic beauty terms: "a faint smile held back", "eyes slightly wet but steady", "jaw relaxed, breath visible", "brows barely drawn together".
6. Make the clothing physically plausible. Include silhouette, closure, layers, textile, embroidery/pattern, jewelry/props, and signs of status or story. Avoid impossible mixtures unless the user asks for surreal design.
7. Use cinematic language that can be rendered: lens focal length, shot size, light source, contrast, color temperature, film stock or grade, atmosphere, and composition.
8. Run a distinctiveness pass before final output:
   - Design the face from structure, not from copying a complete reference face. Build an original face model from face outline, facial proportions, feature hierarchy, expression, hair, and makeup.
   - Start with face shape before features: round face for friendly/youthful softness, short oval for sweet everyday freshness, narrow oval for cool restraint, longer face for maturity and distance, square or softly squared face for stability and power. Avoid overly pointed chins and generic V-line influencer faces unless the user explicitly needs that look.
   - Specify san-ting/wu-yan proportion logic when faces matter: middle-third length, lower-third length, eye spacing, brow-eye distance, nose length, mouth-to-chin spacing, and how these proportions support age and temperament.
   - Use the "one strong feature, two supporting features" rule. Let only one facial feature become the memory point, such as eyes, nose, lips, brows, or bone structure; make the other features quieter so the face does not become a collage of competing beautiful parts.
   - Replace generic "perfect beauty", "idol face", "网红脸", or averaged symmetry with 3-5 concrete facial traits: eye shape, brow bone, cheekbone, nose bridge/tip, lip line, jaw/chin, facial proportion, skin texture, and expression tension.
   - Avoid celebrity resemblance by describing an original composite identity only; do not use real-person names, star aura, actor-like labels, fandom-coded descriptions, or any wording that pushes the face toward a recognizable public figure.
   - If references are provided, use only local structure: face reference for outline/bone direction, eye reference for eye shape, nose reference for bridge/tip proportion, mouth reference for lip temperament, and a base face model for proportions. Never ask the model to copy a whole face, makeup look, expression, or celebrity aura from one image.
   - Check for common facial design conflicts: juvenile round eyes with overly severe thin lips, doll face with heavy jaw, fox eyes with hooked nose and pointed chin, all features too sharp, all features too large, over-smoothed skin, mismatched age signals, or makeup that changes the underlying face.
   - Lock makeup and styling to the existing face. Makeup may change skin finish, brow softness, eye depth, blush placement, and lip color, but must not change face shape, san-ting/wu-yan proportions, eye spacing, nose placement, or mouth-to-chin spacing.
   - Give hair its own design logic and make it beautify the face: use crown height, hairline softness, parting, temple hair, cheek-framing strands, side volume, braided/looped sections, tail flow, and ornament placement to correct proportions, lift the face, narrow or sharpen the jaw, soften a long face, and make the eyes/cheekbones more striking. Reject stiff helmet hair, bulky top knots, flat center-part curtains, messy accidental flyaways, or ornaments that overpower the face.
   - For male characters, make the face striking and forceful without becoming harsh: clear brow architecture, sharp but elegant cheekbones, clean mandibular angle, balanced long face or noble narrow V-contour, defined nose bridge, compressed or calm lips, controlled gaze, and neck/shoulder bearing that supports authority.
   - For female characters, make the beauty surprising rather than template-sweet: asymmetrical micro-expression, unusual eye rhythm, distinctive lip shape, refined cheek contour, and a small imperfection or story mark when appropriate.

9. When the user asks for high attractiveness, beautiful heroine, handsome hero, perfect proportions, waist-hip ratio, or ChatGPT Image quality, translate vague beauty words into concrete renderable structure:
   - Do not rely on generic terms like "beautiful", "handsome", "perfect body", or "good proportions" alone. Break them into face structure, facial feature hierarchy, hair/makeup, body proportion, tailoring, pose, lighting, lens, and negative constraints.
   - For face shape and facial structure, use concrete terms such as: soft oval face shape, symmetrical facial features, defined jawline, elegant high cheekbones, balanced facial thirds, expressive eyes, soft double eyelids, refined nose bridge, natural lip shape, and a subtle warm smile. Keep these details character-specific, not a generic beauty checklist.
   - To avoid plastic artificial faces, include realistic skin texture: subtle pores, natural skin glow, faint under-eye softness, tiny skin variation, soft freckles when suitable, and believable makeup sitting on the skin rather than replacing the skin.
   - Use eye and expression details to create life: expressive eyes, warm catchlights, relaxed eyelids, a subtle smile rather than an exaggerated grin, gaze direction, emotional restraint, and a candid moment rather than mannequin stillness.
   - For adult female leads, describe tasteful natural elegance: graceful neck and shoulders, slim but believable waistline, naturally beautiful waist-hip ratio, balanced pelvis/hip volume, long leg proportion, upright posture, and clothing seams or belts that reveal the silhouette without vulgar emphasis.
   - For adult male leads, describe forceful but elegant structure: tall cranial proportion, broad shoulders, narrow waist, clean back/waist line, long limbs, stable neck and shoulder bearing, controlled posture, and clothing layers that preserve the V-shaped silhouette.
   - For couple prompts, lock both bodies separately: heroine face and waist-hip silhouette remain feminine and character-specific; hero face and shoulder-waist structure remain masculine and character-specific; both must keep natural anatomy, correct head-to-body scale, and believable posture.
   - For body and posture vocabulary, prefer: slender but toned build, athletic physique, elegant collarbones, hourglass silhouette for adult female fashion/character prompts, broad shoulders and lean waist for adult male prompts, gracefully standing, relaxed and confident posture, and candid pose. Avoid vulgar phrasing or purely anatomical fixation.
   - For high-quality portrait lighting, choose one or two motivated lighting setups: Rembrandt lighting for sculpted facial depth, soft directional window light for realistic skin texture, golden hour warm light for romantic atmosphere, moonlit rim light for fantasy, or controlled studio key light for editorial polish.
   - For camera language, use practical photography terms when appropriate: fashion editorial photography, realistic environmental portrait, cinematic realistic style, 85mm portrait lens, f/1.8, shallow depth of field, crisp subject focus, soft background bokeh, professional DSLR or full-frame portrait feel.
   - For ChatGPT Image / DALL-E style requests, default to a polished Chinese prompt for the user. Add a complete English prompt only when the user explicitly asks for English, bilingual output, Midjourney-style prompting, or direct English prompt text. Use the formula: character identity + original face structure + realistic skin texture + eyes/expression + body proportion/posture + clothing/tailoring + scene + lighting + camera/lens + quality style + negative constraints.
   - Treat "网感" as polish in makeup, lighting, color grade, pose, camera, and high-share editorial presentation. It must not become a generic influencer face, copied social-media face, excessive V-line slimming, or over-smoothed plastic skin.
   - Include negative anatomy terms when body proportion matters: wrong head-to-body ratio, head too large, distorted torso, broken waist, unnatural waist-hip ratio, warped pelvis, too narrow shoulders, extra-long neck, malformed hands, and stiff mannequin posture.

Read `references/preferred-look-profile.md` first when the user asks Codex to complete, enrich, or stylize character image prompts without giving a competing style reference. Use it as the default taste anchor for face quality, lighting, costume richness, pose, palette, and camera feel.

Read `references/style-bank.md` when the user requests rich aesthetic choices, period clothing detail, specific light moods, or when you need more vocabulary for Eastern/Western/hybrid styling.

## Output Format

Default output language is Chinese. For ordinary requests, output:

```markdown
## 中文提示词
[one polished prompt in Chinese]

## Negative Prompt / 反向提示词
[concise negative prompt]

## 参数建议
- 画幅:
- 镜头:
- 光影:
- 风格强度:
```

If the user names a platform, adapt the output:

- **Midjourney**: Add an English prompt only when useful for direct Midjourney use; add aspect ratio and style parameters at the end; keep negative terms after `--no`.
- **Stable Diffusion / Flux**: Separate positive prompt, negative prompt, and suggested sampler/resolution only if useful.
- **ChatGPT Image / DALL-E / 即梦 / 可灵 / Sora / Runway**: Use Chinese natural-language cinematic sentences by default; avoid over-tagging. Add English only if the user asks for it.

If the user explicitly asks for bilingual or English output, add:

```markdown
## English Prompt
[one polished prompt in English]
```

For four-view character sheets, output the prompt with an explicit two-column layout:

```markdown
## 中文提示词
[one polished four-view prompt in Chinese]

## 版式锁定 / Layout Lock
- 左上: 人物近景正脸
- 左下: A-pose 全身正面照
- 右上: 人物全身侧视图
- 右下: 人物全身背视图
- 左右两列、上下两格，纯净背景或统一棚拍背景
- 四视图必须严格保持同一张脸、同一发型、同一妆容、同一套服装、同一配饰、同一材质和纹样，不允许任何服装版本差异

## Negative Prompt / 反向提示词
[include inconsistency negatives]
```

## Prompt Rules

- Default to Chinese output for all user-facing sections, including prompt text, parameter suggestions, layout locks, and negative prompts. Provide English only when the user explicitly asks for English/bilingual output or when a named platform clearly requires direct English prompt text.
- Prefer one vivid finished prompt over many fragmented tags unless the platform requires tags.
- When style or layout is missing and the user has not asked for an immediate final prompt, ask the user to choose before producing the final prompt. Keep the question brief and offer a recommended default.
- If the user asks for a four-view character sheet, the result must be a two-column layout: top-left close-up frontal face, bottom-left full-body frontal A-pose, top-right full-body side view, bottom-right full-body back view. Side and back views must show the complete character from head to toe, including crown, hair, full garment silhouette, sleeves, hem, shoes if visible, and the full vertical costume proportions; never crop them to bust, half-body, or three-quarter length.
- Four-view prompts must repeatedly lock identity and wardrobe consistency: same face, same facial proportions, same hairstyle, same makeup, same costume silhouette, same garment layers, same embroidery/pattern placement, same jewelry/props, same colors, same materials, and same wear state across all four panels.
- Four-view negative prompts must reject: different face, different person, inconsistent clothing, changed hairstyle, changed accessories, mismatched colors, altered embroidery, front/back costume mismatch, asymmetrical unintended garment changes, extra panels, missing panel, wrong layout, dynamic pose replacing A-pose, cropped side view, cropped back view, half-body side view, half-body back view, missing feet or hem in side/back panels.
- When generating a new character face, include a compact original face model: face shape, san-ting/wu-yan proportion, one dominant facial memory point, two supporting features, and a non-celebrity identity lock.
- When generating highly attractive characters, include a compact "body proportion lock" in addition to the face design lock: natural head-to-body scale, shoulder width, waist line, hip/leg proportion, neck/shoulder bearing, posture, and garment tailoring. Keep body description tasteful, adult-appropriate when curves are emphasized, and anatomically plausible.
- Do not use a single complete human face as the target look. When the user supplies references, explicitly separate them into local structural references and recombine them into a new original face.
- Avoid common face failures: copied reference face, celebrity resemblance, influencer V-line chin, over-pointed chin, excessive face slimming, plastic smooth skin, feature collage, all features competing, mismatched age signals, harsh high cheekbones, too-wide or too-close eye spacing unless intentional, unnatural nose height, over-thin lips, stiff mannequin expression, makeup changing facial structure.
- Avoid common body proportion failures: head too large, childlike head-to-body ratio for adult characters, neck too long, shoulders too narrow, broken torso, pinched waist, warped pelvis, unnatural waist-hip ratio, distorted legs, stiff doll posture, and clothing that hides or contradicts the intended silhouette.
- Include "cinematic still", "film lighting", or equivalent only once; support it with concrete lighting details.
- Use "photorealistic" only when the user asks for realistic output or when it matches the request.
- Avoid over-sexualized descriptions. For minors or ambiguous youth, keep styling age-appropriate and non-sensual.
- Do not include celebrity names or living-artist style mimicry unless the user provided a lawful fictional or public-domain reference. Use neutral film/aesthetic descriptors instead.
- Do not generate a face that reads as a specific celebrity, idol, actor, influencer, or "star lookalike"; explicitly ask for an original, non-celebrity face with distinctive facial proportions. Prefer "designed original face, structure-based face design, no complete face reference copied".
- If user constraints conflict, preserve identity and story first, then costume, then lighting, then rendering flourishes.
- When no competing style is specified, bias toward the user's saved preference profile: luminous close-up beauty, refined Chinese fantasy/court styling, airy fabric, ornate but readable jewelry, natural micro-expression, soft wind in hair, shallow depth of field, and cinematic back/rim light.
- For character-sheet or portrait outputs, include a compact "face design lock" and "hair design lock" in the positive prompt. The hair design lock must state how the hairstyle flatters the face: raised crown for better cranial proportion, softened hairline, controlled temple strands, cheekbone-framing pieces, side volume balance, and ornaments placed to elongate or lift the silhouette. Include negatives for template face, celebrity resemblance, idol lookalike, stiff hair, ugly topknot, flat hairline, bulky crown hair, unflattering exposed forehead, face-widening side hair, and face-obscuring ornaments.

## Quality Checklist

Before finalizing, confirm the prompt includes:

- A clear character anchor and visual identity
- A chosen Eastern, Western, or hybrid aesthetic
- Specific costume construction and material detail
- A natural, emotionally readable expression
- A distinctive original face design that avoids template prettiness and celebrity resemblance
- Realistic skin texture when the output is photoreal or cinematic realistic: subtle pores, natural glow, tiny skin variation, and no waxy plastic finish
- Face-shape logic and san-ting/wu-yan proportions that match the character's age, status, and temperament
- A facial feature hierarchy with one memory point and two supporting features, avoiding feature collage
- A deliberate hairstyle silhouette that flatters the face and supports the character's status
- A tasteful body proportion lock when attractiveness or full-body composition matters
- Film lighting with source, mood, and color temperature, such as Rembrandt lighting, soft directional window light, golden hour warm light, moonlit rim light, or controlled studio key light when appropriate
- Camera shot, focal length or lens feel, composition, and depth, such as 85mm portrait lens, f/1.8, shallow depth of field, crisp subject focus, and soft bokeh when appropriate
- Negative prompt targeting common failures
- For four-view output: two-column panel order is locked; side and back panels are explicitly full-body head-to-toe views; identity/costume consistency is stated in both positive and negative prompts


