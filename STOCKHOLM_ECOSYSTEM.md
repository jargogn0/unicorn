# STOCKHOLM: Founder Map ecosystem research

*Researched on 2026-11-23. Data file: `Stockholm/Content/Data/Ecosystem/stockholm_ecosystem.json` (schema v1, 39 entries: 16 partially_verified, 23 verified).*

## 1. Purpose and method

This document supports the **Founder Map** layer of STOCKHOLM, an original open-world game about building a startup in Stockholm. It lists real organisations in the Stockholm tech ecosystem (landmark companies, investors, accelerators, coworking spaces, universities and recurring events) so the map can feel grounded. All missions and characters are fictional.

**Method**

1. A seed list of organisations was checked one by one with web search (company sites, press releases, regulatory filings, reputable tech press) and Wikipedia. Wikipedia heavily rate-limited automated access during this session, so a few Wikipedia citations were read through search-result extracts or the REST summary endpoint rather than as full articles.
2. For each entry we recorded the founding year, public founder names, a short history, **current status as of November 2026** (listing, acquisition, bankruptcy, shutdown), unicorn history, and locations.
3. Every key fact is tied to at least one source URL in the entry's `sources` array. Where sources conflicted, the conflict is written in the entry's `notes`.
4. Each entry is graded:
   - **verified**: all key facts sourced, no unresolved material conflict.
   - **partially_verified**: core facts sourced, but something material is missing or conflicting (founding year, address, founders).
   - **unverified**: not used. Weak entries were dropped rather than included.
5. "Fewer, correct entries" beats coverage. Organisations from the seed list that could not be sourced well enough were left out (see section 6).

## 2. Licensing, ethics and data rules

- **No impersonation of real people.** Founder names appear in the data only as public historical facts. The game must **not** portray real founders, investors or executives as characters, quote them, or imply that they endorse anything. NPCs inspired by these organisations must be fictional people with fictional names.
- **No implied endorsement by real organisations.** Real organisations may appear as map landmarks or ambient world detail. Missions should use *fictional* companies whose challenges are inspired by real ones. Each `storyline_hooks` entry describes a **company challenge archetype** (for example "music-licensing negotiations" or "payments trust problem"), not a script involving the real firm.
- **Handle failures with care.** Bankruptcies (Northvolt), layoffs (King 2025) and shutdowns (Skype) affected real people. Use them only as abstracted cautionary archetypes, never for mockery.
- **No invented addresses or coordinates.** An address is recorded only when a cited source states it, and the entry records which source. Addresses from aggregators (Yahoo Finance, CB Insights) are flagged in `notes`. **All `lat`/`lon` values are `null` by design.**
- **Geocoding comes from OpenStreetMap.** Coordinates will be added later by geocoding against OpenStreetMap data, licensed under the **Open Database License (ODbL)**. The game and its credits must show the attribution **"© OpenStreetMap contributors"**, and any derived database must follow ODbL share-alike terms.
- **Precision levels.** `address` = street and number from a source; `street` = street only; `district` = neighbourhood only; `city` = Stockholm only. **District-precision entries are placed at a district anchor point and must be labelled "approximate location" in-game.** City-precision entries should not get a map pin unless a designer picks a deliberately generic spot, also labelled approximate.
- **District inference.** Some `district` values were inferred from a sourced address or postcode, for example Västgötagatan 2 / 118 27 = Södermalm. These are flagged and should be confirmed during OSM geocoding. `other` means outside the enumerated districts (for example Danderyd or Skellefteå) or unknown.
- **Data freshness.** The data reflects sources seen up to **2026-11-23**. Statuses such as share listings, valuations, leadership and office locations go stale. Re-verify before shipping, and record the check date.
- **Nulls mean "not verified".** For example `unicorn.ever: null` means we did not confirm it. It does not mean "false".

## 3. Tables by category

An organisation can appear under more than one category. "Location precision" is the best precision across the entry's recorded locations.

### Unicorn landmarks (historical and current)

| Name | Founded | Status (as of 2026-11) | Location precision | Verification |
|---|---|---|---|---|
| Spotify | 2006 | public (NYSE: SPOT) | address | verified |
| Klarna | 2005 | public (NYSE: KLAR) | address | verified |
| King (Candy Crush) | 2003 | subsidiary; owner: Microsoft (via Activision Blizzard) | address (historical only) | verified |
| Mojang Studios (Minecraft) | 2009 | subsidiary; owner: Microsoft | address | partially_verified |
| Skype | 2003 | defunct; owner: Microsoft | city (historical only) | verified |
| Zettle by PayPal (formerly iZettle) | 2010 | subsidiary; owner: PayPal | city | verified |
| Tink | 2012 | subsidiary; owner: Visa | city | verified |
| Lovable | 2023 | private | city | verified |
| Legora (formerly Leya) | 2023 | private | city | verified |
| Epidemic Sound | 2009 | private | address | verified |
| Truecaller | 2009 | public (Nasdaq Stockholm: TRUE B) | address | partially_verified |
| Voi Technology | 2018 | private | city | verified |

### Other startups and scaleups

| Name | Founded | Status (as of 2026-11) | Location precision | Verification |
|---|---|---|---|---|
| Lovable | 2023 | private | city | verified |
| Legora (formerly Leya) | 2023 | private | city | verified |
| Northvolt | 2016 | bankrupt; owner: Lyten (assets) | city (historical only) | partially_verified |
| Voi Technology | 2018 | private | city | verified |
| Kry (Livi) | 2015 | private | city | partially_verified |
| Einride | 2016 | public (Nasdaq: ENRD) | city | verified |
| Trustly | 2008 | private | city | partially_verified |
| Sana (formerly Sana Labs) | 2016 | acquired; owner: Workday | city (historical only) | verified |
| Paradox Interactive | 1999 | public (Nasdaq Stockholm: PDX) | district | partially_verified |
| EA DICE | 1992 | subsidiary; owner: Electronic Arts | city | partially_verified |
| Tobii | 2001 | public (Nasdaq Stockholm: TOBII) | address | partially_verified |
| Bambuser | 2007 | public (Nasdaq First North: BUSER) | city | partially_verified |

### Venture capital and investors

| Name | Founded | Status (as of 2026-11) | Location precision | Verification |
|---|---|---|---|---|
| Creandum | 2003 | private | address | verified |
| EQT Ventures | 2016 | subsidiary; owner: EQT AB (parent) | address | partially_verified |
| Northzone | 1996 | private | address | verified |
| Almi Invest | 2009 | institution | city | verified |
| Industrifonden | 1979 | institution | city | verified |
| Antler (Stockholm / Nordics) | n/a | private | city | partially_verified |

### Accelerators and incubators

| Name | Founded | Status (as of 2026-11) | Location precision | Verification |
|---|---|---|---|---|
| KTH Innovation | 2007 | institution | address | verified |
| Sting (Stockholm Innovation & Growth) | 2002 | nonprofit | address | verified |
| SSE Business Lab | 2001 | institution | district | partially_verified |
| Antler (Stockholm / Nordics) | n/a | private | city | partially_verified |

### Coworking and innovation houses

| Name | Founded | Status (as of 2026-11) | Location precision | Verification |
|---|---|---|---|---|
| Epicenter Stockholm | 2015 | private | address | verified |
| Norrsken House Stockholm (Norrsken Foundation) | 2016 | nonprofit | address | verified |
| Kista Science City | 1986 | nonprofit | district | partially_verified |
| SUP46 (Start-Up People of Sweden) | 2013 | private | address | partially_verified |

### Universities and research clusters

| Name | Founded | Status (as of 2026-11) | Location precision | Verification |
|---|---|---|---|---|
| KTH Innovation | 2007 | institution | address | verified |
| KTH Royal Institute of Technology | 1827 | institution | district | verified |
| Kista Science City | 1986 | nonprofit | district | partially_verified |
| Stockholm School of Economics (SSE) | 1909 | institution | address | verified |

### Founder events

| Name | Founded | Status (as of 2026-11) | Location precision | Verification |
|---|---|---|---|---|
| Epicenter Stockholm | 2015 | private | address | verified |
| SUP46 (Start-Up People of Sweden) | 2013 | private | address | partially_verified |
| Nordic Tech Week | n/a | private | district | partially_verified |
| STHLM Tech Fest / SthlmTech meetup (historical) | 2013 | defunct | district (historical only) | partially_verified |

### Potential customers (corporates)

| Name | Founded | Status (as of 2026-11) | Location precision | Verification |
|---|---|---|---|---|
| Spotify | 2006 | public (NYSE: SPOT) | address | verified |
| Klarna | 2005 | public (NYSE: KLAR) | address | verified |
| Zettle by PayPal (formerly iZettle) | 2010 | subsidiary; owner: PayPal | city | verified |
| Tink | 2012 | subsidiary; owner: Visa | city | verified |
| Epidemic Sound | 2009 | private | address | verified |
| Truecaller | 2009 | public (Nasdaq Stockholm: TRUE B) | address | partially_verified |
| Trustly | 2008 | private | city | partially_verified |
| Paradox Interactive | 1999 | public (Nasdaq Stockholm: PDX) | district | partially_verified |
| EA DICE | 1992 | subsidiary; owner: Electronic Arts | city | partially_verified |
| Tobii | 2001 | public (Nasdaq Stockholm: TOBII) | address | partially_verified |
| Ericsson | 1876 | public (Nasdaq Stockholm: ERIC B; Nasdaq: ERIC) | address | verified |

## 4. Key organisations: narratives and storyline opportunities

These are short factual recaps (full sourcing is in the JSON) plus mission *inspiration*. Missions must star fictional companies and people.

### Spotify

Founded in Stockholm in 2006 and listed on the NYSE in 2018 through a direct listing (no new capital raised). Since 1 January 2026, Daniel Ek has been executive chairman, with two co-CEOs. HQ: Regeringsgatan 19 (Spotify's own press page).

*Storyline opportunities:* rights-holder negotiations before launch; converting free users to paying ones; a founder handing over day-to-day control.

### Klarna

Founded in 2005 by three Stockholm School of Economics students. It created a UK holding company (Klarna Group plc) before listing on the NYSE on 10 September 2025 at $40 per share. The shares later fell far below that price; Q3 2026 revenue was about $1B with a net loss. Klarna Bank AB's head office is Sveavägen 46.

*Storyline opportunities:* a payments trust problem; growing a loan book without letting credit losses eat the margin; life as a public company after the IPO.

### King (Candy Crush)

Founded in August 2003 as Midasplayer.com and nearly went bankrupt in its first year. Candy Crush Saga (2012) made it huge. Activision Blizzard bought it in 2016, and Microsoft bought Activision Blizzard in 2023. In July 2025 King cut about 10% of its staff, mostly in Stockholm.

*Storyline opportunities:* surviving until the first hit; following up a mega-hit; keeping a studio's culture under a corporate parent.

### Mojang Studios (Minecraft)

Minecraft began as a side project in 2009. Microsoft bought Mojang for $2.5B (announced September 2014, completed November 2014). It is now an Xbox studio on Södermalm.

*Storyline opportunities:* an indie hit forces a solo developer to become a company; whether to sell to a platform giant.

### Skype

A Swedish-Danish founder pair, Estonian engineers and a Luxembourg registration. Microsoft bought Skype for $8.5B in 2011 and retired the consumer service on 5 May 2025. In-game, this should appear only as a historical landmark.

*Storyline opportunities:* scaling peer-to-peer calling; a product shut down by its corporate parent.

### Zettle by PayPal (formerly iZettle)

Card reader and point-of-sale company for small merchants, founded in 2010. PayPal bought it for about $2.2B in 2018 (cancelling a planned IPO), and it was renamed 'Zettle by PayPal' in 2021.

*Storyline opportunities:* hardware and software merchants trust; IPO versus trade sale.

### Tink

Open-banking platform founded in 2012. Visa bought it in March 2022 (about €1.8B) and runs it as a standalone subsidiary headquartered in Stockholm.

*Storyline opportunities:* integrating with thousands of banks; building a product around a regulatory deadline.

### Lovable

Grew out of the open-source GPT Engineer project. It became a unicorn in July 2025, eight months after launch. Valuation rose to $6.6B in December 2025 and $13.3B in August 2026. The company says Stockholm remains its centre of gravity.

*Storyline opportunities:* hypergrowth infrastructure strain; turning open source into a business; keeping talent in Stockholm.

### Legora (formerly Leya)

Legal AI company founded in 2023 as Leya and renamed in February 2025. Its valuation went from $675M (May 2025) to $1.8B (October 2025), $5.55B (March 2026) and $8.8B (October 2026). Sources disagree on whether its HQ is now New York.

*Storyline opportunities:* selling AI to conservative professionals; a better-funded rival; deciding where headquarters should be.

### Epidemic Sound

Royalty-free music platform for creators, valued at $1.4B in 2021. In 2026 it changed strategy toward a broader creative platform, the parent company is being renamed Epidemic Group, and the CEO changed. HQ: Västgötagatan 2, Södermalm.

*Storyline opportunities:* reinventing music rights; adapting to generative AI.

### Truecaller

Caller ID app founded by two KTH graduates. It listed on Nasdaq Stockholm in October 2021, and most of its users are in India. A 2026 'strategic reset' preceded a return to growth.

*Storyline opportunities:* a spam arms race; a main market far from headquarters; privacy trade-offs.

### Northvolt

Battery company that went bankrupt in March 2025. Lyten bought its main assets and is restarting them. Use it only as a cautionary archetype, handled with care.

*Storyline opportunities:* how much capital deep tech needs; restructuring a fictional hardware startup.

### Epicenter Stockholm

Calls itself Stockholm's first digital 'House of Innovation' (Mäster Samuelsgatan 36). It is a natural early-game base for a founder looking for a first desk and first contacts.

### Norrsken House Stockholm (Norrsken Foundation)

Impact-focused coworking hub in a converted tram depot (Birger Jarlsgatan 57C), opened in early 2017 by the Norrsken Foundation. Useful for missions where a fictional startup has to show social impact.

### KTH Innovation

KTH's free, no-equity innovation support with a pre-incubator at Teknikringen 1. A good fit for 'lab to market' and technical co-founder missions.

### Sting (Stockholm Innovation & Growth)

Stockholm's first startup incubator, founded in 2002 and owned by the Electrum Foundation, with roots in Kista. A natural setting for an accelerator application and demo-day storyline.

### Creandum

Co-led Spotify's 2008 Series A and Lovable's 2025 pre-Series A. Use it as an archetype for a fictional 'seed fund that bets early'. The real firm should not be shown as endorsing the player.

### Northzone

Founded in 1996 in Oslo, with a Stockholm office at Kungsgatan 30. It co-invested in Spotify's 2008 Series A. Use it as an archetype for a board-seat investor.

### EQT Ventures

Multi-stage venture arm of EQT, known for data-driven deal sourcing. Use it as an archetype for an algorithm-scouting investor.

### Kista Science City

ICT cluster north-west of the city, anchored by Ericsson since the 1970s. In May 2026 Ericsson announced plans to move its HQ to Hagastaden from around 2028, which fits a 'district in transition' storyline.

### Ericsson

Ericsson is 150 years old, headquartered in Kista and planning to move to Hagastaden. It is the archetypal enterprise customer with slow, demanding procurement.

## 5. Notable status changes in 2025–2026 (as of 2026-11-23)

- **Skype**: consumer service retired by Microsoft on **5 May 2025**, with users moved to Teams Free.
- **Klarna**: **NYSE IPO on 10 Sept 2025** at $40 per share (KLAR) through UK holding company Klarna Group plc. The shares traded far below the IPO price by mid-2026. Q3 2026: about $1.01B revenue, $65M net loss.
- **Northvolt**: **bankruptcy in Sweden in March 2025**, production stopped in June 2025, assets bought by US company **Lyten**, which is restarting operations.
- **Lovable**: unicorn in July 2025 ($1.8B), then **$6.6B** (Dec 2025), then **$13.3B** (Aug 2026, Series C co-led by the EQT-managed Scaleup Europe Fund).
- **Legora**: $1.8B (Oct 2025), then $5.55B (Mar 2026), then **$8.8B** (Oct 2026). Some reports say its HQ is now in New York.
- **Sana (Labs)**: acquired by **Workday** (completed 4 Nov 2025, about $1.1B announced).
- **Einride**: listed on **Nasdaq (ENRD) on 10 June 2026** via SPAC, at a reduced $1.35B pre-money valuation.
- **Paradox Interactive**: moved from First North to the **Nasdaq Stockholm Main Market** on 9 June 2026.
- **Electronic Arts** (owner of DICE): taken private by a **PIF-led consortium**, about $55B, closed around August 2026.
- **Spotify**: Daniel Ek became executive chairman on **1 Jan 2026**; Gustav Söderström and Alex Norström became co-CEOs.
- **King**: about 10% staff cut (around 200 roles) in **July 2025** as part of Microsoft gaming layoffs.
- **Ericsson**: announced in **May 2026** that its Stockholm operations and HQ will move from **Kista to Hagastaden**, starting around early 2028.
- **Epidemic Sound**: 2026 change of strategy; parent being renamed Epidemic Group AB; co-founder CEO stepped down (interim CEO appointed).
- **Truecaller**: 2026 "strategic reset", with a return to growth reported in Q3 2026.
- **Kry**: first operating profit (2025); Livi brand in the UK and France being merged into Kry.

## 6. Known gaps and items that need verification

- **Mojang Studios (Minecraft)** (partially_verified): Sources give different founding dates (May or June 2009; incorporation in September 2010). The Söder Mälarstrand 43 address was seen only via Wikipedia and aggregator search snippets, not on a Mojang page. A fan wiki names Maria Skolgata 83 as an earlier office (unconfirmed, not recorded). Other co-founders are left out because no source seen named them.
- **Truecaller** (partially_verified): The street address comes from a finance aggregator only, not from Truecaller. Confirm it before using it as more than a district anchor. The valuation at listing is from Seedtable and pre-IPO coverage.
- **Northvolt** (partially_verified): The founding year is reported as 2015 (as SGF Energy, per Wikipedia) or 2016. Some sources add Carl-Erik Lagercrantz and Harald Mix as co-founders. The closing date of the Lyten deal and current production status were not confirmed. Present this entry respectfully: real people lost jobs.
- **Kry (Livi)** (partially_verified): The founding year is 2015 per Kry's own press material and 2014 per one secondary source. Co-founders were not confirmed from the sources seen, so the list is left empty. No HQ street address was found.
- **Trustly** (partially_verified): Founder names were not confirmed in the sources seen. The CEO and chair listed on Wikipedia may be out of date.
- **Paradox Interactive** (partially_verified): The founding year is given as 1999 or 2004, depending on whether the earlier entity is counted. Street addresses conflict (Magnus Ladulåsgatan 4 on Yahoo Finance, Västgötagatan 5 on CB Insights), so only the district is recorded.
- **EA DICE** (partially_verified): Some fan sources give 1988 in Alvesta as the founding date. No Stockholm street address was recorded. The EA take-private appears to have closed in early August 2026 (exact date not confirmed).
- **Tobii** (partially_verified): Danderyd is a municipality north of Stockholm, so district is 'other'. The address comes from an aggregator; Tobii itself says 'Stockholm'.
- **Bambuser** (partially_verified): The First North listing date was not confirmed. Founders were not confirmed.
- **EQT Ventures** (partially_verified): The address comes from an aggregator, and CB Insights gives 2015 as the founding year (Wikipedia says 2016). status.label is 'subsidiary' because it is part of the EQT group; acquired_by names the parent, not an acquisition.
- **Kista Science City** (partially_verified): founded_year = 1986 (Electrum Foundation); one weaker source says 1985. 'Europe's largest ICT cluster' is a common claim but not independently measured here.
- **SSE Business Lab** (partially_verified): The exact building and address of the 'House of Innovation' were not confirmed, so the location is at district precision, assumed to be near the SSE main campus. Company counts differ between pages (250+ vs 350+).
- **SUP46 (Start-Up People of Sweden)** (partially_verified): The Regeringsgatan 65 vs 29 history comes from search snippets; confirm on the Visit Stockholm page before final placement. CB Insights lists Tegelbacken 4A (likely outdated).
- **Antler (Stockholm / Nordics)** (partially_verified): Antler's founding year was not cleanly confirmed (search summaries were ambiguous), so it is left null. Programme length differs between pages (8 or 10 weeks).
- **Nordic Tech Week** (partially_verified): The organiser and first edition year were not confirmed. Kungsträdgården is placed in Norrmalm (district inferred). Attendance figures (around 25,000) come from a source not used here.
- **STHLM Tech Fest / SthlmTech meetup (historical)** (partially_verified): status.label 'defunct' means 'not confirmed active'. Treat it as historical inspiration only. The link between STHLM Tech Week (2019) and Nordic Tech Week was not established.


**Seed-list organisations not included (not sourced well enough in this pass):** Depict (only mentioned as a co-founder's previous employer), Anyfin, Inventure (Helsinki-based), byFounders (Copenhagen-based), Wellstreet, a recurring "Stockholm Tech Meetup" under that name (only the historical SthlmTech/STHLM Tech Fest was found), and iZettle-adjacent founder ventures. A separate trade show, Stockholm Tech Show (Kistamässan, May 2026), was found but left out because it is an IT trade fair, not a founder event.

**Cross-cutting gaps**
- **Street addresses** are missing for several major companies (Tink, Zettle, Lovable, Legora, Voi, Kry, Einride, Trustly, DICE, Bambuser, Almi Invest, Industrifonden, Antler). Each one needs an official source (company contact page or annual report) before getting more than city precision.
- **Aggregator-only addresses** (Truecaller, Tobii, EQT Ventures) need a primary source.
- **Founders** are not confirmed for Kry, Einride, Trustly, Paradox, DICE, Bambuser, Tink (only one co-founder named) and Mojang (only Markus Persson named).
- **Wikipedia rate limiting**: a later pass should re-read the full Wikipedia articles (infoboxes) for Klarna, Skype, Tink, Northvolt, Trustly and DICE to confirm details seen only in search extracts.
- **Valuations and share prices** are left out of summaries where they change daily. Recorded round valuations are point-in-time.

## 7. Full source list

Every URL cited in the JSON, in order of first appearance.

1. Wikipedia: Spotify (REST summary, read 2026-11-23): <https://en.wikipedia.org/wiki/Spotify>
2. Spotify press page (HQ address): <https://www.spotify.com/us/about/press/>
3. Harvard Law School Forum: Spotify direct listing case study: <https://corpgov.law.harvard.edu/2018/07/05/spotify-case-study-structuring-and-executing-a-direct-listing/>
4. Fortune: Spotify direct listing (2018-04-03): <https://fortune.com/2018/04/03/spotify-stock-market-cap-ipo-direct-listing/>
5. NPR: Daniel Ek to step aside as CEO (2025-09-30): <https://www.npr.org/2025/09/30/nx-s1-5558012/spotifys-daniel-ek-announces-that-hell-step-aside-as-ceo.Retrieved>
6. Music Week: co-CEOs named: <https://www.musicweek.com/public_html/index.php/digital/read/daniel-ek-to-become-spotify-executive-chairman-gustav-s-derstr-m-alex-norstr-m-upped-to-co-ceos/092746>
7. Klarna: pricing of IPO (press release): <https://www.klarna.com/international/press/klarna-announces-pricing-of-its-initial-public-offering/>
8. Fortune: Klarna jumps in NYSE debut (2025-09-11): <https://fortune.com/2025/09/11/swedish-bnpl-giant-klarna-biggest-ipo-2025-nyse/>
9. SEC: Klarna Group plc 424B4 prospectus: <https://www.sec.gov/Archives/edgar/data/0002003292/000200329225000052/klarnagroupplc424b4.htm>
10. CNBC: Klarna sets up UK holding company (2023-11-06): <https://www.cnbc.com/2023/11/06/klarna-sets-up-uk-holding-company-in-move-toward-ipo.html/>
11. Klarna contact page (head office address): <https://www.klarna.com/se/en/about-us/contact/>
12. Wikipedia: Klarna: <https://en.wikipedia.org/wiki/Klarna>
13. The Next Web: Klarna Q3 2026 results: <https://thenextweb.com/news/klarna-q3-2026-results-revenue-1bn-us-fair-financing>
14. Investing.com: KLAR quote (price context, Aug 2026): <https://www.investing.com/equities/klarna>
15. Wikipedia: King (company) (REST summary, read 2026-11-23): <https://en.wikipedia.org/wiki/King_(company)>
16. TechCrunch: Activision Blizzard closes $5.9B acquisition of King (2016-02-23): <https://techcrunch.com/2016/02/23/activision-blizzard-closes-its-5-9b-acquisition-of-king-makers-of-candy-crush/>
17. Microsoft blog: welcoming Activision Blizzard King (2023-10-13): <https://blogs.microsoft.com/blog/2023/10/13/welcoming-the-legendary-teams-at-activision-blizzard-king-to-team-xbox/>
18. Dezeen: King's Stockholm offices (2015): <https://www.dezeen.com/2015/03/24/candy-crush-offices-interior-designed-kingdom-adolfsson-partners-stockholm-sweden/amp/>
19. PocketGamer.biz: King loses 10% of staff: <https://www.pocketgamer.biz/king-loses-10-of-staff-as-microsoft-makes-games-division-cuts>
20. Fortune: Activision buys King (2015-11-03): <https://fortune.com/2015/11/03/activision-king-digital/>
21. Wikipedia: Mojang Studios (REST summary, read 2026-11-23): <https://en.wikipedia.org/wiki/Mojang_Studios>
22. Microsoft News: Minecraft to join Microsoft (2014-09-15): <https://news.microsoft.com/2014/09/15/minecraft-to-join-microsoft/>
23. Engadget: Microsoft completes acquisition of Minecraft studio (2014-11-06): <https://www.engadget.com/2014/11/06/microsoft-completes-acquisition-of-minecraft-studio/>
24. Wikipedia: Skype: <https://en.wikipedia.org/wiki/Skype>
25. Microsoft News: Microsoft officially welcomes Skype (2011-10-13): <https://news.microsoft.com/2011/10/13/microsoft-officially-welcomes-skype>
26. TechCrunch: Skype to shut down May 5, 2025: <https://techcrunch.com/2025/02/28/microsoft-hangs-up-on-skype-service-to-shut-down-may-5-2025>
27. Tom's Hardware: Microsoft retires Skype: <https://www.tomshardware.com/software/video-conferencing/microsoft-finally-retires-skype-after-22-years-of-service>
28. ERR News: Skype's legacy (Estonia): <https://news.err.ee/1609621340/skype-s-legacy-much-more-than-just-free-internet-and-video-calls>
29. Wikipedia: Zettle (REST summary, read 2026-11-23): <https://en.wikipedia.org/wiki/Zettle>
30. PayPal newsroom: PayPal completes acquisition of iZettle (2018-09-20): <https://newsroom.paypal-corp.com/2018-09-20-PayPal-Completes-Acquisition-of-iZettle>
31. Zettle: iZettle is now Zettle by PayPal: <https://www.zettle.com/gb/about-us/izettle-now-zettle-by-paypal>
32. TechCrunch: PayPal buying iZettle for $2.2B (2018-05-17): <https://techcrunch.com/2018/05/17/paypal-confirms-that-it-is-buying-payments-startup-izettle-for-2-2b-in-an-all-cash-deal>
33. Visa IR: Visa completes acquisition of Tink (2022-03-10): <https://investor.visa.com/news/news-details/2022/Visa-Completes-Acquisition-of-Tink/default.aspx>
34. Visa FY2022 10-K (SEC): <https://www.sec.gov/Archives/edgar/data/1403161/000140316122000081/v-20220930.htm>
35. tech.eu: Visa buys Tink for €1.8B (2021-06-24): <https://tech.eu/2021/06/24/visa-charges-ahead-swipes-up-open-banking-platform-tink-for-e1-8-billion/>
36. TechCrunch: Lovable becomes a unicorn (2025-07-17): <https://techcrunch.com/2025/07/17/lovable-becomes-a-unicorn-with-200m-series-a-just-8-months-after-launch>
37. TechCrunch: Lovable $16M pre-Series A (2025-02-25): <https://techcrunch.com/2025/02/25/swedens-lovable-an-app-building-ai-platform-rakes-in-16m-after-spectacular-growth>
38. TechCrunch: Lovable raises $330M at $6.6B (2025-12-18): <https://techcrunch.com/2025/12/18/vibe-coding-startup-lovable-raises-330m-at-a-6-6b-valuation/>
39. Lovable blog: Series C: <https://lovable.dev/blog/series-c>
40. tech.eu: Lovable valuation doubles to $13.3B (2026-08-12): <https://tech.eu/2026/08/12/lovables-valuation-doubles-to-13bn-as-raises-400m/>
41. Antler press release: Lovable Series C: <https://www.antler.co/press-releases/antler-portfolio-company-lovable-raises-400m-series-c-at-13-3b-valuation>
42. Wikipedia: Anton Osika: <https://en.wikipedia.org/wiki/Anton_Osika>
43. Forbes Australia: Lovable founding story: <https://forbes.com.au/news/entrepreneurs/vibe-coding-turned-this-swedish-ai-unicorn-into-the-fastest-growing-software-startup-ever/>
44. Legora blog: $150M Series C: <https://legora.com/blog/series-c>
45. Business Wire: Legora raises $150M Series C (2025-10-30): <https://www.businesswire.com/news/home/20251030974157/en/Legora-Raises-$150-Million-Series-C-to-Accelerate-Global-Rollout-of-Its-AI-Platform-for-Legal-Professionals>
46. tech.eu: Legora $150M Series C: <https://tech.eu/2025/10/30/swedish-legaltech-legora-raises-150m-series-c/>
47. TechCrunch: Legora reaches $5.55B (2026-03-10): <https://techcrunch.com/2026/03/10/legora-reaches-5-55-billion-valuation-as-ai-legaltech-boom-endures/>
48. Legora blog: $550M Series E: <https://legora.com/blog/series-e>
49. Artificial Lawyer: Leya rebrands to Legora (2025-02-19): <https://www.artificiallawyer.com/2025/02/19/legal-genai-pioneer-leya-rebrands-to-legora/>
50. Contrary Research: Legora: <https://research.contrary.com/report/legora>
51. Y Combinator: Legora: <https://www.ycombinator.com/companies/legora>
52. Epidemic Sound: $450M round at $1.4B (2021): <https://corporate.epidemicsound.com/press-and-media/press-releases/2021/epidemic-sound-the-company-soundtracking-the-internet-closes-a-450million-round-at-a-1-4billion-valuation/>
53. Epidemic Sound: About (legal entity and address): <https://epidemicsound.com/about>
54. Epidemic Sound careers: founders: <https://careers.epidemicsound.com/pages/what-we-do>
55. Epidemic Sound: Höglund steps down as CEO (2026): <https://corporate.epidemicsound.com/press-and-media/press-releases/2026/co-founder-oscar-hoglund-steps-down-as-ceo-and-takes-position-on-the-board-cfo-sara-borsvik-appointed-interim-ceo/>
56. Epidemic Group: 2025 annual report (2026): <https://corporate.epidemicsound.com/press-and-media/press-releases/2026/epidemic-group-publishes-2025-annual-and-sustainability-report-a-transformative-year-investing-significantly-into-ai-and-bringing-the-company-back-to-profitable-growth-in-2026/>
57. Wikipedia: Epidemic Sound: <https://en.wikipedia.org/wiki/Epidemic_Sound>
58. Cision: Truecaller IPO priced at SEK 52: <https://news.cision.com/truecaller-ab/r/the-offering-price-for-truecaller-s-initial-public-offering-has-been-set-at-sek-52-per-class-b-share,c3429160>
59. Seedtable: Truecaller listing: <https://seedtable.com/exits/truecaller>
60. KTH: KTH duo behind fast-growing mobile app: <https://www.kth.se/en/aktuellt/nyheter/kth-duo-behind-fast-growing-mobile-app-1.437091>
61. Wikipedia: Truecaller: <https://en.wikipedia.org/wiki/Truecaller>
62. MFN: Truecaller Q3 2026 report: <https://mfn.se/cis/a/truecaller/truecaller-ab-return-to-growth-following-a-successful-strategic-reset-495674ad>
63. Yahoo Finance: Truecaller profile (address): <https://uk.finance.yahoo.com/quote/0AA7.L/profile>
64. Wikipedia: Northvolt: <https://en.wikipedia.org/wiki/Northvolt>
65. Northvolt: Lyten to acquire remaining assets in Sweden and Germany: <https://northvolt.com/articles/lyten-to-acquire-all-remaining-northvolt-assets-in-sweden-and-germany/>
66. Electrek: Lyten takes over Northvolt (2025-08-07): <https://electrek.co/2025/08/07/lyten-just-took-over-5b-of-northvolt-battery-empire/>
67. Energy-Storage.news: Lyten deal and creditors: <https://www.energy-storage.news/a-win-for-transatlantic-relations-but-a-big-loss-for-creditors-lytens-northvolt-deal/>
68. Fortune: Northvolt battery factory (2017): <https://fortune.com/2017/03/07/northvolt-battery-factory-sweden-carlsson/>
69. TechCrunch: Voi reports first profitable year (2025-01-28): <https://techcrunch.com/2025/01/28/shared-scooter-startup-voi-reports-its-first-profitable-year-as-it-explores-an-ipo>
70. tech.eu: Voi $115M Series D at $1B (2021-12-21): <https://tech.eu/2021/12/21/voi-keeps-a-rollin-along-brings-home-115-million-in-series-d-round/>
71. Zag Daily: Voi 'no concrete plans' for IPO: <https://zagdaily.com/micromobility/voi-reveals-no-concrete-plans-for-ipo-after-strong-q2-results/>
72. MFN: Voi full-year report 2025: <https://mfn.se/all/a/voitechnology/voi-technology-ab-publ-publishes-fourth-quarter-and-full-year-report-2025>
73. Seedtable: Voi (founders): <https://seedtable.com/companies/voi>
74. Kry press: Kry drives growth in 2024: <https://www.kry.se/press/nyheter/kry-drives-growth-in-2024-with-its-best-results-to-date/>
75. Livi: Livi becomes Kry in the UK and France: <https://uk-partners.livi.co.uk/news/livi-becomes-kry-in-the-uk-and-france/>
76. MobiHealthNews: Kry merges with Helsa: <https://www.mobihealthnews.com/news/emea/kry-announces-merger-swedish-healthcare-company-helsa>
77. Index Ventures: Kry seed round: <https://www.indexventures.com/news-room/news/kry-the-swedish-video-based-healthcare-provider-raises-%E2%82%AC61-million-in-seed-round-led>
78. TechCrunch: Einride plans SPAC (2025-11-12): <https://techcrunch.com/2025/11/12/self-driving-trucks-startup-einride-plans-to-go-public-via-a-spac>
79. TechCrunch: Einride $113M PIPE (2026-02-26): <https://techcrunch.com/2026/02/26/self-driving-truck-startup-einride-raises-113m-pipe-ahead-of-public-debut/>
80. Trucking Dive: Einride becomes publicly traded: <https://www.truckingdive.com/news/einride-becomes-publicly-traded-company/822734/>
81. Finviz/PR: Einride commences trading on Nasdaq (ENRD, ENRDW): <https://finviz.com/news/360906/einride-a-global-leader-in-autonomous-and-electric-freight-commences-trading-on-nasdaq-under-tickers-enrd-and-enrdw>
82. The Next Web: Einride lists at $1.35B: <https://thenextweb.com/news/einride-nasdaq-spac-driverless-trucking-valuation-drop>
83. Wikipedia: Trustly: <https://en.wikipedia.org/wiki/Trustly>
84. Nordic Capital: acquires Trustly (2018): <https://www.nordiccapital.com/insights/press-releases/nordic-capital-acquires-trustly-the-leading-next-generation-direct-payment-provider/>
85. Finextra: Nordic Capital buys majority stake: <https://finextra.com/newsarticle/31812/nordic-capital-buys-majority-stake-in-online-payments-firm-trustly>
86. Placera: Trustly equity commitments (2026-10-02): <https://www.placera.se/pressmeddelanden/trustly-001-trustly-ab-publ-receives-signed-equity-commitment-letters-of-more-than-usd-40m-from-nordic-capital-and-alfvn-didrikson-to-accelerate-its-ai-powered-growth-strategy-20261002>
87. Workday: completes acquisition of Sana (2025-11-04): <https://newsroom.workday.com/2025-11-04-Workday-Completes-Acquisition-of-Sana>
88. tech.eu: Workday to acquire Sana for $1.1B: <https://tech.eu/2025/09/16/workday-to-acquire-sana-for-11-billion/>
89. Seedtable: Sana exit: <https://seedtable.com/exits/sana>
90. Paradox Interactive: our company: <https://www.paradoxinteractive.com/our-company>
91. Paradox Interactive: prospectuses (main market listing): <https://www.paradoxinteractive.com/investors/prospectuses>
92. Wikiwand/Wikipedia: Paradox Interactive: <https://www.wikiwand.com/en/Paradox_Interactive>
93. Wikipedia: DICE (company): <https://en.wikipedia.org/wiki/DICE_(company)>
94. The National: PIF completes $55bn Electronic Arts takeover (2026-08-05): <https://www.thenationalnews.com/future/technology/2026/08/05/saudi-pif-completes-55bn-electronic-arts-takeover/>
95. Saudi Gazette: PIF-led consortium completes EA acquisition: <https://saudigazette.com.sa/article/663546>
96. Tobii: history of Tobii: <https://corporate.tobii.com/about-us/history-of-tobii>
97. Wikipedia: Tobii: <https://en.wikipedia.org/wiki/Tobii>
98. Yahoo Finance: Tobii profile (address): <https://au.finance.yahoo.com/quote/0R6W.IL/profile>
99. Bambuser: about us: <https://bambuser.com/about-us>
100. MFN: Bambuser rights issue outcome: <https://mfn.se/all/a/bambuser/bambuser-ab-announces-final-outcome-of-the-companys-rights-issue>
101. Placera: Bambuser press release (2026-09-24): <https://www.placera.se/pressmeddelanden/bambuser-bambuser-invites-live-shopping-hosts-to-join-its-global-community-20260924>
102. Ericsson: Sweden (HQ address): <https://www.ericsson.com/en/about-us/company-facts/ericsson-worldwide/sweden>
103. Ericsson: to relocate Stockholm operations to Hagastaden (May 2026): <https://www.ericsson.com/en/press-releases/2026/5/ericsson-to-relocate-stockholm-operations-to-hagastaden>
104. Ericsson history: 1876 workshop: <https://www.ericsson.com/en/about-us/history/company/timeline-placeholder/timeline-1876-lars-magnus-ericsson-starts-a-mechanical-workshop>
105. Ericsson: plans to move HQ to Kista (2002): <https://www.ericsson.com/en/press-releases/2002/12/ericsson-plans-to-move-headquarters-to-kista>
106. Nordregio: Kista and Ericsson history: <https://archive.nordregio.org/Metameny/About-Nordregio/Journal-of-Nordregio/2009/Journal-of-Nordregio-no-2-2009/Kista-wants-entrepreneurial-ICT-student/index.html>
107. Wikipedia: Ericsson (REST summary): <https://en.wikipedia.org/wiki/Ericsson>
108. Epicenter: about: <https://weareepicenter.com/stockholm/about-epicenter>
109. Visit Stockholm: Epicenter (address): <https://www.visitstockholm.com/o/epicenter>
110. Vice: inside Epicenter Stockholm: <https://creators.vice.com/en_us/article/inside-epicenter-stockholm-innovation-hub>
111. Wikipedia: Norrsken Foundation: <https://en.wikipedia.org/wiki/Norrsken_Foundation>
112. The Local: Klarna founder unveils social entrepreneurship hub (2016-09-05): <https://www.thelocal.se/20160905/klarna-founder-unveils-huge-social-entrepreneurship-hub>
113. Norrsken: Stockholm house: <https://www.norrsken.org/houses/stockholm>
114. Thatsup: Norrsken House (address): <https://thatsup.co.uk/stockholm/conference-room/norrsken-house/>
115. Allabolag: Stiftelsen Norrsken Foundation: <https://www.allabolag.se/8024795448/stiftelsen-norrsken-foundation>
116. KTH Innovation: find us: <https://www.kth.se/om/innovation/om/hitta-till-kth-innovation-1.979474>
117. KTH Innovation: about: <https://kth.se/en/om/innovation/om>
118. KTH Innovation: pre-incubator: <https://www.kth.se/en/innovation/forinkubator>
119. KTH Innovation alumni (startups from KTH): <https://www.kth.se/en/om/innovation/alumner>
120. Wikipedia: KTH Royal Institute of Technology (REST summary): <https://en.wikipedia.org/wiki/KTH_Royal_Institute_of_Technology>
121. KTH: history: <https://www.kth.se/en/om/fakta/historik>
122. KTH: Sweden's largest technical university: <https://www.kth.se/en/om/fakta/sveriges-storsta-tekniska-universitet-1.3487>
123. KTH: Kista campus: <https://www.kth.se/en/om/kontakt/campus/kth-kista-1.640358>
124. Sting: about: <https://sting.co/about>
125. Visit Stockholm: Sting (address): <https://www.visitstockholm.com/o/sting>
126. SISP: Sting (Kista address): <https://www.sisp.se/members/sting>
127. City AM: Pär Hedberg, founder of Sting: <https://www.cityam.com/sting-founder-par-hedberg-sweden-tech-startups/>
128. Interreg Europe: Sting good practice: <https://interregeurope.eu/good-practices/sting-stockholm-innovation-growth>
129. Creandum: contact: <https://creandum.com/contact>
130. Creandum: Spotify commitment: <https://creandum.com/commitments/spotify>
131. Creandum: 20 years of Creandum: <https://creandum.com/stories/20-years-of-creandum>
132. Creandum: Lovable commitment: <https://creandum.com/commitments/lovable>
133. Bloomberg: early Spotify investor raises $300M (2019): <https://www.bloomberg.com/news/articles/2019-06-24/early-spotify-investor-raises-300-million-for-early-stage-deals>
134. Wikipedia: EQT Ventures: <https://en.wikipedia.org/wiki/EQT_Ventures>
135. EQT: EQT Ventures secures EUR 566M (2016): <https://eqtgroup.com/news/2016/eqt-ventures-secures-commitments-totaling-eur-566-million>
136. EQT: EQT Ventures III closes (2022): <https://eqtgroup.com/news/2022/eqt-ventures-iii-closes-europe-s-largest-venture-capital-fund-committed-to-early-stage-tech-startups>
137. CB Insights: EQT Ventures (address): <https://www.cbinsights.com/investor/eqt-ventures>
138. Northzone: offices: <https://northzone.com/offices>
139. Northzone: Spotify, the impossible success story: <https://northzone.com/insights/spotify-impossible-success-story>
140. Bloomberg: Northzone raises $500M (2019): <https://www.bloomberg.com/news/articles/2019-11-18/spotify-backer-northzone-raises-500-million-for-new-investments>
141. Fortune: Spotify investor Pär-Jörgen Pärson (2018): <https://fortune.com/2018/03/21/spotify-investor-par-jorgen-parson>
142. Wikipedia: Kista: <https://en.wikipedia.org/wiki/Kista>
143. SISP: Kista Science City: <https://www.sisp.se/members/kista-science-city>
144. SSE: history, year by year: <https://www.hhs.se/en/about-us/history/year-by-year/>
145. SSE: timeline PDF: <https://www.hhs.se/contentassets/1500c23426e5479ca98c466498fb61ae/tidslinje.pdf>
146. SSE Business Lab: <https://www.hhs.se/en/outreach/sse-initiatives/sse-business-lab/>
147. SSE Business Lab: Incubate programme: <https://www.hhs.se/en/outreach/sse-initiatives/sse-business-lab/programs/incubate/>
148. Mynewsdesk: SUP46 officially opened: <https://www.mynewsdesk.com/se/sup46-ab-start-up-people-of-sweden/pressreleases/stockholm-s-new-startup-space-sup46-start-up-people-of-sweden-officially-opened-by-daniel-ek-913397>
149. Visit Stockholm: SUP46: <https://www.visitstockholm.com/o/sup46>
150. Realtid: SUP46 new membership (2026): <https://www.realtid.se/bors-finans/sup46-lanserar-nytt-medlemskap-tar-in-yngre-startups/>
151. KTH/GIDEC: SUP46 presentation (2017): <https://gidec.abe.kth.se/InnoCENS/2017_06_kth/Lana.%20SUP46%20presentation.pdf>
152. Almi Invest: <https://www.almi.se/en/almi-invest/>
153. Almi: about Almi Invest and our mission: <https://www.almi.se/en/venture-capital/is-almi-invest-right-for-your-company/frequently-asked-questions-about-venture-capital/about-almi-invest-and-our-mission/>
154. OECD: benchmarking government support for VC (Sweden): <https://www.oecd.org/en/publications/benchmarking-government-support-for-venture-capital_82cd3fe1-en/sweden_d31bbe06-en.html>
155. Industrifonden: <https://industrifonden.com/>
156. Wikipedia: Industrifonden: <https://en.wikipedia.org/wiki/Industrifonden>
157. Antler: Nordics: <https://www.antler.co/nordics>
158. Antler: Sweden: <https://www.antler.co/sweden>
159. Visit Stockholm: Nordic Tech Week 2026: <https://www.visitstockholm.com/events/nordic-tech-week-2026/next/>
160. KTH: KTH Innovation Collide at Nordic Tech Week: <https://www.kth.se/en/student/kalender/kth-innovation-collide-nordic-tech-week-1.1487522>
161. Luma: Startup Day (Nordic Tech Week 2026): <https://luma.com/x37k41qv>
162. The Local: Stockholm Tech Fest live blog (2014): <https://www.thelocal.se/20140905/live-blog-stockholm-tech-fest>
163. Brunswick: STHLM Tech Fest 2019: <https://www.brunswickgroup.com/sthlm-tech-fest-2019-i11361/>
164. Nordic Startup News: 3000 Tech Fest attendees: <https://nordicstartupnews.com/3000-tech-fest-attendees-celebrated-stockholm/>


---
Map data attribution for future geocoded coordinates: **© OpenStreetMap contributors** (ODbL).
