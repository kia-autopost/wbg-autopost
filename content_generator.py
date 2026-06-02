"""
WBG Content Generator
Uses Claude to generate real estate content for San Diego County.
Rotates between 5 content types for variety.
"""
import os, random, json
import anthropic

CONTENT_TYPES = ['property_spotlight', 'market_stat', 'buyer_seller_tip', 'investor_quote', 'san_diego_lifestyle']

SD_NEIGHBORHOODS = [
    'La Jolla', 'Del Mar', 'Coronado', 'Carmel Valley', 'Rancho Santa Fe',
    'Pacific Beach', 'Mission Hills', 'North Park', 'Encinitas', 'Carlsbad',
    'Chula Vista', 'Point Loma', 'Hillcrest', 'Ocean Beach', 'Solana Beach',
    'Escondido', 'Santee', 'El Cajon', 'Poway', 'Scripps Ranch'
]

def generate_post(content_type: str = None, api_key: str = None) -> dict:
    if api_key is None:
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if content_type is None:
        content_type = random.choice(CONTENT_TYPES)

    neighborhood = random.choice(SD_NEIGHBORHOODS)
    client = anthropic.Anthropic(api_key=api_key)

    prompts = {
        'property_spotlight': f"""Generate a property spotlight post for a home in {neighborhood}, San Diego.
Return ONLY valid JSON with these exact keys:
{{"content_type":"property_spotlight","headline":"short punchy headline","price_range":"price like $1.2M - $1.5M","beds":"3-4","baths":"2-3","sqft":"approx sqft","neighborhood":"{neighborhood}","highlight":"one compelling feature","caption":"2-3 sentences for Instagram. End with: DM us to find yours. Ã°ÂÂÂ¡","hashtags":"#WhisselBeerGroup #SanDiegoRealEstate #{neighborhood.replace(' ','')} #SanDiegoHomes #ExpRealty #SDRealEstate #HomesForSale #SanDiegoBestAgent"}}""",

        'market_stat': f"""Generate a compelling San Diego County real estate market stat post.
Return ONLY valid JSON with these exact keys:
{{"content_type":"market_stat","stat":"one bold statistic like 'Median home price up 8% YoY'","context":"one line of context","caption":"2-3 sentences about what this means for buyers/sellers in San Diego. End with: Questions? DM us. Ã°ÂÂÂ","hashtags":"#WhisselBeerGroup #SanDiegoRealEstate #SanDiegoMarket #RealEstateInvesting #SDHousing #MarketUpdate #ExpRealty"}}""",

        'buyer_seller_tip': f"""Generate a practical real estate tip for San Diego buyers or sellers.
Return ONLY valid JSON with these exact keys:
{{"content_type":"buyer_seller_tip","tip_type":"Buyer Tip or Seller Tip","headline":"short tip headline","tip":"the actual tip in 1-2 sentences","caption":"2-3 sentences expanding on the tip. End with: Ready to get started? DM us. Ã°ÂÂÂ¡","hashtags":"#WhisselBeerGroup #SanDiegoRealEstate #RealEstateTips #HomeBuying #HomeSelling #SDRealEstate #ExpRealty"}}""",

        'investor_quote': """Generate a motivational real estate investor quote.
Return ONLY valid JSON with these exact keys:
{"content_type":"investor_quote","quote":"powerful quote about real estate wealth or investing","author":"real or generic like 'Warren Buffett' or 'Real Estate Wisdom'","caption":"2-3 sentences tying the quote to San Diego real estate opportunity. End with: Let's build wealth together. Ã°ÂÂÂ¼","hashtags":"#WhisselBeerGroup #RealEstateInvesting #WealthBuilding #SanDiegoRealEstate #PassiveIncome #InvestInRealEstate #ExpRealty"}""",

        'san_diego_lifestyle': f"""Generate a San Diego lifestyle + real estate post about {neighborhood}.
Return ONLY valid JSON with these exact keys:
{{"content_type":"san_diego_lifestyle","headline":"why people love {neighborhood}","lifestyle_line":"one vivid lifestyle description","real_estate_tie":"one sentence connecting lifestyle to home value","caption":"2-3 sentences about living in {neighborhood} and the real estate opportunity. End with: Find your San Diego home. Ã°ÂÂÂ","hashtags":"#WhisselBeerGroup #SanDiego #{neighborhood.replace(' ','')} #SanDiegoLiving #SanDiegoLifestyle #SDRealEstate #ExpRealty"}}"""
    }

    msg = client.messages.create(
        model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
        max_tokens=600,
        messages=[{'role': 'user', 'content': prompts[content_type]}]
    )
    raw = msg.content[0].text
    s, e = raw.find('{'), raw.rfind('}')
    return json.loads(raw[s:e+1])
