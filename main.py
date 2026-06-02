from flask import Flask
app = Flask(__name__)

import sys
print("Testing imports...", file=sys.stderr, flush=True)

try:
    from content_generator import generate_post, CONTENT_TYPES
    print("✅ content_generator OK", file=sys.stderr, flush=True)
except Exception as e:
    print(f"❌ content_generator FAILED: {e}", file=sys.stderr, flush=True)

try:
    from video_generator import generate_reel
    print("✅ video_generator OK", file=sys.stderr, flush=True)
except Exception as e:
    print(f"❌ video_generator FAILED: {e}", file=sys.stderr, flush=True)

try:
    from instagram_api import post_reel_to_instagram
    print("✅ instagram_api OK", file=sys.stderr, flush=True)
except Exception as e:
    print(f"❌ instagram_api FAILED: {e}", file=sys.stderr, flush=True)

@app.route('/health')
def health():
    return 'OK', 200
