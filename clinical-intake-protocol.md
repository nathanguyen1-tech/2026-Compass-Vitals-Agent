# Compass Vitals — Clinical Intake Protocol
## AI Health Assistant Conversation Design

_Prepared: 2026-02-23 | For: CVH Physician Team + Development Team_
_Status: DRAFT — Requires physician team review_

---

## 1. Design Principles

1. **Mimic a real clinical encounter** — The AI follows the same logical flow a physician would: CC → HPI → ROS → PMH → Meds → Allergies → Social/Family Hx
2. **Structured but conversational** — Not a rigid form. The AI asks follow-ups based on responses, like a real doctor would.
3. **Bilingual by default** — Every question has Vietnamese + English versions. Member chooses language at start.
4. **Safety-first triage** — Red flag symptoms trigger immediate escalation (chest pain + dyspnea → "Call 911")
5. **Completeness tracking** — The system tracks which intake sections are complete. Won't generate SOAP until minimum data is collected.
6. **Cultural sensitivity** — Account for Vietnamese health beliefs (e.g., "nóng/lạnh" hot/cold imbalance concepts, herbal medicine use, traditional remedies)

---

## 2. Intake Flow (State Machine)

```
START
  │
  ├─ Language Selection (Vietnamese / English)
  ├─ Demographics Verification (age, sex, pregnancy status if applicable)
  │
  ▼
CHIEF COMPLAINT (CC)
  │  "What brings you in today?" / "Hôm nay bạn cần khám gì?"
  │  → Free text, AI classifies into complaint category
  │
  ▼
RED FLAG SCREENING
  │  Based on CC, check for emergency symptoms
  │  → If red flags: EMERGENCY EXIT ("Please call 911")
  │  → If no red flags: continue
  │
  ▼
HISTORY OF PRESENT ILLNESS (HPI)
  │  OLDCARTS framework (see Section 3)
  │  ~8-12 questions, dynamically selected based on CC
  │
  ▼
TARGETED REVIEW OF SYSTEMS (ROS)
  │  Based on CC + HPI findings, ask about related systems
  │  ~4-8 questions
  │
  ▼
PAST MEDICAL HISTORY (PMH)
  │  Known conditions, surgeries, hospitalizations
  │  ~3-5 questions
  │
  ▼
MEDICATIONS & ALLERGIES
  │  Current meds (including OTC, herbals, traditional Vietnamese remedies)
  │  Drug/food allergies + reaction type
  │  ~2-4 questions
  │
  ▼
SOCIAL & FAMILY HISTORY
  │  Smoking, alcohol, occupation, relevant family conditions
  │  ~3-5 questions (targeted to CC)
  │
  ▼
SUMMARY & CONFIRMATION
  │  AI reads back key findings: "Let me make sure I have this right..."
  │  Member confirms or corrects
  │
  ▼
REPORT GENERATION
  │  → Patient Summary (plain language, member's chosen language)
  │  → SOAP Note (English, for physician)
  │  → Differential Diagnosis (ranked)
  │  → Triage Level (routine / urgent / emergency)
  │  → Suggested Workup
  │
  ▼
PHYSICIAN QUEUE
```

**Estimated conversation length:** 10-15 minutes, 15-25 AI questions depending on complexity.

---

## 3. HPI Framework: OLDCARTS

For every chief complaint, the AI systematically covers these dimensions (adapted per complaint):

| Element | Question Template (English) | Question Template (Vietnamese) |
|---------|----------------------------|-------------------------------|
| **O**nset | "When did this start?" | "Triệu chứng này bắt đầu từ khi nào?" |
| **L**ocation | "Where exactly do you feel it?" | "Bạn cảm thấy đau/khó chịu ở đâu?" |
| **D**uration | "How long does it last?" | "Mỗi lần kéo dài bao lâu?" |
| **C**haracter | "Can you describe what it feels like?" | "Bạn có thể mô tả cảm giác như thế nào?" |
| **A**ggravating | "What makes it worse?" | "Có gì làm cho nó nặng hơn không?" |
| **R**elieving | "What makes it better?" | "Có gì làm cho nó bớt hơn không?" |
| **T**emporal | "Is it constant or does it come and go?" | "Nó liên tục hay lúc có lúc không?" |
| **S**everity | "On a scale of 1-10, how bad is it?" | "Trên thang điểm 1-10, mức độ bao nhiêu?" |

**Additional HPI elements the AI should probe:**
- Associated symptoms (contextual to CC)
- Prior episodes / similar problems before
- What they've already tried (OTC meds, home remedies, truyền thống/traditional treatments)
- Impact on daily life / work

---

## 4. Top 20 Presenting Complaints — Tailored Protocols

Each complaint has a **specific question set** beyond the generic OLDCARTS. These are the conditions CVH should build first, prioritized by frequency in primary care + relevance to Vietnamese American population:

### Tier 1: Launch Priority (Build First)

#### 1. Hypertension Management / BP Concerns
_High prevalence in Vietnamese Americans; often the entry point for ongoing care_

**Key HPI additions:**
- Home BP readings (if any)? What device?
- Headaches, vision changes, chest pain, shortness of breath?
- Dietary habits — salt intake, fish sauce (nước mắm) usage
- Current BP medications? Compliance?
- Previous highest BP reading?

**Red flags:** BP >180/120 with headache/vision changes/chest pain → hypertensive emergency → ER

**ROS focus:** Cardiovascular, neurological, renal

---

#### 2. Diabetes / Elevated Blood Sugar
_Vietnamese Americans have one of the highest diabetes incidence rates among Asian subgroups_

**Key HPI additions:**
- Known diabetic? Type 1 or 2? When diagnosed?
- Last A1c / fasting glucose? Home glucose readings?
- Polyuria, polydipsia, polyphagia, unintentional weight loss?
- Numbness/tingling in feet? Vision changes?
- Diet — rice consumption frequency, sweet drinks
- Current diabetes medications? Insulin?

**Red flags:** Symptoms of DKA (nausea/vomiting + confusion + rapid breathing) → ER

**ROS focus:** Endocrine, neurological (neuropathy), ophthalmologic, renal

---

#### 3. Upper Respiratory Infection / Cough / Cold
_Most common primary care visit reason globally_

**Key HPI additions:**
- Fever? Maximum temperature?
- Cough — productive or dry? Color of sputum?
- Sore throat, nasal congestion, post-nasal drip?
- Sick contacts? Recent travel?
- TB screening history (important for Vietnamese immigrant population)
- Duration — acute (<3 weeks) vs chronic?

**Red flags:** High fever + stiff neck, difficulty breathing, coughing blood → ER

**ROS focus:** ENT, pulmonary, constitutional

---

#### 4. Headache
**Key HPI additions:**
- Location (frontal, temporal, occipital, unilateral)?
- Aura? Visual disturbances?
- Worst headache of life? Thunderclap onset?
- Nausea/vomiting? Photo/phonophobia?
- Triggers (stress, food, sleep, menses)?
- Frequency — how many per week/month?
- History of head trauma?

**Red flags:** Thunderclap headache, worst headache of life, fever + stiff neck, neurological deficits, new headache >50yo → ER

**ROS focus:** Neurological, ophthalmologic, ENT

---

#### 5. Back Pain / Joint Pain
**Key HPI additions:**
- Location — upper/lower back? Which joints?
- Radiation — down the legs? Numbness/tingling?
- Bowel/bladder changes? (cauda equina screening)
- Injury or trauma?
- Worse with movement or rest?
- Occupation — physical labor?
- Any weakness in legs?

**Red flags:** Loss of bowel/bladder control, saddle anesthesia, progressive weakness → ER

**ROS focus:** Musculoskeletal, neurological, urological

---

#### 6. Abdominal Pain / GI Complaints
**Key HPI additions:**
- Location (epigastric, RUQ, LLQ, diffuse, periumbilical)?
- Relationship to meals? Worse after eating?
- Nausea/vomiting? Diarrhea/constipation?
- Blood in stool? Black/tarry stools?
- Last bowel movement?
- Diet changes? Spicy food tolerance?
- Alcohol use?
- Hepatitis B screening history (critical for Vietnamese population)

**Red flags:** Severe RLQ pain + fever (appendicitis), rigid abdomen, bloody stool + hemodynamic instability → ER

**ROS focus:** GI, hepatobiliary, urological, gynecological (if applicable)

---

#### 7. Anxiety / Depression / Insomnia
_Mental health stigma is significant in Vietnamese culture — AI should normalize and screen gently_

**Key HPI additions:**
- PHQ-2 screening: Loss of interest? Feeling down/hopeless?
- If positive → PHQ-9 full screening
- GAD-2/GAD-7 for anxiety
- Sleep — onset insomnia vs maintenance? Hours per night?
- Appetite changes? Weight changes?
- Concentration? Energy level?
- **Safety screening:** Thoughts of self-harm or suicide? (mandatory)
- Stressors — immigration, family, financial, cultural adjustment?
- Traditional coping — meditation, temple, family support?

**Red flags:** Active suicidal ideation with plan → Crisis (988 Suicide & Crisis Lifeline) → ER

**ROS focus:** Psychiatric, neurological, constitutional

**Cultural note:** Frame mental health questions gently. Many Vietnamese patients express psychological distress as physical symptoms (somatization) — "I feel tired all the time" or "my chest feels heavy" may indicate depression. The AI should probe further when physical workup seems disproportionate to symptoms.

---

#### 8. Skin Rash / Dermatologic Complaints
**Key HPI additions:**
- Location? Spreading?
- Itchy, painful, or neither?
- New soaps, detergents, medications?
- Photo upload option (critical for derm)
- Fever + rash?
- Contact with anyone with similar rash?

**Red flags:** Rapidly spreading rash + fever + mucosal involvement (SJS concern) → ER

**ROS focus:** Dermatologic, constitutional, allergic/immunologic

---

#### 9. Urinary Symptoms (UTI / Frequency / Dysuria)
**Key HPI additions:**
- Burning with urination? Frequency? Urgency?
- Blood in urine? Cloudy/foul-smelling?
- Flank pain? Fever/chills?
- Vaginal discharge (if applicable)?
- History of UTIs? How many in past year?
- Sexually active?

**Red flags:** High fever + flank pain (pyelonephritis), urinary retention → urgent

**ROS focus:** Genitourinary, constitutional, gynecological

---

#### 10. Fatigue / Weakness
**Key HPI additions:**
- Acute vs chronic? When did it start?
- Sleep quality and quantity?
- Weight changes? Appetite?
- Exercise tolerance — has it changed?
- Depressive symptoms (overlap with #7)?
- Dietary habits — nutritional deficiency risk?
- Heavy periods (if applicable) — iron deficiency?
- Any new medications?

**Red flags:** Sudden onset weakness (especially unilateral) → stroke → ER

**ROS focus:** Constitutional, endocrine, hematologic, cardiac, psychiatric

---

### Tier 2: Build in Phase 2 (Detailed Protocols)

---

#### 11. Hepatitis B Screening & Management
_Critical for Vietnamese Americans — ~1 in 12 are chronic carriers. Leading cause of liver cancer in this population. Many are unaware of their status._

**Key HPI additions:**
- Have you ever been tested for Hepatitis B? When? Results?
- Have you been vaccinated for Hepatitis B?
- Country of birth? Age at immigration? (risk stratification)
- Any family members with Hepatitis B or liver cancer?
- Fatigue, abdominal pain (RUQ), jaundice, dark urine?
- Appetite changes? Unintentional weight loss?
- Alcohol use? (critical — accelerates liver damage)
- Current or prior antiviral treatment?
- Last liver function tests / viral load?

**Red flags:** Jaundice + confusion + abdominal distension (decompensated liver disease) → ER

**ROS focus:** GI/hepatobiliary, constitutional, hematologic

**Screening protocol (for asymptomatic members):**
- All Vietnamese-born members should be screened: HBsAg, anti-HBs, anti-HBc
- If HBsAg+: HBeAg, HBV DNA viral load, LFTs, AFP, liver ultrasound
- If no immunity: recommend vaccination series
- If chronic carrier: enroll in surveillance program (ultrasound + AFP every 6 months)

**Cultural note:** Hepatitis B carries stigma in Vietnamese communities. Frame screening as routine: "This is a standard test we recommend for everyone to keep your liver healthy." Avoid language implying fault or lifestyle judgment.

**Vietnamese terminology:**
- Viêm gan B = Hepatitis B
- Xét nghiệm máu = Blood test
- Gan = Liver
- Ung thư gan = Liver cancer
- Tiêm phòng = Vaccination

---

#### 12. Dyslipidemia / Cholesterol Concerns
_Cardiovascular disease risk management — often co-managed with HTN and DM_

**Key HPI additions:**
- Known high cholesterol? When diagnosed?
- Last lipid panel? Values if known?
- Currently on statin or other lipid medication? Which one?
- Side effects from cholesterol meds? (muscle pain is common concern — ask specifically)
- Family history of heart disease or high cholesterol?
- Diet — fried foods, cooking oil type (many Vietnamese households use vegetable/coconut oil heavily)
- Exercise habits?
- Smoking status?
- Known diabetes or hypertension? (metabolic syndrome screening)

**Red flags:** None specific to dyslipidemia alone — but screen for ACS symptoms if combined with chest pain/dyspnea

**ROS focus:** Cardiovascular, endocrine, constitutional

**Risk assessment:** AI should calculate or prompt for 10-year ASCVD risk score data points:
- Age, sex, race
- Total cholesterol, HDL, LDL (if available)
- Systolic BP, BP medication status
- Diabetes status
- Smoking status

**AI note for SOAP:** Include statin benefit group classification if data sufficient

---

#### 13. Shortness of Breath / Dyspnea
_Broad differential — cardiac, pulmonary, hematologic, anxiety. Requires careful triage._

**Key HPI additions:**
- Acute onset or gradual? (hours vs weeks vs months)
- At rest or with exertion? What level of exertion triggers it?
- Orthopnea? (worse lying flat — how many pillows?)
- PND (paroxysmal nocturnal dyspnea)? Waking up gasping?
- Associated chest pain? Palpitations?
- Cough? Productive? Hemoptysis?
- Leg swelling (edema)?
- Wheezing?
- Fever?
- Recent immobilization, surgery, or long travel? (PE risk)
- History of asthma, COPD, CHF, or lung disease?
- Smoking history (pack-years)?
- Anxiety/panic — does it happen with stress?

**Red flags:**
- Acute onset + chest pain + risk factors → PE/ACS → "Call 911"
- Severe dyspnea at rest + unable to speak in full sentences → "Call 911"
- Dyspnea + unilateral leg swelling (DVT/PE) → ER
- Dyspnea + fever + productive cough + hypoxia symptoms (confusion, cyanosis) → ER

**ROS focus:** Pulmonary, cardiovascular, hematologic, constitutional, psychiatric

**Triage complexity:** HIGH — This complaint requires the most careful red flag screening. The AI should ask PE/ACS screening questions within the first 3-4 questions before proceeding to full HPI.

---

#### 14. Chest Pain
_Highest-stakes triage complaint. Must be built with extreme care. False negatives are unacceptable._

**Key HPI additions (MUST be asked in this order for safety):**

**Immediate safety screening (first 3 questions):**
1. Is the chest pain happening RIGHT NOW?
2. Are you also experiencing shortness of breath, sweating, nausea, or pain in your jaw/arm/back?
3. Do you have a history of heart disease, stents, or bypass surgery?

→ If YES to #1 + any of #2: **IMMEDIATE 911 REDIRECT. Do not continue intake.**

**If cleared for continued intake:**
- Location — center, left, right, substernal?
- Character — pressure/squeezing vs sharp/stabbing vs burning?
- Radiation — to arm, jaw, back, shoulder?
- Duration — seconds, minutes, hours?
- Reproducible with palpation? (musculoskeletal clue)
- Relationship to exertion? Rest? Breathing? Eating? Position?
- Associated: diaphoresis, lightheadedness, palpitations, syncope?
- Similar episodes before? What was the diagnosis?
- Recent illness, cough, fever? (pleurisy/pericarditis)
- GERD symptoms — worse after meals, relieved by antacids?
- Anxiety/stress component?
- Risk factors: smoking, DM, HTN, hyperlipidemia, family hx of early CAD
- Cocaine or stimulant use?

**Red flags (ZERO tolerance — escalate immediately):**
- Active chest pain + diaphoresis → 911
- Chest pain + syncope → 911
- Chest pain + new dyspnea → 911
- Chest pain + unilateral leg swelling → 911 (PE)
- Tearing/ripping chest pain radiating to back → 911 (aortic dissection)
- Chest pain in known CAD patient → 911

**ROS focus:** Cardiovascular (primary), pulmonary, GI, musculoskeletal, psychiatric

**AI behavior rule:** For chest pain, the AI should err heavily toward escalation. If there is ANY ambiguity about whether the pain could be cardiac, the output should recommend urgent/ER evaluation, not routine follow-up.

**Vietnamese emergency messaging:**
- "Đau ngực có thể là dấu hiệu nghiêm trọng. Xin hãy gọi 911 ngay lập tức."
  ("Chest pain can be a serious sign. Please call 911 immediately.")

---

#### 15. Weight Management / Obesity / Metabolic Syndrome
_Growing concern in Vietnamese American community as dietary patterns shift toward Western diet_

**Key HPI additions:**
- Current weight? Height? (calculate BMI — note: Asian-specific BMI cutoffs: overweight ≥23, obese ≥27.5)
- Weight trajectory — gaining, stable, losing? Over what period?
- Intentional or unintentional weight change?
- Diet assessment:
  - Meals per day? Snacking habits?
  - Rice/noodle portions per meal?
  - Sugary drinks (trà sữa/boba, sodas, juices)?
  - Fast food frequency?
  - Cooking at home vs eating out?
- Exercise — type, frequency, duration?
- Sleep — hours per night? Snoring? Witnessed apneas? (OSA screening)
- Mood — emotional eating? Stress relationship to food?
- Known conditions: diabetes, hypertension, high cholesterol?
- Family history of obesity, diabetes, heart disease?
- Prior weight loss attempts? What worked/didn't?
- Interest in: dietary counseling, exercise plan, medication, surgery?

**Red flags:** Rapid unintentional weight loss (>5% in 1 month) → may indicate malignancy, hyperthyroidism, diabetes → urgent workup

**ROS focus:** Endocrine, cardiovascular, psychiatric, musculoskeletal, pulmonary (OSA)

**Screening bundle:** AI should flag for metabolic syndrome screening:
- Waist circumference (Asian-specific: M >90cm, F >80cm)
- Fasting glucose or A1c
- Lipid panel
- Blood pressure

**Cultural note:** Weight discussions require sensitivity. In Vietnamese culture, commenting on weight is more normalized, but the clinical conversation should still be non-judgmental and solution-oriented. Use "health goals" language rather than "weight problem."

---

#### 16. Women's Health (Menstrual, Menopause, Contraception)
_High demand — often underserved in Vietnamese American community due to cultural barriers_

**Key HPI additions — Menstrual Concerns:**
- Last menstrual period (LMP)?
- Cycle regularity? Length? Duration of bleeding?
- Heavy bleeding (menorrhagia)? How many pads/tampons per day? Passing clots?
- Painful periods (dysmenorrhea)? Severity (1-10)?
- Intermenstrual bleeding?
- Associated: bloating, mood changes, breast tenderness?
- Pregnancy possibility? Sexually active?
- History of fibroids, endometriosis, PCOS?

**Key HPI additions — Menopause:**
- Age? Last period?
- Hot flashes — frequency, severity, impact on sleep/work?
- Night sweats?
- Vaginal dryness? Painful intercourse?
- Mood changes, irritability, brain fog?
- Sleep disruption?
- Joint pain?
- Interest in hormone replacement therapy (HRT)?
- Breast cancer history (personal or family)? (HRT contraindication screening)
- Osteoporosis risk — family history, fractures, steroid use?

**Key HPI additions — Contraception:**
- Current method? Satisfaction?
- Side effects from current/prior methods?
- Pregnancy timeline — wanting children? When?
- Medical contraindications screening: migraines with aura, smoking >35yo, DVT/PE history, hypertension
- Menstrual preference — desire to have periods or not?
- STI screening — last tested? Partners?

**Red flags:**
- Pregnancy + vaginal bleeding + severe pain → ectopic pregnancy → ER
- Post-menopausal bleeding → needs urgent workup (endometrial cancer screening)
- Extremely heavy bleeding + lightheadedness/syncope → ER

**ROS focus:** Gynecologic, endocrine, constitutional, psychiatric, musculoskeletal

**Screening reminders AI should include in SOAP:**
- Cervical cancer: Pap smear schedule (Vietnamese Americans have highest cervical cancer rates among Asian subgroups)
- Breast cancer: mammogram schedule
- Osteoporosis: DEXA scan if appropriate age/risk

**Cultural note:** Many Vietnamese women are reluctant to discuss gynecologic issues, especially with male physicians. The AI intake can help by normalizing these conversations in a private, non-judgmental digital space. Use respectful, clinical language. Offer Vietnamese terminology:
- Kinh nguyệt = Menstruation
- Mãn kinh = Menopause
- Tránh thai = Contraception
- Ung thư cổ tử cung = Cervical cancer

---

#### 17. Thyroid Concerns
_Common in primary care — hypothyroidism, hyperthyroidism, nodules_

**Key HPI additions:**
- Known thyroid condition? When diagnosed?
- Current thyroid medication? Dose? Last adjustment?
- Last TSH / thyroid labs? Values?

**Hypothyroid screening:**
- Fatigue, weight gain, cold intolerance?
- Constipation?
- Dry skin, hair loss, brittle nails?
- Depression, brain fog, memory issues?
- Menstrual irregularity (women)?
- Muscle weakness or cramps?

**Hyperthyroid screening:**
- Weight loss despite good appetite?
- Heat intolerance, excessive sweating?
- Palpitations, rapid heart rate?
- Tremor? Anxiety, irritability?
- Diarrhea?
- Eye changes — bulging, dryness, double vision? (Graves')
- Difficulty sleeping?

**Thyroid nodule concerns:**
- Noticed a lump in neck? When?
- Growing? Painful?
- Difficulty swallowing or breathing?
- Voice changes / hoarseness?
- Family history of thyroid cancer?
- Radiation exposure history?

**Red flags:**
- Thyroid storm symptoms (fever + tachycardia + altered mental status in known hyperthyroid) → ER
- Rapidly growing neck mass + voice changes → urgent referral
- Myxedema coma (severe hypothermia + altered consciousness in severe hypothyroidism) → ER

**ROS focus:** Endocrine, cardiovascular, constitutional, dermatologic, neurological, ophthalmologic

---

#### 18. Allergies / Allergic Rhinitis / Sinus Symptoms
_Very common — often chronic, impacts quality of life significantly_

**Key HPI additions:**
- Symptoms: sneezing, runny nose, nasal congestion, post-nasal drip, itchy eyes/nose/throat?
- Seasonal or year-round?
- Triggers identified? (pollen, dust, pets, mold, food?)
- Duration of current episode?
- Impact on sleep? Mouth breathing? Snoring?
- Impact on work/concentration?
- Current medications tried? (antihistamines, nasal sprays, decongestants)
- Prior allergy testing?
- Asthma history? Wheezing with allergies?
- Eczema history? (atopic triad)
- Sinus pressure / facial pain? (sinusitis overlap)
- Fever? (distinguishes infection from allergy)
- Color of nasal discharge? (clear = allergy; yellow/green = possible infection)
- Eye symptoms — watery, red, itchy, swollen? (allergic conjunctivitis)

**Red flags:**
- Throat swelling + difficulty breathing after exposure → anaphylaxis → 911 + EpiPen
- Severe facial pain + high fever + vision changes → complicated sinusitis → ER
- Unilateral nasal symptoms + bloody discharge → needs ENT evaluation (rule out mass)

**ROS focus:** ENT, ophthalmologic, pulmonary, dermatologic

**Seasonal guidance:** AI should note the time of year in San Diego for context:
- Spring (Feb-May): tree pollen, grass pollen
- Summer: grass pollen
- Fall: ragweed, mold
- Winter: indoor allergens (dust mites, mold)

---

#### 19. Dizziness / Vertigo
_Broad differential — vestibular, cardiovascular, neurological, medication-related. Good AI triage candidate._

**Key HPI additions:**
- Type of dizziness (critical distinction):
  - "Room spinning" (true vertigo) → vestibular
  - "Lightheaded/faint" (presyncope) → cardiovascular/orthostatic
  - "Unsteady/off-balance" (disequilibrium) → neurological/musculoskeletal
  - "Foggy/spacey" → medication/metabolic/psychiatric
- Triggered by position changes? (BPPV — most common cause)
- Duration of episodes — seconds, minutes, hours, days?
- Associated: hearing loss? Tinnitus? Ear fullness? (Meniere's)
- Nausea/vomiting?
- Recent URI or ear infection? (vestibular neuritis/labyrinthitis)
- Headache with vertigo? (vestibular migraine, posterior stroke)
- New medications or dose changes? (many meds cause dizziness)
- Blood pressure medications? (orthostatic hypotension)
- Falls? How many in past 6 months?
- Cardiac symptoms — palpitations, chest pain?
- Anxiety? Hyperventilation? (very common cause)
- History of diabetes? (autonomic neuropathy)

**Red flags (MUST screen early):**
- Vertigo + NEW headache + any neurological symptoms (double vision, dysarthria, weakness, numbness, ataxia) → posterior circulation stroke → 911
- Dizziness + syncope/near-syncope + chest pain/palpitations → cardiac → 911
- Sudden hearing loss + vertigo → urgent ENT (within 24-48h for steroid window)
- Vertigo after head trauma → ER

**ROS focus:** Neurological (primary), ENT/vestibular, cardiovascular, psychiatric

**AI triage note:** The key diagnostic question is the TYPE of dizziness. The AI should use descriptive options rather than medical terms:
- "Does it feel like the room is spinning around you?"
- "Does it feel like you might faint?"
- "Does it feel like you're unsteady on your feet?"
- "Does it feel like your head is foggy or unclear?"

---

#### 20. Tobacco / Substance Use / Cessation
_Vietnamese American men have significantly higher smoking rates (~25-30%) than general population. Critical for CVD and cancer prevention._

**Key HPI additions — Tobacco:**
- Current smoker? Former? Never?
- Type: cigarettes, cigars, hookah, vaping/e-cigarettes?
- How much per day? Pack-years calculation?
- Age started?
- If former: when quit? How long smoked?
- Prior quit attempts? Methods tried? (cold turkey, NRT, Chantix, Wellbutrin)
- What triggered relapse (if applicable)?
- Readiness to quit — contemplation stage?
  - Pre-contemplation: not thinking about quitting
  - Contemplation: thinking about it
  - Preparation: planning to quit soon
  - Action: actively quitting
- Triggers — stress, after meals, social situations, with alcohol?
- Household members who smoke?
- Aware of health risks? Specific concerns motivating change?

**Key HPI additions — Alcohol:**
- How often do you drink? (days per week)
- How many drinks on a typical drinking day?
- CAGE screening:
  - Cut down — ever felt you should?
  - Annoyed — by criticism of drinking?
  - Guilty — about drinking?
  - Eye-opener — drink in the morning?
- Binge episodes?
- Impact on work, relationships, health?
- History of withdrawal symptoms? (tremor, seizure — dangerous)

**Key HPI additions — Other Substances:**
- Betel nut (trầu) use? (common in older Vietnamese — oral cancer risk)
- Cannabis?
- Prescription medication misuse?
- Other substances?

**Red flags:**
- Alcohol withdrawal symptoms (tremor, sweating, confusion, seizures) → ER
- Suicidal ideation in context of substance use → 988/ER
- Chest pain or hemoptysis in heavy smoker → urgent workup

**ROS focus:** Pulmonary, cardiovascular, GI/hepatic, psychiatric, oncologic screening

**Cessation support the AI should mention:**
- FDA-approved pharmacotherapy options (NRT, bupropion, varenicline)
- Quitline: 1-800-QUIT-NOW (has Vietnamese language support)
- Behavioral counseling available through CVH
- Lung cancer screening eligibility (LDCT if age 50-80 + ≥20 pack-years)

**Cultural note:** Smoking is deeply social in Vietnamese culture, particularly among men. Avoid stigmatizing language. Frame as health empowerment: "Many of our members have successfully reduced or quit — we can help you find what works for you." Ask about betel nut specifically — often missed by Western providers but carries significant oral cancer risk.

**Vietnamese terminology:**
- Hút thuốc = Smoking
- Bỏ thuốc = Quit smoking
- Rượu bia = Alcohol
- Trầu = Betel nut

---

## 5. Red Flag / Emergency Exit Protocol

The AI **must** screen for and immediately escalate these:

| Red Flag Pattern | Action |
|-----------------|--------|
| Chest pain + dyspnea + diaphoresis | "Please call 911 immediately. This could be a heart attack." |
| Active chest pain + syncope or near-syncope | "Please call 911 immediately." |
| Tearing/ripping chest pain radiating to back | "Please call 911 immediately. This needs emergency evaluation." (aortic dissection) |
| Sudden severe headache ("worst of my life") | "Please call 911. This needs immediate evaluation." |
| Suicidal ideation with plan/intent | "Please call 988 (Suicide & Crisis Lifeline) or go to your nearest ER." |
| Signs of stroke (FAST: face droop, arm weakness, speech difficulty) | "Please call 911 immediately." |
| Vertigo + new neuro symptoms (double vision, slurred speech, weakness) | "Please call 911 immediately." (posterior circulation stroke) |
| Severe abdominal pain + rigid abdomen | "Please go to the nearest ER." |
| Jaundice + confusion + abdominal distension | "Please go to the nearest ER." (decompensated liver disease) |
| Anaphylaxis symptoms (throat swelling, difficulty breathing after exposure) | "Please call 911 and use EpiPen if available." |
| Loss of bowel/bladder control + back pain | "Please go to the nearest ER." |
| Pregnancy + vaginal bleeding + severe pain | "Please go to the nearest ER." (ectopic pregnancy) |
| Post-menopausal bleeding | Urgent workup required — flag for priority physician review |
| Rapid unintentional weight loss (>5% in 1 month) | Urgent workup — flag for priority physician review |
| Sudden hearing loss + vertigo | Urgent ENT referral (within 24-48h for steroid treatment window) |
| Alcohol withdrawal (tremor, confusion, seizures) | "Please go to the nearest ER immediately." |
| Thyroid storm (fever + tachycardia + confusion in hyperthyroid patient) | "Please call 911 immediately." |
| Severe dyspnea at rest + cannot speak full sentences | "Please call 911 immediately." |
| Dyspnea + unilateral leg swelling | "Please go to the nearest ER." (DVT/PE) |

**Implementation:** Red flag screening happens EARLY in the conversation (after CC, before full HPI). The AI should ask targeted safety questions based on the chief complaint category before diving into detailed history.

**Vietnamese translations must be prepared for all emergency messaging.**

---

## 6. SOAP Note Output Template

After intake is complete, the AI generates:

### For Physicians (English)

```
COMPASS VITALS — AI-ASSISTED CLINICAL ENCOUNTER
Date: [date] | Member ID: [ID] | Language: [Vietnamese/English]
AI Confidence: [High/Medium/Low] | Triage Level: [Routine/Urgent/Emergency]

SUBJECTIVE:
  CC: [Chief complaint in patient's words]
  HPI: [Narrative paragraph using OLDCARTS data]
  ROS:
    - Constitutional: [positive/negative findings]
    - [System]: [findings]
    - [System]: [findings]
  PMH: [conditions, surgeries, hospitalizations]
  Medications: [current meds including traditional/herbal]
  Allergies: [drug/food allergies + reaction type]
  Social Hx: [smoking, alcohol, occupation, relevant lifestyle]
  Family Hx: [relevant conditions]

OBJECTIVE:
  [Note: No physical exam — AI encounter only]
  Vitals: [if member has home monitoring: BP, glucose, weight, temp]
  Self-reported findings: [anything member observed]

ASSESSMENT:
  Differential Diagnosis (ranked by likelihood):
    1. [Diagnosis] — [likelihood: high/moderate/low] — [supporting evidence]
    2. [Diagnosis] — [likelihood] — [evidence]
    3. [Diagnosis] — [likelihood] — [evidence]
    4. [Diagnosis] — [likelihood] — [evidence]

PLAN:
  Recommended workup:
    - [Lab/test 1]
    - [Lab/test 2]
  Suggested treatment considerations:
    - [Treatment option 1]
    - [Treatment option 2]
  Patient education points:
    - [Key point 1]
    - [Key point 2]
  Follow-up: [Recommended timeframe]
  Referral: [If indicated]

--- AI-GENERATED | PENDING PHYSICIAN REVIEW ---
```

### For Members (Plain Language, in their chosen language)

```
Kết Quả Khám Sức Khỏe AI / Your AI Health Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dựa trên những gì bạn chia sẻ, đây là những gì chúng tôi tìm thấy:
Based on what you shared, here's what we found:

[Plain language summary — no jargon, 6th grade reading level]

Các nguyên nhân có thể / Possible causes:
1. [Most likely] — [simple explanation]
2. [Second likely] — [simple explanation]

Bước tiếp theo / Next steps:
- [What to expect]
- [When your doctor will review]
- [What to watch for / when to go to ER]

⚕️ Bác sĩ sẽ xem xét kết quả này và liên hệ với bạn.
   A physician will review this and follow up with you.
```

---

## 7. Conversation Design Guidelines

### Tone & Style
- **Warm but professional** — "I'd like to understand more about what you're experiencing"
- **No medical jargon with members** — "high blood pressure" not "hypertension"
- **Acknowledge concerns** — "That sounds uncomfortable. Let me ask a few more questions to help your doctor."
- **Vietnamese cultural awareness:**
  - Use respectful pronouns (bạn, anh/chị depending on context)
  - Don't dismiss traditional remedies — ask about them non-judgmentally
  - Normalize mental health screening: "These are questions we ask everyone"

### Conversation Rules
1. **One question at a time** — Never ask multiple questions in one message
2. **Offer choices when appropriate** — "Is the pain: (A) sharp/stabbing, (B) dull/aching, (C) burning, (D) pressure-like?"
3. **Allow free text** — Don't force multiple choice for everything
4. **Acknowledge answers** — Brief acknowledgment before next question: "Got it." / "Thank you."
5. **Don't diagnose during conversation** — Save assessment for the final report
6. **Time estimate** — Tell member upfront: "This will take about 10-15 minutes"
7. **Progress indicator** — "We're about halfway through" helps completion rates
8. **Escape hatch** — Member can end early; AI generates partial report with "[Incomplete]" flag

### AI System Prompt Structure (for Dev Team)

```
You are a clinical intake assistant for Compass Vitals, a telehealth 
service for Vietnamese Americans. Your role is to conduct a thorough 
medical history interview, similar to what a physician would do in an 
initial visit.

RULES:
- Ask ONE question at a time
- Follow the OLDCARTS framework for HPI
- Screen for red flag symptoms early based on chief complaint
- Never provide a diagnosis during the conversation
- Never recommend specific medications during the conversation
- If emergency red flags detected, immediately provide emergency guidance
- Be culturally sensitive to Vietnamese health beliefs
- Track which intake sections are complete
- When all required sections are done, generate the SOAP note

LANGUAGE: Conduct the conversation in [member's chosen language].
SOAP note is always generated in English for physician review.
Patient summary is generated in member's chosen language.

REQUIRED SECTIONS (minimum for SOAP generation):
☐ Chief Complaint
☐ HPI (at least 6 of 8 OLDCARTS elements)
☐ Targeted ROS (at least 2 systems)
☐ PMH
☐ Current Medications
☐ Allergies
☐ Red flag screening (for applicable CC)
```

---

## 8. Data Points to Capture (Database Schema Guidance)

Each encounter should store:

```
encounter {
  id
  member_id
  language (vi | en)
  start_time
  end_time
  chief_complaint_raw (member's words)
  chief_complaint_category (standardized)
  
  hpi {
    onset, location, duration, character, 
    aggravating, relieving, temporal, severity,
    associated_symptoms[], prior_episodes
  }
  
  ros {
    system: finding (positive/negative/not_asked)
  }
  
  pmh {
    conditions[], surgeries[], hospitalizations[]
  }
  
  medications[] { name, dose, frequency }
  allergies[] { substance, reaction_type }
  
  social_history {
    smoking, alcohol, occupation, 
    exercise, diet_notes, traditional_remedies
  }
  
  family_history[] { relation, condition }
  
  vitals_self_reported {
    bp, glucose, weight, temperature
  }
  
  ai_output {
    differential_diagnoses[] { diagnosis, likelihood, evidence }
    soap_note (full text)
    patient_summary (full text, in member language)
    triage_level (routine | urgent | emergency)
    suggested_workup[]
    ai_confidence (high | medium | low)
    red_flags_detected[]
  }
  
  physician_review {
    reviewer_id
    review_time
    approved (bool)
    modifications (text)
    final_plan (text)
    prescriptions[]
    referrals[]
    follow_up_date
  }
  
  completion_status {
    cc: bool, hpi: bool, ros: bool, pmh: bool,
    meds: bool, allergies: bool, social: bool, family: bool
  }
  
  conversation_log[] { role, content, timestamp }
}
```

---

## 9. Quality Metrics to Track

| Metric | Target | Why |
|--------|--------|-----|
| Intake completion rate | >85% | Members finishing the full conversation |
| Average conversation length | 10-15 min | Too short = incomplete, too long = fatigue |
| Physician agreement with AI DDx | >70% top-1 match | AI accuracy benchmark |
| SOAP note modification rate | <30% requiring major edits | AI quality indicator |
| Red flag detection sensitivity | 100% | Safety — can never miss an emergency |
| Member satisfaction (post-encounter) | >4.0/5.0 | UX quality |
| Time from AI report → physician review | <4 hours (routine) | Service level |
| Vietnamese language accuracy | Physician-verified | No mistranslation of medical terms |

---

## 10. Next Steps

- [ ] **Physician Team**: Review this protocol, especially:
  - Are the top 10 complaints correct for your patient population?
  - Are the red flag protocols complete?
  - Any OLDCARTS modifications per complaint?
  - Vietnamese medical terminology review
- [ ] **Dev Team**: Use Section 7 (AI System Prompt) + Section 8 (Schema) to start building the prototype
- [ ] **Content Team**: Develop Vietnamese translations for all template questions
- [ ] **Everyone**: Test the intake flow by role-playing as patients with different complaints

---

_This protocol should be reviewed and updated by the CVH physician team before implementation. Clinical accuracy is paramount._
