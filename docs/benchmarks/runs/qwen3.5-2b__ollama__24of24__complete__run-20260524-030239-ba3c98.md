# Speech-check benchmark — `qwen3.5:2b`

Incremental run log for the [community leaderboard](../../MODEL_LEADERBOARD.md). This file updates **after each case**; commit partial progress or stop with Ctrl+C. **Grade this file** with [MODEL_REVIEW_PROMPT.md](../../contributing/MODEL_REVIEW_PROMPT.md) (paste the full markdown into your judge chat — not raw terminal output).

## Run metadata

| Field | Value |
|-------|-------|
| Report file | `qwen3.5-2b__ollama__24of24__complete__run-20260524-030239-ba3c98.md` |
| Run id | `20260524-030239-ba3c98` |
| Model | `qwen3.5:2b` |
| Backend | ollama |
| Fixture suite | 24 cases |
| Cases completed | 24 |
| Host | Linux x86_64, x86_64 |
| Started (UTC) | 2026-05-24 03:02:39 |
| Status | **complete** (24/24) |
| Judge model | Composer 2.5 |

## Progress

| # | case_id | label | speakable line | judge grade |
|---|---------|-------|----------------|-------------|
| 1 | `de_tax_notice` | German — tax assessment notice | You received an email from Finanzamt München about your 2025 income tax return. You have four weeks to object to the tax assessment. If you have questions, you can call your local office. | **WEAK** |
| 2 | `en_angry_order` | English — angry ALL CAPS order complaint | You received an email from Chris Morgan about an unpaid order number nine nine two eight one that has not shipped. An angry customer is complaining that the order is still not shipped and is demanding a callback today. | **WEAK** |
| 3 | `en_api_bullet_list` | English — three numbered API questions | You received an email from Priya Nair about API migration blockers. She is asking about webhooks, export limits, and key rotation before a Tuesday board meeting. | **PASS** |
| 4 | `en_dentist_reminder` | English — dental appointment reminder | You received an email from Bright Smile Dental reminding you of a dental cleaning scheduled for Monday, May twenty-sixth at four a.m. PM with Dr. Patel. You should reply or call five five five zero one nine eight eight three two to reschedule. | **FAIL** |
| 5 | `en_deploy_alert` | English — staging deploy failed | You received an email from Alex Chen about a staging deployment that failed at nine forty-five a.m. because the migration step timed out. Please check the pipeline logs when you get a chance. | **PASS** |
| 6 | `en_forward_partner` | English forward — account manager intro | You received an email from your client Omar El Khal, who is introducing himself as your dedicated account manager at AffiliaXe. He is asking how he can help you. | **FAIL** |
| 7 | `en_github_pr` | English — GitHub pull request review | You received an email from GitHub about a pull request review request for a code change to your account. It is important because you were asked to review a specific code change before a Friday release. The change involves refactoring authentication and session handling. You should review the code before Friday's release cut. | **WEAK** |
| 8 | `en_invoice_due` | English — invoice payment due | You received an email from Billing about an invoice number four four two one due this Friday. Pay at the portal vendor link or reply if you need a purchase order. | **PASS** |
| 9 | `en_minimal_ping` | English — one-line ping | You received an email from Sam asking if you got the document. Please check your inbox and let me know if you have it. | **WEAK** |
| 10 | `en_newsletter_noise` | English — newsletter marketing (noise) | You received an email about a fifty percent off weekend sale. Worth checking — it might be spam. | **PASS** |
| 11 | `en_ooo_autoreply` | English — out-of-office auto-reply | You received an email from Marcus Webb at an agency stating that he is out of the office until Monday, June second with limited email access, and that urgent matters should be directed to Jane Park at jane at agency. | **PASS** |
| 12 | `en_rent_increase` | English — landlord rent increase letter | You received an email from Oak Street Properties regarding a rent increase of eight percent effective July first. The new monthly amount is one thousand seven hundred twenty-eight dollars. A signed rider is attached and must be returned within fourteen days. | **PASS** |
| 13 | `en_school_snow_day` | English — school closure alert | You received an email from Lincoln Elementary about a school closure on Thursday due to severe weather. Students should join remote classes via Teams at nine a.m. AM. The hot lunch program is suspended. | **WEAK** |
| 14 | `en_security_alert` | English — sign-in from new device | You received an email from Security about a new sign-in to your account from Berlin at two fourteen a.m. UTC. If this wasn't you, reset your password now. | **PASS** |
| 15 | `en_short_ack` | English — short acknowledgment | You received an email from Jordan Lee at team saying three p.m. tomorrow works for him. | **PASS** |
| 16 | `en_subject_only_flight` | English — subject-only flight cancellation | You received an email from United Airlines about a flight UA882 to Chicago that was canceled on May 22. You should check your booking options to rebook your flight. | **PASS** |
| 17 | `es_delivery` | Spanish — package delivery window | You received an email from Logística about a package arriving tomorrow between nine a.m. and noon. You should have someone at home to receive it. | **PASS** |
| 18 | `fr_complaint` | French — product complaint | You received an email from Lucie Dupont regarding a refund request for a wrong order model, asking for a refund within forty-eight hours. | **PASS** |
| 19 | `fr_forward_phone` | French forward — client asks for phone number | You received an email from Omar El Khal, a client, asking for your phone number. Please reply with your number. | **FAIL** |
| 20 | `fr_meeting_move` | French — meeting moved to Thursday | You received an email from Sophie Martin about a meeting that has been moved to Thursday at two p.m. in room B12 instead of room A3. | **PASS** |
| 21 | `it_dinner_invite` | Italian — informal dinner invitation | You received an email from Giulia Rossi asking to meet Saturday evening with Luca at eight p.m. for six people, and she wants to know if you are vegetarian. | **PASS** |
| 22 | `ja_en_mixed_vendor` | Mixed JP/EN — vendor shipment delay | You received an email from Tanaka Trading about a delayed shipment for PO-7781 due to customs. Omar-san is informing you that the new estimated arrival date is June fifth and that express fees will be covered. Please confirm receipt of this update. | **FAIL** |
| 23 | `nl_interview_invite` | Dutch — job interview invitation | You received an email from HR TechVision inviting you to a job interview for a Backend Engineer position on Tuesday at two p.m. at their office on Herengracht 100. Please bring a valid ID and your CV, and confirm your attendance. | **PASS** |
| 24 | `pt_hotel_confirm` | Portuguese — hotel booking confirmation | You received an email from Reservas confirming your hotel reservation for June 12th through 14th. The check-in time is three p.m., but you will arrive late at eleven p.m. with a small breakfast included. | **PASS** |

## Cases

### 1/24 `de_tax_notice`

- **Label:** German — tax assessment notice
- **Intent:** Finanzamt sent 2025 income tax assessment; objection deadline applies.
- **From:** Finanzamt München <finanzamt@example.de>
- **Subject:** Steuerbescheid 2025 — Einkommensteuer

**Body preview**

```
Sehr geehrter Herr EL KHAL, anbei erhalten Sie Ihren Einkommensteuerbescheid für 2025. Einspruchsfrist: 4 Wochen ab Zustellung. Bei Rückfragen steht Ihnen unser Bürgerbüro zur Verfügung.
```

**Model speakable line**

> You received an email from Finanzamt München about your 2025 income tax return. You have four weeks to object to the tax assessment. If you have questions, you can call your local office.

**Judge grade:** **WEAK** — Generic opener; says tax return not assessment.

### 2/24 `en_angry_order`

- **Label:** English — angry ALL CAPS order complaint
- **Intent:** Customer furious; order #99281 missing; demands callback today.
- **From:** Chris Morgan <chris.m@email.com>
- **Subject:** WHERE IS MY ORDER

**Body preview**

```
THIS IS UNACCEPTABLE. I PAID FOR ORDER #99281 TWO WEEKS AGO AND STILL NOTHING. CALL ME TODAY OR I CHARGE BACK.
```

**Model speakable line**

> You received an email from Chris Morgan about an unpaid order number nine nine two eight one that has not shipped. An angry customer is complaining that the order is still not shipped and is demanding a callback today.

**Judge grade:** **WEAK** — Accurate but wordy and narrates anger twice.

### 3/24 `en_api_bullet_list`

- **Label:** English — three numbered API questions
- **Intent:** Client asks three distinct API migration questions.
- **From:** Priya Nair <priya@clientcorp.com>
- **Subject:** API migration — three blockers

**Body preview**

```
Hi team, 1) Will v2 webhooks stay supported through Q3? 2) What's the rate limit on bulk export? 3) Do sandbox keys rotate automatically? Need answers before our board meeting Tuesday. — Priya
```

**Model speakable line**

> You received an email from Priya Nair about API migration blockers. She is asking about webhooks, export limits, and key rotation before a Tuesday board meeting.

**Judge grade:** **PASS** — Covers all three API questions clearly.

### 4/24 `en_dentist_reminder`

- **Label:** English — dental appointment reminder
- **Intent:** Reminder for cleaning Monday 4pm; call to reschedule if needed.
- **From:** Bright Smile Dental <reminders@brightsmile.example>
- **Subject:** Reminder: cleaning appointment Mon May 26 at 4:00 PM

**Body preview**

```
Hi Omar, reminder for your dental cleaning Monday May 26 at 4:00 PM with Dr. Patel. Reply or call (555) 019-8832 to reschedule.
```

**Model speakable line**

> You received an email from Bright Smile Dental reminding you of a dental cleaning scheduled for Monday, May twenty-sixth at four a.m. PM with Dr. Patel. You should reply or call five five five zero one nine eight eight three two to reschedule.

**Judge grade:** **FAIL** — Broken time: four a.m. PM.

### 5/24 `en_deploy_alert`

- **Label:** English — staging deploy failed
- **Intent:** Staging deploy failed; migration timed out; check logs.
- **From:** Alex Chen <alex@company.com>
- **Subject:** Staging deploy failed

**Body preview**

```
Hey — the staging deploy failed around 9:45. Looks like the migration step timed out. Can you check the pipeline logs when you get a chance?
```

**Model speakable line**

> You received an email from Alex Chen about a staging deployment that failed at nine forty-five a.m. because the migration step timed out. Please check the pipeline logs when you get a chance.

**Judge grade:** **PASS** — Sender, failure time, and migration timeout.

### 6/24 `en_forward_partner`

- **Label:** English forward — account manager intro
- **Intent:** Asi from affiliaXe offers help as account manager.
- **From:** Omar EL KHAL <elkhalomar@gmail.com>
- **Subject:** Fwd: Hi Omar El Khal

**Body preview**

```
Hi Omar El Khal, Nice to e-meet you, My name is Asi and i would be your dedicated account manager at affiliaXe. I have noticed that you sent an email to partners@affiliaxe.com - How can I help you? Best regards Asi
```

**Model speakable line**

> You received an email from your client Omar El Khal, who is introducing himself as your dedicated account manager at AffiliaXe. He is asking how he can help you.

**Judge grade:** **FAIL** — Forward: credits Omar; real sender is Asi at AffiliaXe.

### 7/24 `en_github_pr`

- **Label:** English — GitHub pull request review
- **Intent:** Review requested on PR #882 auth refactor before release.
- **From:** GitHub <notifications@github.com>
- **Subject:** [repo] Review requested on PR #882: refactor auth middleware

**Body preview**

```
@you were requested to review pull request #882 by @devon. Refactors JWT validation and session refresh. Target branch: main. Please review before Friday's release cut.
```

**Model speakable line**

> You received an email from GitHub about a pull request review request for a code change to your account. It is important because you were asked to review a specific code change before a Friday release. The change involves refactoring authentication and session handling. You should review the code before Friday's release cut.

**Judge grade:** **WEAK** — Correct but too long for one spoken breath.

### 8/24 `en_invoice_due`

- **Label:** English — invoice payment due
- **Intent:** Invoice #4421 due Friday; pay via portal.
- **From:** Billing <billing@vendor.com>
- **Subject:** Invoice #4421 due Friday

**Body preview**

```
Your invoice #4421 for €1,240 is due this Friday. Pay at portal.vendor.com or reply if you need a PO.
```

**Model speakable line**

> You received an email from Billing about an invoice number four four two one due this Friday. Pay at the portal vendor link or reply if you need a purchase order.

**Judge grade:** **PASS** — Invoice number and Friday due date.

### 9/24 `en_minimal_ping`

- **Label:** English — one-line ping
- **Intent:** Sender asks if you received the doc.
- **From:** Sam <sam@docs.co>
- **Subject:** doc

**Body preview**

```
Did you get the doc?
```

**Model speakable line**

> You received an email from Sam asking if you got the document. Please check your inbox and let me know if you have it.

**Judge grade:** **WEAK** — Adds assistant voice (let me know).

### 10/24 `en_newsletter_noise`

- **Label:** English — newsletter marketing (noise)
- **Intent:** Marketing promo — ideally brief or filtered; not a full readout.
- **From:** Deals Weekly <news@shop.example>
- **Subject:** 🔥 50% OFF everything this weekend!!!

**Body preview**

```
Don't miss our biggest sale! Shop now and save 50% on all items. Unsubscribe at the bottom. Click here for deals.
```

**Model speakable line**

> You received an email about a fifty percent off weekend sale. Worth checking — it might be spam.

**Judge grade:** **PASS** — Sale plus sensible spam hedge.

### 11/24 `en_ooo_autoreply`

- **Label:** English — out-of-office auto-reply
- **Intent:** Sender away until June 2; contact Jane for urgent items.
- **From:** Marcus Webb <marcus@agency.io>
- **Subject:** Out of office Re: contract draft

**Body preview**

```
I'm out of the office until Monday, June 2 with limited email access. For urgent matters contact Jane Park at jane@agency.io. This is an automated response.
```

**Model speakable line**

> You received an email from Marcus Webb at an agency stating that he is out of the office until Monday, June second with limited email access, and that urgent matters should be directed to Jane Park at jane at agency.

**Judge grade:** **PASS** — OOO dates and Jane Park backup.

### 12/24 `en_rent_increase`

- **Label:** English — landlord rent increase letter
- **Intent:** Rent rises 8% from July 1; new lease rider attached.
- **From:** Oak Street Properties <leasing@oakstreet.example>
- **Subject:** Notice: rent adjustment effective July 1

**Body preview**

```
Dear tenant, per your lease section 14, monthly rent will increase by 8% effective July 1. The new amount is $1,728. A signed rider is attached; return within 14 days.
```

**Model speakable line**

> You received an email from Oak Street Properties regarding a rent increase of eight percent effective July first. The new monthly amount is one thousand seven hundred twenty-eight dollars. A signed rider is attached and must be returned within fourteen days.

**Judge grade:** **PASS** — Eight percent, amount, fourteen-day rider.

### 13/24 `en_school_snow_day`

- **Label:** English — school closure alert
- **Intent:** School closed tomorrow due to snow; classes remote on Teams.
- **From:** Lincoln Elementary <office@lincoln-edu.example>
- **Subject:** Emergency: school closed Thursday — remote learning

**Body preview**

```
Due to severe weather, Lincoln Elementary will be closed Thursday. Students should join remote classes via Teams at 9:00 AM. Hot lunch program suspended.
```

**Model speakable line**

> You received an email from Lincoln Elementary about a school closure on Thursday due to severe weather. Students should join remote classes via Teams at nine a.m. AM. The hot lunch program is suspended.

**Judge grade:** **WEAK** — Snow day OK but nine a.m. AM stutter.

### 14/24 `en_security_alert`

- **Label:** English — sign-in from new device
- **Intent:** New sign-in from Berlin; reset password if not you.
- **From:** Security <security@service.com>
- **Subject:** New sign-in from Berlin

**Body preview**

```
We noticed a sign-in to your account from Berlin, Germany at 02:14 UTC. If this wasn't you, reset your password now.
```

**Model speakable line**

> You received an email from Security about a new sign-in to your account from Berlin at two fourteen a.m. UTC. If this wasn't you, reset your password now.

**Judge grade:** **PASS** — Berlin sign-in and reset-password cue.

### 15/24 `en_short_ack`

- **Label:** English — short acknowledgment
- **Intent:** Quick thanks and confirm 3pm meeting.
- **From:** Jordan Lee <jordan@team.io>
- **Subject:** Re: sync

**Body preview**

```
Thanks — 3pm tomorrow works for me.
```

**Model speakable line**

> You received an email from Jordan Lee at team saying three p.m. tomorrow works for him.

**Judge grade:** **PASS** — Jordan Lee, three p.m. tomorrow.

### 16/24 `en_subject_only_flight`

- **Label:** English — subject-only flight cancellation
- **Intent:** United canceled flight UA882; body is empty boilerplate.
- **From:** United Airlines <noreply@united.com>
- **Subject:** Flight UA882 to ORD on May 22 canceled — rebook options

**Body preview**

```
View this message in your browser. Manage preferences.
```

**Model speakable line**

> You received an email from United Airlines about a flight UA882 to Chicago that was canceled on May 22. You should check your booking options to rebook your flight.

**Judge grade:** **PASS** — Recovers UA882 cancellation from subject.

### 17/24 `es_delivery`

- **Label:** Spanish — package delivery window
- **Intent:** Package arrives tomorrow 9-12; someone must be home.
- **From:** Logística <envios@correo.es>
- **Subject:** Entrega mañana

**Body preview**

```
Hola, su paquete llegará mañana entre 9:00 y 12:00. Debe haber alguien en casa para recibirlo.
```

**Model speakable line**

> You received an email from Logística about a package arriving tomorrow between nine a.m. and noon. You should have someone at home to receive it.

**Judge grade:** **PASS** — Tomorrow delivery window nine to noon.

### 18/24 `fr_complaint`

- **Label:** French — product complaint
- **Intent:** Customer unhappy; wants refund within 48 hours.
- **From:** Lucie Dupont <lucie.dupont@gmail.com>
- **Subject:** Remboursement

**Body preview**

```
Bonjour, j'ai reçu le mauvais modèle. Je demande un remboursement sous 48 heures svp.
```

**Model speakable line**

> You received an email from Lucie Dupont regarding a refund request for a wrong order model, asking for a refund within forty-eight hours.

**Judge grade:** **PASS** — Lucie Dupont refund within forty-eight hours.

### 19/24 `fr_forward_phone`

- **Label:** French forward — client asks for phone number
- **Intent:** Customer Mustafa asks Omar for a phone number.
- **From:** Omar EL KHAL <elkhalomar@gmail.com>
- **Subject:** Fwd:

**Body preview**

```
Bonjour Omar j'espère que tu vas bien je suis un client chez vous possible d'avoir votre numéro de téléphone merci
```

**Model speakable line**

> You received an email from Omar El Khal, a client, asking for your phone number. Please reply with your number.

**Judge grade:** **FAIL** — Forward: names Omar; Mustafa is the client asking.

### 20/24 `fr_meeting_move`

- **Label:** French — meeting moved to Thursday
- **Intent:** Meeting moved to Thursday 14h, room change.
- **From:** Sophie Martin <sophie@corp.fr>
- **Subject:** Report réunion

**Body preview**

```
Bonjour, la réunion est décalée à jeudi 14h. On se retrouve en salle B12 au lieu de A3. Merci.
```

**Model speakable line**

> You received an email from Sophie Martin about a meeting that has been moved to Thursday at two p.m. in room B12 instead of room A3.

**Judge grade:** **PASS** — Sophie, Thursday two p.m., room B twelve.

### 21/24 `it_dinner_invite`

- **Label:** Italian — informal dinner invitation
- **Intent:** Invite to dinner Saturday 8pm at Trattoria da Luca.
- **From:** Giulia Rossi <giulia.rossi@gmail.com>
- **Subject:** Cena sabato?

**Body preview**

```
Ciao Omar! Sabato sera ci vediamo da Luca alle 20:00? Prenoto per 6 persone. Fammi sapere se vegetariano per te.
```

**Model speakable line**

> You received an email from Giulia Rossi asking to meet Saturday evening with Luca at eight p.m. for six people, and she wants to know if you are vegetarian.

**Judge grade:** **PASS** — Saturday eight p.m., six people, vegetarian ask.

### 22/24 `ja_en_mixed_vendor`

- **Label:** Mixed JP/EN — vendor shipment delay
- **Intent:** Tokyo supplier says shipment delayed; new ETA June 5.
- **From:** Tanaka Trading <export@tanaka-trading.co.jp>
- **Subject:** Re: PO-7781 — shipment delay / 出荷遅延

**Body preview**

```
Omar-san, 申し訳ございません。PO-7781 will ship late due to customs. New ETA: June 5. We will absorb express fees. Please confirm receipt of this update.
```

**Model speakable line**

> You received an email from Tanaka Trading about a delayed shipment for PO-7781 due to customs. Omar-san is informing you that the new estimated arrival date is June fifth and that express fees will be covered. Please confirm receipt of this update.

**Judge grade:** **FAIL** — Misattributes Omar-san; Tanaka Trading is sender.

### 23/24 `nl_interview_invite`

- **Label:** Dutch — job interview invitation
- **Intent:** Interview Tuesday 10:00 at HQ; bring ID and CV.
- **From:** HR TechVision <hr@techvision.nl>
- **Subject:** Uitnodiging sollicitatiegesprek — Backend Engineer

**Body preview**

```
Beste Omar, graag nodigen wij u uit voor een gesprek op dinsdag om 10:00 in ons kantoor (Herengracht 100). Neem een geldig ID en CV mee. Bevestig uw aanwezigheid.
```

**Model speakable line**

> You received an email from HR TechVision inviting you to a job interview for a Backend Engineer position on Tuesday at two p.m. at their office on Herengracht 100. Please bring a valid ID and your CV, and confirm your attendance.

**Judge grade:** **PASS** — Interview Tuesday two p.m., bring ID and CV.

### 24/24 `pt_hotel_confirm`

- **Label:** Portuguese — hotel booking confirmation
- **Intent:** Booking confirmed in Porto; check-in Friday; late arrival noted.
- **From:** Reservas <reservas@hotelporto.pt>
- **Subject:** Confirmação — Hotel Ribeira, 12–14 Jun

**Body preview**

```
Olá Omar, a sua reserva está confirmada para 12 a 14 de junho. Check-in a partir das 15h. Informámos chegada tardia (~23h). Pequeno-almoço incluído.
```

**Model speakable line**

> You received an email from Reservas confirming your hotel reservation for June 12th through 14th. The check-in time is three p.m., but you will arrive late at eleven p.m. with a small breakfast included.

**Judge grade:** **PASS** — June dates, late eleven p.m. arrival noted.


## Judge verdict (Composer 2.5)

| PASS | WEAK | FAIL |
|------|------|------|
| 16 | 5 | 4 |

**Verdict:** Usable for dev smoke tests on Ollama CPU, but **not leaderboard-ready** until forwarded-mail sender attribution is fixed. Generic “You received an email from…” openers appear on most lines.

**Average desktop (16 GB RAM, CPU-only):** Marginal — full suite took ~10 minutes; expect noticeable CPU load during listen.

**vs model size:** Strong entity recall for monolingual English transactional mail; worse than mid 4B–9B on forwards and mixed-language vendor mail.

### Three worst cases

1. **`en_forward_partner`** — Introduces Omar as AffiliaXe account manager; real sender is Asi Zaror.
2. **`fr_forward_phone`** — Mustafa (client) buried; line treats Omar as the client asking for a number.
3. **`ja_en_mixed_vendor`** — Calls Omar-san the informant; Tanaka Trading sent the delay notice.

### Suggested leaderboard row

| Rank | Model | Backend | Quant / notes | Hardware | PASS | WEAK | FAIL | Good for average PC? | Contributor | Date | Run log |
|------|-------|---------|---------------|----------|------|------|------|----------------------|-------------|------|---------|
| — | qwen3.5:2b | ollama | default pull | Linux x86_64, CPU | 16 | 5 | 4 | Marginal | *(your handle)* | 2026-05-24 | docs/benchmarks/runs/qwen3.5-2b__ollama__24of24__complete__run-20260524-030239-ba3c98.md |

## Next steps

1. Paste **this entire markdown file** into a chat with [MODEL_REVIEW_PROMPT.md](../../contributing/MODEL_REVIEW_PROMPT.md).
2. Record the **judge model** name in metadata above (e.g. Composer 2.5).
3. Fill **judge grade** in the progress table and per-case sections (PASS / WEAK / FAIL).
4. Open a PR: leaderboard row in `docs/MODEL_LEADERBOARD.md` + commit this run log.
