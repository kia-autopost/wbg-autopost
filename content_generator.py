"""
WBG Content Generator - v3 Whitney Pierce Local Expert Edition
Content is first-person Whitney, positioned as the go-to San Diego
real estate expert.
"""
import os, random, json
import anthropic

CONTENT_TYPES = [
    'sd_hidden_gem',
    'current_event_tie',
    'hot_take',
    'hyper_local_intel',
    'sd_lifestyle_hook',
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
    'The SD Zoo is considered one of the best in the world',
    'Coronado Island is actually a peninsula connected by a narrow strip of land',
    'SD has over 300 days of sunshine per year',
    'North Park was named one of the coolest neighborhoods in America',
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

CRITICAL RULES:
- The "stat" field must be SHORT — a number, year, or brief phrase under 20 characters (e.g. "1907", "300 days", "$1.2M", "2.2 miles"). NEVER a full sentence.
- ALL content must be specifically about the neighborhood named in the prompt. Do NOT substitute a different San Diego neighborhood or landmark.
- Never use generic real estate language. No "dream home" or "motivated seller."
- Be specific, be human, be Whitney.
- Always return ONLY valid JSON, no markdown, no preamble."""


def generate_post(content_type: str = None, api_key: str = None) -> dict:
    if api_key is None:
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if content_type is None:
        content_type = random.choice(CONTENT_TYPES)

    neighborhood = random.choice(SD_NEIGHBORHOODS)
    sd_fact      = random.choice(SD_EVENTS_AND_FACTS)
    client       = anthropic.Anthropic(api_key=api_key)

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
