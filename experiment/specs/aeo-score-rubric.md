# AEO/GEO on-site score — rubric (v0)

Synthesized 2026-08-03 by the ora.ai research lab from its AEO/GEO literature compilations; the
rubric behind the scoring used in this study.

The on-site component of the AEO score splits into two sub-scores.

## Sub-score A: Citability gates

*Can answer engines ingest this site at all? These are the only on-site properties with converging discoverability-stage evidence.*

| Check | Evidence | Detection |
|---|---|---|
| robots.txt allows retrieval bots: `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Googlebot`, `bingbot` (blanket `*` disallow = fail) | Official docs, all five engines | Parse `/robots.txt` |
| Training-bot stance (`GPTBot`, `ClaudeBot`, `Google-Extended`) — recorded as intent signal, **not scored** (doesn't gate answer visibility) | OpenAI/Anthropic/Google docs: search and training are independent controls | Parse `/robots.txt` |
| Not WAF/CDN-blocked for AI user agents | OpenAI + Perplexity official ("allow our published IPs") | Fetch with bot UA strings vs normal UA; compare status/content |
| No `noindex`/`nosnippet`/`data-nosnippet`/`max-snippet` (Google AI Overviews gate) | Google official | Meta tags + X-Robots-Tag headers |
| No `NOCACHE`/`NOARCHIVE` (Copilot citation gate) | Microsoft official (Sept 2023 controls) | Meta tags + headers |
| Content present without JavaScript (raw-HTML text ÷ rendered-DOM text ratio) | Vercel/MERJ 500M+ fetches: GPTBot/ClaudeBot/PerplexityBot execute **zero** JS; searchVIU live-fetch probe concurs | Raw fetch vs headless-render text diff |
| Crawl hygiene: HTTPS, sitemap.xml (+`lastmod`), 200s on key pages, TTFB < ~3s | Mechanistic; AI fetchers time out ~1–5s; 34% of their fetches hit 404s | Direct crawl |

## Sub-score B: Optimization level (four pillars, graded)

### B1. Machine-parseable construction (Lighthouse-anchored)
- Lighthouse SEO audits: `document-title`, `meta-description`, `is-crawlable`, `robots-txt` validity, `crawlable-anchors`, `canonical`, `hreflang`, `image-alt`, `http-status-code`
- Lighthouse Best Practices: `doctype`, `charset`, HTTPS, no browser errors
- Semantic HTML ratio (`main`/`article`/`section`/`table` vs div-soup) — Google's one named technical item
- Heading hierarchy: single H1, no level skips
- Human-readable URL slugs (Ahrefs 1.4M-prompt study: 89.8% vs 81.1% citation rate among retrieved)

### B2. Answer-shaped content
- Answer-first blocks under headings (highest industry consensus, 7+ sources; needs small LLM judge)
- Question-format H2/H3 headings
- FAQ sections (+0.07 std effect, Discovered Labs)
- List/table density
- Chunkable paragraphs; word-count bands (~250–2,000 words over-index in citations, Seer 8,500-keyword study)
- Readability (Flesch)

### B3. Evidence density (GEO-paper tactics — weight modestly)
- Statistics density (numerals/percentages per 1,000 words)
- Attributed quotations
- Outbound citations to authoritative sources
- Evidence: Princeton GEO +22–41% *conditional on retrieval*; C-SEO Bench (NeurIPS 2025) negative replication (3/54 positive); effects are zero-sum redistributions

### B4. Freshness & entity metadata
- Visible dates + `dateModified` schema + sitemap `lastmod` agreement
- Update recency (AI-cited content 25.7% fresher, Ahrefs 17M citations; ~10-month citation window)
- schema.org JSON-LD presence/types, Organization + `sameAs` — **low weight** (adoption signal: Ahrefs DiD shows null direct effect; no engine parses JSON-LD at live retrieval; Bing says schema feeds LLMs at indexing)
- Bylines/about/contact — recorded, near-zero weight (Seer: author bios *inversely* correlate)

## Explicitly excluded (with receipts)

| Excluded | Why |
|---|---|
| llms.txt | In Ora's AX check catalog → axis contamination. Also: 97% of files get zero bot requests (Ahrefs 137K-domain study); Google officially ignores it |
| Core Web Vitals / Lighthouse perf score | No citation effect after controls (Discovered Labs); only hard timeouts matter |
| Keyword optimization / stuffing | Negative (~−10%, GEO paper); Google spam policies |
| IndexNow | Secret-key filename — not third-party detectable |
| Bing/Google index status, Search Console toggles, publisher programs | Private consoles/partnerships — not crawl-detectable |
| Title↔prompt semantic similarity | Strong signal (Ahrefs cosine 0.602 vs 0.484) but requires a query set → deferred to spec discussion; risks coupling to outcome queries |

## Scoring framing

Primary tag = **consensus-weighted adoption** of industry-recommended practices (not evidence-weighted efficacy) — the experiment itself tests efficacy. The two AEO proxies published per domain (`discovery`, `citation_breadth` in `data/domains.csv`) derive from this framing.

## Scanner shape

Fetch homepage + 2–3 key pages (pricing/docs/product — where AI referrals concentrate, per Ahrefs). Stack: fetch + cheerio + headless Chrome (Lighthouse CLI + render-diff) + one small LLM judge for answer-first quality. Cacheable one-time pass per domain.
