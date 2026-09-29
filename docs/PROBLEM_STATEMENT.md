# SIH Problem Statement 26097 and how HunarVaani answers it

**Title:** AI-Driven voice Assistant for livelihood Mapping and NSQF-Aligned Skilling
Recommendations for SC Communities under GIA component of PM-AJAY
**Organisation:** Ministry of Social Justice and Empowerment (MoSJE), Department of Social Justice
and Empowerment · **Category:** Software · **Theme:** Agriculture, FoodTech & Rural Development

## The problem statement (as given)

**Background.** The Pradhan Mantri Anusuchit Jaati Abhyuday Yojana (PM-AJAY) aims to reduce
poverty among Scheduled Caste (SC) communities through livelihood promotion, skill development and
enterprise support under its Grant-in-Aid (GIA) component. A major challenge in implementation is
identifying skill training pathways that match both the beneficiaries' aspirations and the actual
livelihood opportunities in their local regions.

Many beneficiaries face low digital literacy, limited awareness of modern trades, language
constraints and difficulty with text-heavy digital systems. Enrolled programmes then often do not
match the beneficiary's interests, capabilities or local market demand, leading to high dropout
and poor post-training employment. An AI-enabled conversational system is needed that talks
naturally in regional languages and dialects, understands aspirations, assesses skill gaps and
recommends suitable NSQF-aligned livelihood opportunities in and around the beneficiary's area.

**Basic issues under GIA:** no proper road map and planning of perspective plans from execution to
implementation; identifying trained and skilled financial consultants; job placement after
skilling; coordination between the corporation and ministries/departments; inadequate technical
and support teams at ground level.

**Detailed description.** An AI-driven, multilingual, voice-based virtual livelihood assistant
that interviews beneficiaries from aspirational SC communities by voice instead of forms, and
collects:
- educational background
- existing or traditional family occupations
- current livelihood activities
- skills and interests
- mobility and physical constraints
- preference for self-employment or wage employment
- local economic realities and opportunities

It should support regional languages and dialects for users with low literacy, and feel
empathetic and conversational rather than administrative. AI/ML profiling and recommendation
should identify suitable NSQF-aligned training programmes, relevant trades and livelihood
pathways, skill gaps needing intervention, and region-specific employment or enterprise
opportunities. It should work in low-connectivity, low-tech settings: IVR phone calls for feature
phones, WhatsApp voice notes, lightweight mobile or kiosk solutions.

**Expected solution.** An AI-powered multilingual voice assistant that helps SC beneficiaries
under PM-AJAY find suitable skill training and livelihood opportunities through simple voice
conversations in regional languages and local dialects.

(No dataset was provided with the problem statement.)

## Coverage: what the prototype does for each ask

| The problem statement asks for | HunarVaani today | Plan |
|---|---|---|
| IVR calls for feature phones, low connectivity | ✅ plain phone call (Exotel); the caller needs no internet or smartphone | — |
| Regional languages | ✅ Hindi, English, Marathi, picked at the start of the call | More languages Sarvam supports: add prompt text + render |
| Dialects | ❌ | Needs speech models that support the dialect; out of scope |
| Educational background | ✅ keypad question | — |
| Traditional family occupation | ❌ | **Next:** one short question |
| Current livelihood activity | ✅ caller describes their work in their own words → Sarvam speech-to-text → NCO occupation → read back to confirm | — |
| Skills and interests | ⚠ current work only | **Next:** "what would you like to learn" question |
| Mobility and physical constraints | ⚠ travel distance ✅; physical constraints ❌ | **Next:** keypad question on physical difficulty |
| Self-employment or wage employment | ✅ keypad question | — |
| Age (needed for training eligibility) | ❌ | **Next:** keypad age band |
| Empathetic, conversational | ⚠ short polite prompts; reads back the caller's own work; human officer on 0 | Later: India-hosted LLM writes the next line from earlier answers |
| NSQF-aligned training recommendations | ❌ | **Next priority:** rules over sample NSQF qualification data |
| Trades and livelihood pathways | ✅ occupation (NCO code) identified | Recommendations build on it |
| Skill gaps | ❌ | With recommendations: qualification entry needs vs the caller's profile |
| Region-specific opportunities | ❌ | With recommendations: sample district opportunity data, clearly labelled as sample |
| WhatsApp voice notes, kiosk | ❌ | Later: the same speech-to-text + search pipeline behind a WhatsApp number |
| Planning / coordination for officials (GIA issues) | ⚠ `/calls` page for the team | Later: live dashboard and profile pages |

**Caste:** the scheme is for SC communities, but the call never asks caste (our rule, and a
privacy risk on a voice line). Beneficiaries reach HunarVaani through the scheme's own outreach;
eligibility is confirmed by an official afterwards.
