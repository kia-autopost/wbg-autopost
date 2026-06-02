"""
WBG Content Generator - v3 Whitney Pierce Local Expert Edition
--------------------------------------------------------------
Content is first-person Whitney, positioned as the go-to San Diego
real estate expert. Focuses on:
  - Surprising / little-known SD facts
  - Current SD events & neighborhood happenings
  - Eccentric / personality-driven real estate takes
  - Hyper-local market intel (not generic stats)
  - SD lifestyle tied to real estate decisions
"""
import os, random, json
import anthropic

CONTENT_TYPES = [
    'sd_hidden_gem',        # Surprising SD fact or little-known neighborhood insight
    'current_event_tie',    # Local SD event/news tied to real estate
    'hot_take',             # Eccentric / bold real estate opinion from Whitney
    'hyper_local_intel',    # Specific neighborhood market intel
    'sd_lifestyle_hook',    # SD lifestyle moment → real estate connection
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
    'The Gaslamp Quarter has over 90 restaurants and bars',
    'SD has more craft breweries per capita than almost any US city',
    'The average San Diego temperature is 70 degrees year-round',
    'Balboa Park is larger than Central Park in NYC',
    'SD ranks consistently in the top 5 most desirable cities to live in the US',
    'La Jolla Cove is home to a protected colony of sea lions',
    'The Del Mar racetrack season brings thousands of visitors each summer',
    'SD has the second largest naval fleet in the world',
    'Torrey Pines State Reserve has the rarest pine tree in North America',
    'The SD Zoo is considered one of the best in the world',
    'Coronado Island is actually a peninsula connected by a narrow strip of land',
    'SD has over 300 days of sunshine per year',
    'The Gaslamp Quarter was once called the Stingaree - San Diego\'s red light district',
    'SD is home to the largest urban cultural park in the US - Balboa Park',
    'North Park was named one of the coolest neighborhoods in America by multiple outlets',
    'Little Italy in SD is one of the most walkable neighborhoods on the West Coast',
    'SD has been the fastest appreciating major metro in California over the past decade',
]

SYSTEM_PROMPT = """You are writing social media content for Whitney Pierce, a San Diego real estate expert with Whissel Beer Group at eXp Realty. 

Whitney's voice is:
- Warm, confident, and genuinely passionate about San Diego
- Knowledgeable but never stuffy — she makes real estate feel exciting and accessible
- First-person, conversational — like a text from a knowledgeable friend
- Specific and local — she knows the neighborhoods intimately
- Occasionally surprising people with facts they didn't know about SD

Never use generic real estate language. No "dream home" or "motivated seller." 
Be specific, be human, be Whitney.
Always return ONLY valid JSON, no markdown, no preamble."""


def generate_post(content_type: str = None, api_key: str = None) -> dict:
    if api_key is None:
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if content_type is None:
        content_type = random.choice(CONTENT_TYPES)

    neighborhood = random.choice(SD_NEIGHBORHOODS)
    sd_fact      = random.choice(SD_EVENTS_AND_FACTS)
    client       = anthropic.Anthropic(api_key=api_key)

    prompts = {

        'sd_hidden_gem': f"""Write a post where Whitney shares a surprising or little-known fact about San Diego or the neighborhood "{neighborhood}". 
The fact should be genuinely interesting — something most people don't know. 
Tie it back to why this makes San Diego real estate special or why people stay here forever.
Seed fact to inspire you (you can use it or create a better one): "{sd_fact}"

Return ONLY valid JSON:
{{
  "content_type": "sd_hidden_gem",
  "neighborhood": "{neighborhood}",
  "headline": "short punchy headline revealing the surprising fact (max 8 words)",
  "insight": "the surprising fact or hidden gem — 1-2 sentences, first person Whitney voice",
  "real_estate_tie": "one sentence connecting this fact to real estate value or why people buy here",
  "stat": "one specific number or data point from the fact (e.g. '300 days of sunshine')",
  "context": "brief supporting context for the stat",
  "caption": "3-4 sentences in Whitney's voice sharing the fact and connecting to SD real estate. Personal, specific, no generic phrases. End with a question to engage followers.",
  "hashtags": "#WhisselBeerGroup #SanDiego #{neighborhood.replace(' ','')} #SanDiegoFacts #SanDiegoRealEstate #SDLiving #ExpRealty #WhitneyPierceWBG"
}}""",

        'current_event_tie': f"""Write a post where Whitney ties a current San Diego event, season, or happening to a real estate insight.
Use something timely — a seasonal event, a neighborhood development, a local trend, something happening in San Diego right now.
Neighborhood focus: "{neighborhood}". Inspiration: "{sd_fact}"

Return ONLY valid JSON:
{{
  "content_type": "current_event_tie",
  "neighborhood": "{neighborhood}",
  "headline": "event or happening name / short hook (max 8 words)",
  "insight": "what's happening in SD right now and why it matters — Whitney's voice, 1-2 sentences",
  "real_estate_tie": "how this event or trend affects real estate in the area",
  "stat": "one relevant number (attendance, price change, visitor count, etc.)",
  "context": "one line of supporting context",
  "caption": "3-4 sentences from Whitney connecting the event to why SD is such a special place to own real estate. Conversational and specific. End with a call to action.",
  "hashtags": "#WhisselBeerGroup #SanDiego #{neighborhood.replace(' ','')} #SanDiegoEvents #SanDiegoRealEstate #SDLife #ExpRealty #WhitneyPierceWBG"
}}""",

        'hot_take': f"""Write a post where Whitney shares a bold, slightly eccentric real estate opinion or hot take.
It should be confident, a little surprising, maybe counterintuitive — but backed by real knowledge of San Diego.
Could be about a neighborhood people overlook, a common mistake buyers make, why a "bad" area is actually great, etc.
Neighborhood to potentially feature: "{neighborhood}"

Return ONLY valid JSON:
{{
  "content_type": "hot_take",
  "neighborhood": "{neighborhood}",
  "headline": "the bold opinion in 6-8 words (provocative, not clickbait)",
  "insight": "Whitney's hot take — 1-2 sentences, first person, confident and specific",
  "real_estate_tie": "the practical real estate implication of this take",
  "stat": "one number or fact that supports the hot take",
  "context": "brief context or evidence",
  "tip_type": "HOT TAKE",
  "caption": "3-4 sentences where Whitney makes her case. Personality-forward, specific to SD. End by inviting people to agree or disagree.",
  "hashtags": "#WhisselBeerGroup #SanDiegoRealEstate #{neighborhood.replace(' ','')} #RealEstateTips #SDHotTake #ExpRealty #WhitneyPierceWBG #SanDiegoExpert"
}}""",

        'hyper_local_intel': f"""Write a post where Whitney shares hyper-specific, insider market intelligence about "{neighborhood}" in San Diego.
Not generic stats — specific intel like days on market, what's happening with inventory, a micro-trend only a local expert would know.

Return ONLY valid JSON:
{{
  "content_type": "hyper_local_intel",
  "neighborhood": "{neighborhood}",
  "headline": "the intel in 6-8 words — specific to {neighborhood}",
  "insight": "the insider market insight — specific, local, 1-2 sentences from Whitney",
  "real_estate_tie": "what this means for buyers or sellers in {neighborhood} right now",
  "stat": "one specific market number (e.g. 'median price up 12%', '14 days avg on market')",
  "context": "one line explaining what drives this trend in {neighborhood}",
  "tip_type": "MARKET INTEL",
  "caption": "3-4 sentences from Whitney sharing the intel like she's texting a friend. Specific to {neighborhood}, no generic language. End with an offer to share more.",
  "hashtags": "#WhisselBeerGroup #{neighborhood.replace(' ','')} #SanDiegoRealEstate #SanDiegoMarket #LocalExpert #SDRealEstate #ExpRealty #WhitneyPierceWBG"
}}""",

        'sd_lifestyle_hook': f"""Write a post where Whitney starts with a vivid San Diego lifestyle moment and connects it to why people buy real estate here.
Start with something sensory and specific — a morning in {neighborhood}, a Saturday in SD, something that makes you feel the place.
Inspiration: "{sd_fact}"

Return ONLY valid JSON:
{{
  "content_type": "sd_lifestyle_hook",
  "neighborhood": "{neighborhood}",
  "headline": "the lifestyle moment in 6-8 words (vivid, sensory)",
  "insight": "the vivid lifestyle description — 1-2 sentences, present tense, you can almost feel it",
  "lifestyle_line": "one sentence capturing the essence of this SD moment",
  "real_estate_tie": "one sentence connecting this feeling/lifestyle to why people buy here and never leave",
  "stat": "one number that captures why SD is special (sunshine days, coastline miles, etc.)",
  "context": "brief context for the stat",
  "caption": "3-4 sentences from Whitney — start with the lifestyle moment, end with the real estate truth. Personal, evocative, zero clichés. End with a question.",
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
