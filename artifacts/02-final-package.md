# CLAUDE — Senior Editor / Orchestrator Response

## Reconciliation Note

I've reviewed Gemini's audit. **Gemini's determination is correct and I am upholding it without modification.**

The source material field contains only the template placeholder string:
> *"Replace this file with the material to research, fact-check, edit, and turn into a production package."*

There is no topic, script draft, claim set, quote, statistic, name, date, or narrative of any kind in the input. This is not a partial or ambiguous source — it is an empty one.

**Orchestrator decision: PRODUCTION BLOCKED AT STAGE 0 (INGESTION).**

I will not generate the nine deliverables (script, scenes, B-roll list, graphics, SRT, thumbnails, description, QC) against invented subject matter. Doing so would violate the explicit rules governing this task:
- "Do not invent sources or verification results"
- "Preserve uncertainty where primary sources conflict" (there is nothing to have uncertainty *about* yet — inventing a topic would manufacture false certainty)
- "Flag claims requiring fresh web verification" — impossible with zero claims present

Producing a fake finished package (e.g., picking an arbitrary topic like "5 facts about the moon" and treating it as if it came from the source) would be a worse failure than declining to produce one, because it would silently misrepresent fabricated content as a reconciled, fact-checked output. That is the exact failure mode this task is designed to prevent.

---

## What IS Actionable Right Now

Since "final output must be actionable, not just explanatory," here is the actionable artifact: an **intake package** that removes all ambiguity and lets production start the moment real material arrives — no back-and-forth needed.

### A. Required Intake Fields (send these, and the pipeline runs immediately)

| Field | Needed | Notes |
|---|---|---|
| Topic / working title | ❌ Missing | One sentence is enough to start |
| Core claims / talking points | ❌ Missing | Bullet list, even rough notes |
| Direct quotes (if any) | ❌ Missing | With speaker attribution |
| Statistics/numbers used | ❌ Missing | Include where you got them, even informally |
| Source links / documents | ❌ Missing | Raw links fine — I will still verify independently |
| Target video length | ❌ Missing | e.g., 6 min explainer / 60s short |
| Platform | ❌ Missing | Long-form YouTube / Shorts / both |
| Tone | ❌ Missing | News-style, casual, documentary, satirical, etc. |
| Any legally sensitive names/entities involved | ❌ Missing | Flags for defamation review upfront |
| Existing footage/assets you already have | ❌ Missing | Determines B-roll vs AI-generation split |

### B. Pre-Built Output Scaffold (ready to populate on ingestion)

So the next round is fast, here is the exact shell every deliverable will fill into once material lands:

```
1. CORRECTED PRODUCTION PLAN
   - Topic, angle, runtime, audience, platform — pending intake

2. FINAL SCRIPT
   - [HOOK] — pending
   - [SEGMENT 1..N] — pending, each line tagged FACT/FORECAST/TARGET/INTERPRETATION
   - [CTA/OUTRO] — pending

3. SCENE-BY-SCENE VISUAL INSTRUCTIONS
   - Scene # | Script line | Visual | Duration — pending

4. B-ROLL / REAL vs AI LIST
   - Per scene: Real footage needed | Stock available | AI-gen permissible | Licensing risk — pending

5. GRAPHICS SPECS
   - Lower thirds, chart data sources, on-screen citations — pending
     (chart/graphic claims will be tagged with verification tier)

6. SRT DRAFT
   - Timecoded captions matching final script — pending

7. THUMBNAIL / TITLE OPTIONS
   - 3–5 options each, no clickbait misrepresenting unverified claims — pending

8. DESCRIPTION
   - Summary + sourced links + timestamps — pending

9. FINAL QC CHECKLIST
   - [ ] All FACT claims sourced to Tier 1/2
   - [ ] All FORECAST/TARGET claims labeled with issuer + non-guarantee language
   - [ ] All INTERPRETATION labeled as such, alt views included where consensus absent
   - [ ] Fresh web verification completed for volatile claims
   - [ ] Legal/defamation review passed
   - [ ] No fabricated sources anywhere in script or graphics
```

---

## Risk Flag (Process-Level)

- **Risk:** Downstream team members or automation may be tempted to auto-fill this template with placeholder or invented content to "complete the run." Flag this explicitly: **any populated version of the above without a real source input is non-compliant with task rules and must be rejected in QC.**

---

**Next step:** Paste the actual research material, script draft, or topic notes. On receipt, Gemini's audit log and this orchestration will run against real claims, and all nine deliverables will be produced in full — not as a scaffold, but as the finished, corrected, actionable package.