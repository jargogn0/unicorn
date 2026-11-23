# STOCKHOLM — Game Design

## 1. Pitch

STOCKHOLM is a third-person open-world game about building a company from nothing in a living, recognisable Stockholm, and later San Francisco. It aims for GTA's freedom, density and cinematic missions, with the criminal underworld replaced by the founder journey: rent you can't pay, demos that crash, investors who say no, friends you let down, and the occasional enormous win.

The city must be fun with no mission active. You can walk Gamla Stan in the snow, take the view from Monteliusvägen, drive Söder Mälarstrand at blue hour, buy a cardamom bun or work a late night at the laptop.

## 2. Pillars

1. **Physical freedom.** Every story beat happens in a place you travel to, on foot, by car or by transit, in real weather.
2. **The founder journey, told truthfully.** Uncertainty, money, customers, rejection, sacrifice, luck.
3. **Consequences that persist.** People remember promises and how you treated them, and money changes your life. Being wealthy is not the same as the company succeeding.
4. **Recoverable failure.** Losing a deal, a room or an investor opens another path; it never ends the game.
5. **A real ecosystem, respectfully.** Real companies and places inspire missions. Real people are never portrayed or implied to endorse anything.

## 3. Core loop

Explore the city, meet people, and discover opportunities on the Founder Map. Take missions that use travel, conversation, timed decisions and objects. The consequences change your stats, relationships, cash and world state. That unlocks new places, people, housing, offices and markets, which you then explore.

Time runs at 1 real second = 30 game seconds in the Unreal build (48-minute days). The browser preview runs at 1 game minute per second. Sleeping skips to morning. Days matter because the rent is due on the 17th, people keep routines, and deadlines are real.

## 4. Progression dimensions

All of these are implemented in `FounderState` (`Stat` enum), the cap table and relationships:

- Personal cash and company cash, monthly burn, MRR, runway (derived), and whether the company is default-alive.
- Reputation, product quality, customers, pipeline, retention.
- Team size and capability, international reach.
- Funding and equity: SAFEs, priced rounds, option pool, board seats, a founder-control index, the liquidation preference stack.
- Wellbeing and energy (sleep, overwork, money stress).
- Housing tier 0–4 (sofa → penthouse) and office tier 0–4 (kitchen table → headquarters).
- Relationships: affinity, trust, memories and commitments for each NPC.

Funding is optional. Bootstrapping is a first-class route (chapter 7 accepts either). Joining the accelerator is optional (chapter 9) and never required for success.

## 5. Story structure (13 chapters)

| # | Chapter | Content status |
|---|---|---|
| 1 | Idea and Survival | **Implemented**: the opening and missions m00–m03 |
| 2 | Building the MVP | Design |
| 3 | First Customers | Design |
| 4 | Launch and Early Failures | Design |
| 5 | First Revenue | Design |
| 6 | Investor Rejection (The Investor Party, The Rejection) | Design |
| 7 | First Check or Bootstrapped Growth (The First Check) | Design |
| 8 | Hiring and Scaling | Design |
| 9 | Optional accelerator application and interview | Design |
| 10 | San Francisco (accelerator / customer / investor / self-funded paths) | Design |
| 11 | Product-Market Fit and Demo Day | Design |
| 12 | Later rounds, acquisitions, scale | Design |
| 13 | Endings: IPO, acquisition, or an independent profitable company | Design |

Chapter entry conditions live in `Content/Data/Story/chapters.json` and are evaluated by the simulation.

## 6. Chapter 1, the first 30 minutes (implemented)

The player's product is **Rota**, a scheduling and waste tool for small hospitality businesses. Players can rename it.

**m00 Five Days.**

- Opening cinematic: snow outside, the phone lights up with "Rent due in 5 days", and the laptop shows the unfinished product.
- Noor's message: "Hey. Heard you're building something. Can you show me?"
- You reply (a timed choice that shapes Noor's first impression), then grab the laptop.

**m01 Can You Show Me? (customer discovery).**

- Walk to Kafé Kollektivet on Hornsgatan before 13:00. If you're late, Noor reschedules for tomorrow; stand her up twice and her trust drops.
- The discovery conversation rewards listening over pitching and unlocks facts: scheduling pain, waste pain, willingness to pay.
- Walk to Gamla Stan to validate with Aditi, a former telecom engineer turned baker, who spots the offline-sync flaw.
- Go home and rework the product through the night. Product quality improves according to what you learned.

**m02 The First Pitch (product demo).**

- Choose how to cross the city: borrow Sami's Volvo (a promise to return it by 20:00 with a full tank), take the tunnelbana, or pay for a taxi.
- Heavy snow is forced. Be at Mälarbröd on Kungsholmen by 10:00; being late changes the meeting.
- The demo fails when the office wifi drops. You get a **12-second** decision:
  - Fix it live (needs product quality ≥ 20; a key-sequence minigame against the clock).
  - Switch to a manual spreadsheet walkthrough (needs the scheduling insight).
  - Ask to reschedule.
- Elin's verdict branches four ways: paid pilot, proposal request, honest no (the door stays open), or polite no.
- Return the Volvo on time, or Sami remembers it. The bus to the hospital takes fifty minutes.

**m02b Another Door (failure recovery).** A founders' breakfast, Mateo's advice ("who already loves you?"), Founder Map discoveries, and Noor offering to become the first customer.

**m03 First Payment.**

- Set your price: 1 490 / 2 900 / 4 900 kr per location. Premium needs proof.
- Choose how to invoice:
  - Sole trader (enskild firma).
  - Aktiebolag: needs 25 000 kr of share capital, which you can't afford yet.
  - Invoicing service: takes a 6 % cut.
- Negotiate monthly, quarter-upfront (10 % discount) or free month plus setup fee.
- Wait for the payment, then face the rent. A low price means you can't cover it: ask Gunilla for grace, or borrow from Sami and owe him.

**Chapter 2 begins.** The Founder Map gains Norrsken House and Almi Invest.

Money figures are gameplay approximations and are not presented as legal or tax advice. Tax isn't simulated in Chapter 1.

## 7. Missions: rules for every mission

- Every mission is physical: travel, place, time, people, objects.
- Each mission has at least one meaningful branch with persistent consequences: facts, memories, stats.
- Failure routes to an alternative (`fail_next`). `@fail` is reserved for optional content and always comes with a `recovery_hint`.
- Missions inspired by ecosystem entries reference them through `inspiration`. They fictionalise the challenge (for example music-licensing deadlock or payments trust) and never the people.

Designed signature missions: The Investor Party (Stureplan), The Rejection, The First Check (cash, control, dilution and timing, using `CounterAcceptProbability`), San Francisco, Demo Day.

## 8. Living city and life systems

- **NPC routines:** schedules per day type; the simulation decides presence and missions override it.
- **Ambient activities:** coffee, buns, the viewpoint, working at the laptop, sleep.
- **Planned:** saunas, the archipelago ferry, the KTH hackathon, meetups, clothing, apartment upgrades, a gym.
- **Phone:** Messages, Bank (pay rent), People (trust and affinity, remembered moments), Calendar (promises with deadlines), Founder Map.
- **Housing and eviction:** ten days of overdue rent loses you the sublet, and you move to a friend's sofa. That is recoverable.
- **The community** is international and diverse, written as individuals with motivations: Noor (café owner), Sami (ICU nurse, friend), Aditi (ex-telecom engineer, baker), Elin (operations head), Mateo (developer weighing whether to stay in Sweden), Helena (angel investor), Gunilla (landlord).

## 9. Narrative data language (for writers)

**Conditions** (an array means all must hold):

- Facts and stats: `{"fact":"x"}`, `{"fact":"x","op":">=","value":2}`, `{"stat":"mrr","op":">=","value":25000}`, plus `runway_months` and `founder_ownership`.
- Relationships: `{"rel":"noor","field":"trust","op":">=","value":40}`, `{"met":"aditi"}`, `{"memory":"sami","has":"car_late"}` (or `"lacks"`).
- Progress: `{"mission":"m01_show_me","status":"completed"}`, `{"chapter_at_least":3}`, `{"commitment":"id","status":"pending|fulfilled|broken|none"}`.
- World and money: `{"hour_between":[22,4]}`, `{"weekend":true}`, `{"weather_in":[...]}`, `{"discovered":"epicenter"}`, `{"can_afford":9400}`, `{"rent_paid":true}`.
- Logic: `all`, `any`, `not`.

**Effects:**

- Stats and facts: `add_stat`, `set_stat`, `set_fact`, `add_fact`.
- People: `rel` (affinity/trust), `meet`, `remember`, `forget`, `commit` (`due_hours`, `on_broken`, `on_fulfilled`), `fulfil`, `message`, `notify`.
- Missions and world: `start_mission`, `fail_mission`, `discover`, `advance_time`, `world_event`, `start_dialogue`.
- Money: `pay_rent`, `to_company`, `invoice`, `offer`, `accept_offer`, `decline_offer`.
- Branching: `chance` (`then`/`else`), `if` (`then`/`else`).

**Dialogue nodes** have:

- `speaker`, `text`, `anim` (gesture tag) and `camera` (shot tag).
- `effects` and `next`.
- `choices` (`if`, `locked_hint`, `hide_if_locked`).
- `timeout` and `timeout_choice` for timed choices.
- `branch`: silent routing on conditions; the last branch must be unconditional.
- `end`.

**Objectives** have:

- A `type`: reach, drive, talk, interact, decision, wait_until, phone_call or custom.
- `target`, `marker` and `dialogue`.
- Timing: `deadline` (with `deadline_anchor: "mission"` and `deadline_day_offset` for "tomorrow 10:00"), `time_limit_minutes`, `decision_seconds` and `decision_default`.
- Choices and hooks: `options`, `on_start`, `on_complete`.
- Routing: `next`, `next_if`, `on_fail` and `fail_next`.

Validation (`ContentDatabase::Validate`) catches missing nodes, locations, NPCs and dialogues, dead ends, and out-of-range timeouts.

## 10. Endings

IPO, acquisition, or an independent profitable company. Each is a legitimate win, and each is weighed by what it cost: wellbeing, relationships, control.
