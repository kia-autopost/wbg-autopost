"""
WBG Content Generator - v4
Content types:
- sd_hidden_gem: surprising neighborhood facts
- current_event_tie: local events tied to real estate
- hot_take: bold opinions
- hyper_local_intel: insider market intel
- sd_lifestyle_hook: lifestyle moments
- market_data: REAL web-searched SD neighborhood market stats
- home_tour: AI-generated fictional luxury property showcase
"""
import os, random, json, re, logging
import anthropic
log = logging.getLogger('WBG')

# Weighted content type pool:
# home_tour:   1/27 = ~3.7% (~1 per week with 2 posts/day)
# market_data: 3/27 = ~11% (~1-2 per week)
# lifestyle/neighborhood: ~85%
CONTENT_TYPES = [
    'sd_hidden_gem',
    'sd_hidden_gem',
    'sd_hidden_gem',
    'sd_hidden_gem',
    'sd_hidden_gem',
    'current_event_tie',
    'current_event_tie',
    'current_event_tie',
    'current_event_tie',
    'current_event_tie',
    'hot_take',
    'hot_take',
    'hot_take',
    'hot_take',
    'hot_take',
    'hyper_local_intel',
    'hyper_local_intel',
    'hyper_local_intel',
    'hyper_local_intel',
    'hyper_local_intel',
    'sd_lifestyle_hook',
    'sd_lifestyle_hook',
    'sd_lifestyle_hook',
    'sd_lifestyle_hook',
    'market_data',
    'market_data',
    'market_data',
    'home_tour',
]

SD_NEIGHBORHOODS = [
    'La Jolla', 'Del Mar', 'Coronado', 'Carmel Valley', 'Rancho Santa Fe',
    'Pacific Beach', 'Mission Hills', 'North Park', 'Encinitas', 'Carlsbad',
    'Chula Vista', 'Point Loma', 'Hillcrest', 'Ocean Beach', 'Solana Beach',
    'Escondido', 'Santee', 'El Cajon', 'Poway', 'Scripps Ranch',
    'Little Italy', 'Barrio Logan', 'Golden Hill', 'South Park', 'Kensington',
    'Bird Rock', 'Windansea', 'Bankers Hill', 'Mission Valley', 'Clairemont',
]

SD_EVENTS_AND_FACTS = [
    'San Diego has 70 miles of coastline',
    'SD is the oldest city in California',
    'Comic-Con draws 130,000+ visitors annually to the Gaslamp Quarter',
    'SD has more craft breweries per capita than almost any US city',
    'The average San Diego temperature is 70 degrees year-round',
    'Balboa Park is larger than Central Park in NYC',
    'SD ranks consistently in the top 5 most desirable cities to live in the US',
    'La Jolla Cove is home to a protected colony of sea lions',
    'The Del Mar racetrack season brings thousands of visitors each summer',
    'SD has the second largest naval fleet in the world',
    'Torrey Pines State Reserve has the rarest pine tree in North America',
    'Coronado Island is actually a peninsula connected by a narrow strip of land',
    'SD has over 300 days of sunshine per year',
    'North Park was named one of the coolest neighborhoods in America',
    'Little Italy in SD is one of the most walkable neighborhoods on the West Coast',
]

# Price tiers for home tours - mix of aspirational and approachable
HOME_TOUR_CONFIGS = [
    # Aspirational luxury
    {'tier': 'luxury',      'price_range': ('$2.8M', '$8.5M'), 'neighborhoods': ['La Jolla', 'Rancho Santa Fe', 'Coronado', 'Del Mar', 'Bird Rock']},
    # Upper mid
    {'tier': 'upper_mid',   'price_range': ('$1.4M', '$2.7M'), 'neighborhoods': ['Carmel Valley', 'Encinitas', 'Solana Beach', 'Mission Hills', 'Pacific Beach']},
    # Approachable
    {'tier': 'approachable','price_range': ('$750K', '$1.3M'),  'neighborhoods': ['North Park', 'South Park', 'Kensington', 'Hillcrest', 'Ocean Beach', 'Poway']},
]

SYSTEM_PROMPT = """You are writing social media content for Whitney Pierce, a San Diego real estate expert with Whissel Beer Group at eXp Realty.

Whitney's voice is:
- Warm, confident, and genuinely passionate about San Diego
- Knowledgeable but never stuffy — she makes real estate feel exciting and accessible
- First-person, conversational — like a text from a knowledgeable friend
- Specific and local — she knows the neighborhoods intimately

CRITICAL RULES:
- The "stat" field must be SHORT — a number, year, or brief phrase under 20 characters (e.g. "1907", "300 days", "$1.2M", "2.2 miles"). NEVER a full sentence.
- ALL content must be specifically about the neighborhood named in the prompt.
- Never use generic real estate language. No "dream home" or "motivated seller."
- Be specific, be human, be Whitney.
- Always return ONLY valid JSON, no markdown, no preamble."""


def _search_market_data(neighborhood, api_key):
    """Use Claude with web search to get real current market data for a neighborhood."""
    client = anthropic.Anthropic(api_key=api_key)
    
    search_prompt = f"""Search for current real estate market data for {neighborhood}, San Diego, CA.
Find: median home price, average days on market, year-over-year price change, and inventory level.
Use Redfin, Zillow, or Realtor.com data. Return ONLY valid JSON with these exact fields:
{{
  "median_price": "e.g. $1.2M or $875K",
  "days_on_market": "e.g. 12 days",
  "price_change_yoy": "e.g. +8.2% or -3.1%",
  "inventory": "e.g. 45 homes or low/high",
  "market_temp": "hot/warm/cool/cold",
  "key_insight": "one sentence about what makes this market unique right now"
}}
If you cannot find specific {neighborhood} data, use San Diego County data and note it."""

    msg = client.messages.create(
        model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
        max_tokens=500,
        messages=[{'role': 'user', 'content': search_prompt}],
        tools=[{'type': 'web_search_20250305', 'name': 'web_search'}]
    )
    
    # Extract text from response
    full_text = ' '.join([b.text for b in msg.content if hasattr(b, 'text') and b.text])
    s, e = full_text.find('{'), full_text.rfind('}')
    if s >= 0 and e > s:
        return json.loads(full_text[s:e+1])
    return None


def generate_post(content_type: str = None, api_key: str = None) -> dict:
    if api_key is None:
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if content_type is None:
        content_type = random.choice(CONTENT_TYPES)

    neighborhood = random.choice(SD_NEIGHBORHOODS)
    sd_fact      = random.choice(SD_EVENTS_AND_FACTS)
    client       = anthropic.Anthropic(api_key=api_key)

    # ── MARKET DATA ──────────────────────────────────────────────────────────
    if content_type == 'market_data':
        # Get real market data via web search
        market = _search_market_data(neighborhood, api_key)
        
        if not market:
            # Fallback: use Claude's knowledge to estimate market data
            log.warning(f'Web search failed for {neighborhood}, using AI estimate')
            fallback_msg = client.messages.create(
                model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
                max_tokens=300,
                messages=[{'role': 'user', 'content': f'Based on your knowledge of San Diego real estate, provide estimated current market data for {neighborhood}. Return ONLY valid JSON with these fields: median_price (e.g. "$1.2M"), days_on_market (e.g. "14 days"), price_change_yoy (e.g. "+5.2%"), inventory (e.g. "low"), market_temp (hot/warm/cool/cold), key_insight (one sentence about this market).'}]
            )
            raw = fallback_msg.content[0].text.strip()
            s, e = raw.find('{'), raw.rfind('}')
            try:
                market = json.loads(raw[s:e+1])
            except:
                market = {
                    'median_price': 'See caption',
                    'days_on_market': '~14 days',
                    'price_change_yoy': '+4-8%',
                    'inventory': 'low',
                    'market_temp': 'warm',
                    'key_insight': f'{neighborhood} continues to be a sought-after San Diego market.'
                }

        prompt = f"""Whitney Pierce is sharing real market data for {neighborhood}, San Diego.
Here is the current market data: {json.dumps(market)}

Write a post in Whitney's voice interpreting this data for buyers and sellers.
Make it feel like insider knowledge, not a press release.

Return ONLY valid JSON:
{{
  "content_type": "market_data",
  "neighborhood": "{neighborhood}",
  "headline": "punchy market headline for {neighborhood} (max 8 words)",
  "median_price": "{market.get('median_price', 'N/A')}",
  "days_on_market": "{market.get('days_on_market', 'N/A')}",
  "price_change_yoy": "{market.get('price_change_yoy', 'N/A')}",
  "inventory": "{market.get('inventory', 'N/A')}",
  "market_temp": "{market.get('market_temp', 'active')}",
  "stat": "the single most impressive stat under 20 chars (e.g. '$1.2M median' or '9 days DOM')",
  "insight": "Whitney's 1-2 sentence take on what this data means for real buyers/sellers in {neighborhood}",
  "caption": "3-4 sentences from Whitney interpreting the {neighborhood} market right now. Specific, actionable, no fluff. End with a question or call to action.",
  "hashtags": "#WhisselBeerGroup #SanDiego #{neighborhood.replace(' ','')} #SanDiegoRealEstate #MarketUpdate #SDMarket #ExpRealty #WhitneyPierceWBG"
}}"""

        msg = client.messages.create(
            model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        s, e = raw.find('{'), raw.rfind('}')
        return json.loads(raw[s:e+1])

    # ── HOME TOUR ─────────────────────────────────────────────────────────────
    if content_type == 'home_tour':
        # Pick a random price tier (mix of luxury and approachable)
        config = random.choice(HOME_TOUR_CONFIGS)
        tier   = config['tier']
        
        # Pick neighborhood from tier's list, or fall back to random
        hood_pool = [n for n in config['neighborhoods'] if n in SD_NEIGHBORHOODS]
        neighborhood = random.choice(hood_pool) if hood_pool else random.choice(SD_NEIGHBORHOODS)
        
        # Generate price within tier range
        low_str, high_str = config['price_range']
        
        # Generate a truly random price within the tier range
        import random as _rand
        def _parse_price(s):
            s = s.replace('$','').replace(',','').strip()
            if 'M' in s: return float(s.replace('M','')) * 1_000_000
            if 'K' in s: return float(s.replace('K','')) * 1_000
            return float(s)
        low_num  = _parse_price(low_str)
        high_num = _parse_price(high_str)
        rand_price = _rand.randint(int(low_num), int(high_num))
        # Round to realistic increments ($25K steps)
        rand_price = round(rand_price / 25000) * 25000
        price_str  = f'${rand_price:,}'

        prompt = f"""Create a fictional luxury property showcase post for Whitney Pierce featuring a home in {neighborhood}, San Diego.
Price tier: {tier}
The price is EXACTLY: {price_str} — use this exact price, do not change it.
Generate a compelling, specific fictional property — real architectural details, specific features, no generic descriptions.

Return ONLY valid JSON:
{{
  "content_type": "home_tour",
  "neighborhood": "{neighborhood}",
  "tier": "{tier}",
  "price": "{price_str}",
  "beds": "number only (e.g. '4')",
  "baths": "number only (e.g. '3')",
  "sqft": "number with comma (e.g. '2,847')",
  "headline": "compelling property headline max 8 words (NOT 'dream home')",
  "feature_1": "most impressive feature in 5-6 words (e.g. 'Vaulted ceilings with exposed beams')",
  "feature_2": "second best feature in 5-6 words (e.g. 'Chef kitchen with Taj Mahal quartz')",
  "feature_3": "lifestyle feature in 5-6 words (e.g. 'Walk to Del Mar Village')",
  "stat": "price per sqft or lot size under 20 chars (e.g. '$820/sqft' or '0.4 acre lot')",
  "caption": "4-5 sentences from Whitney about this property. Start with something that makes you stop scrolling. Specific details, genuine excitement, no clichés. End with a call to action to DM her.",
  "hashtags": "#WhisselBeerGroup #SanDiego #{neighborhood.replace(' ','')} #JustListed #SanDiegoRealEstate #LuxuryHomes #SDHomes #ExpRealty #WhitneyPierceWBG"
}}"""

        msg = client.messages.create(
            model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        s, e = raw.find('{'), raw.rfind('}')
        return json.loads(raw[s:e+1])

    # ── EXISTING CONTENT TYPES ────────────────────────────────────────────────
    prompts = {

        'sd_hidden_gem': f"""Write a post where Whitney shares a surprising or little-known fact specifically about "{neighborhood}" in San Diego.
IMPORTANT: The fact must be about {neighborhood} specifically — not about another San Diego neighborhood or landmark.
Tie it back to why this makes {neighborhood} real estate special or why people stay here forever.
Seed fact for inspiration (use it or create a better one about {neighborhood}): "{sd_fact}"

Return ONLY valid JSON:
{{
  "content_type": "sd_hidden_gem",
  "neighborhood": "{neighborhood}",
  "headline": "short punchy headline about {neighborhood} (max 8 words)",
  "insight": "the surprising fact about {neighborhood} — 1-2 sentences, first person Whitney voice",
  "real_estate_tie": "one sentence connecting this {neighborhood} fact to real estate value",
  "stat": "ONE short number or year under 20 characters (e.g. '1887', '4,600 acres', '$1.8M median')",
  "context": "brief supporting context for the stat — one sentence max",
  "caption": "3-4 sentences in Whitney's voice about {neighborhood}. Personal, specific. End with a question.",
  "hashtags": "#WhisselBeerGroup #SanDiego #{neighborhood.replace(' ','')} #SanDiegoFacts #SanDiegoRealEstate #SDLiving #ExpRealty #WhitneyPierceWBG"
}}""",

        'current_event_tie': f"""Write a post where Whitney ties a current San Diego event or happening specifically in or near "{neighborhood}" to a real estate insight.
IMPORTANT: Keep the focus on {neighborhood} — not other neighborhoods.

Return ONLY valid JSON:
{{
  "content_type": "current_event_tie",
  "neighborhood": "{neighborhood}",
  "headline": "event or hook about {neighborhood} (max 8 words)",
  "insight": "what's happening in {neighborhood} right now — 1-2 sentences, Whitney's voice",
  "real_estate_tie": "how this affects real estate in {neighborhood}",
  "stat": "ONE short number under 20 characters (attendance, price, year, etc.)",
  "context": "one line of supporting context",
  "caption": "3-4 sentences from Whitney connecting the event to {neighborhood} real estate. End with a call to action.",
  "hashtags": "#WhisselBeerGroup #SanDiego #{neighborhood.replace(' ','')} #SanDiegoEvents #SanDiegoRealEstate #SDLife #ExpRealty #WhitneyPierceWBG"
}}""",

        'hot_take': f"""Write a post where Whitney shares a bold, slightly eccentric real estate opinion about "{neighborhood}".
It should be confident, a little surprising, maybe counterintuitive — but backed by real knowledge of {neighborhood}.
IMPORTANT: Keep it specific to {neighborhood}.

Return ONLY valid JSON:
{{
  "content_type": "hot_take",
  "neighborhood": "{neighborhood}",
  "headline": "bold opinion about {neighborhood} in 6-8 words",
  "insight": "Whitney's hot take about {neighborhood} — 1-2 sentences, confident and specific",
  "real_estate_tie": "the practical real estate implication of this take for {neighborhood}",
  "stat": "ONE short number under 20 characters that supports the take",
  "context": "brief evidence or context",
  "tip_type": "HOT TAKE",
  "caption": "3-4 sentences where Whitney makes her case about {neighborhood}. End by inviting people to agree or disagree.",
  "hashtags": "#WhisselBeerGroup #SanDiegoRealEstate #{neighborhood.replace(' ','')} #RealEstateTips #SDHotTake #ExpRealty #WhitneyPierceWBG #SanDiegoExpert"
}}""",

        'hyper_local_intel': f"""Write a post where Whitney shares hyper-specific, insider market intelligence about "{neighborhood}" in San Diego.
Not generic stats — specific intel only a local expert would know about {neighborhood}.
IMPORTANT: All data must be specifically about {neighborhood}, not San Diego generally.

Return ONLY valid JSON:
{{
  "content_type": "hyper_local_intel",
  "neighborhood": "{neighborhood}",
  "headline": "the intel in 6-8 words — specific to {neighborhood}",
  "insight": "the insider market insight about {neighborhood} — specific, local, 1-2 sentences from Whitney",
  "real_estate_tie": "what this means for buyers or sellers in {neighborhood} right now",
  "stat": "ONE short market number under 20 characters (e.g. '14 days DOM', '+12% YoY', '$850K median')",
  "context": "one line explaining what drives this trend in {neighborhood}",
  "tip_type": "MARKET INTEL",
  "caption": "3-4 sentences from Whitney sharing the intel like she's texting a friend. Specific to {neighborhood}. End with an offer to share more.",
  "hashtags": "#WhisselBeerGroup #{neighborhood.replace(' ','')} #SanDiegoRealEstate #SanDiegoMarket #LocalExpert #SDRealEstate #ExpRealty #WhitneyPierceWBG"
}}""",

        'sd_lifestyle_hook': f"""Write a post where Whitney starts with a vivid lifestyle moment in "{neighborhood}" and connects it to why people buy real estate there.
Start with something sensory and specific about {neighborhood} — a morning there, a Saturday, something that makes you feel the place.
IMPORTANT: The lifestyle moment must be specific to {neighborhood}, not generic San Diego.

Return ONLY valid JSON:
{{
  "content_type": "sd_lifestyle_hook",
  "neighborhood": "{neighborhood}",
  "headline": "vivid lifestyle moment in {neighborhood} (6-8 words)",
  "insight": "the vivid description of {neighborhood} — 1-2 sentences, present tense, you can almost feel it",
  "lifestyle_line": "one sentence capturing the essence of {neighborhood}",
  "real_estate_tie": "one sentence connecting this {neighborhood} lifestyle to why people buy and never leave",
  "stat": "ONE short number under 20 characters (sunshine days, price, year built, etc.)",
  "context": "brief context for the stat",
  "caption": "3-4 sentences from Whitney — start with the {neighborhood} lifestyle moment, end with the real estate truth. Zero clichés. End with a question.",
  "hashtags": "#WhisselBeerGroup #SanDiego #{neighborhood.replace(' ','')} #SanDiegoLiving #SanDiegoLifestyle #SDRealEstate #ExpRealty #WhitneyPierceWBG"
}}"""
    }

    msg = client.messages.create(
        model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompts[content_type]}]
    )
    raw = msg.content[0].text.strip()
    s, e = raw.find('{'), raw.rfind('}')
    return json.loads(raw[s:e+1])
