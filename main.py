import os, logging, time, traceback, threading
from datetime import datetime
from flask import Flask, jsonify
import pytz
from content_generator import generate_post, CONTENT_TYPES
from video_generator import generate_reel
from instagram_api import post_reel_to_instagram

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger('WBG')

TZ            = os.getenv('TIMEZONE', 'America/Los_Angeles')
TIME_MORNING  = os.getenv('POST_TIME_MORNING', '08:00')
TIME_EVENING  = os.getenv('POST_TIME_EVENING', '18:00')
ANTHROPIC_KEY = os.getenv('ANTHROPIC_API_KEY', '')
IG_USER_ID    = os.getenv('INSTAGRAM_USER_ID', '')
IG_TOKEN      = os.getenv('INSTAGRAM_ACCESS_TOKEN', '')
CLD_CLOUD     = os.getenv('CLOUDINARY_CLOUD_NAME', '')
CLD_KEY       = os.getenv('CLOUDINARY_API_KEY', '')
CLD_SECRET    = os.getenv('CLOUDINARY_API_SECRET', '')

app = Flask(__name__)
_post_index = [0]

def run_post(slot='morning'):
    log.info(f'--- Starting {slot} post ---')
    try:
        ct = CONTENT_TYPES[_post_index[0] % len(CONTENT_TYPES)]
        _post_index[0] += 1
        post_data = generate_post(ct, ANTHROPIC_KEY)
        log.info(f'Content type: {ct}')
        video_url = generate_reel(post_data)
        log.info(f'Video ready: {video_url}')
        result = post_reel_to_instagram(
            video_url, post_data['caption'],
            IG_USER_ID, IG_TOKEN, CLD_CLOUD, CLD_KEY, CLD_SECRET
        )
        log.info(f'Posted to Instagram! ID: {result}')
        return True, result
    except Exception as e:
        log.error(f'Post failed: {e}')
        log.error(traceback.format_exc())
        return False, str(e)

@app.route('/test', methods=['GET', 'POST'])
def test_post():
    log.info('Manual test triggered via /test')
    t = threading.Thread(target=run_post, kwargs={'slot': 'morning'}, daemon=True)
    t.start()
    return jsonify({
        'status': 'started',
        'message': 'Post generating in background. Check logs and Instagram in ~2 min!'
    }), 200

@app.route('/debug', methods=['GET', 'POST'])
def debug_post():
    log.info('Debug test triggered — running synchronously')
    try:
        ct = CONTENT_TYPES[0]
        log.info(f'Step 1: Generating content for type: {ct}')
        post_data = generate_post(ct, ANTHROPIC_KEY)
        log.info(f'✅ Content generated: {post_data}')

        log.info('Step 2: Generating reel...')
        video_url = generate_reel(post_data)
        log.info(f'✅ Video ready: {video_url}')

        log.info('Step 3: Posting to Instagram...')
        result = post_reel_to_instagram(
            video_url, post_data['caption'],
            IG_USER_ID, IG_TOKEN, CLD_CLOUD, CLD_KEY, CLD_SECRET
        )
        log.info(f'✅ Posted! ID: {result}')
        return jsonify({'status': 'success', 'instagram_id': result}), 200

    except Exception as e:
        return jsonify({
            'status':       'error',
            'step_failed':  type(e).__name__,
            'error':        str(e),
            'traceback':    traceback.format_exc()
        }), 500

@app.route('/health')
def health():
    return jsonify({
        'status':   'running',
        'timezone': TZ,
        'morning':  TIME_MORNING,
        'evening':  TIME_EVENING
    }), 200

def scheduler_loop():
    tz = pytz.timezone(TZ)
    posted_today = set()
    log.info(f'Scheduler running - TZ: {TZ}, Posts at: {TIME_MORNING} and {TIME_EVENING}')
    while True:
        now      = datetime.now(tz)
        hhmm     = now.strftime('%H:%M')
        date_str = now.strftime('%Y-%m-%d')

        morning_key = f'{date_str}_morning'
        evening_key = f'{date_str}_evening'

        if hhmm == TIME_MORNING and morning_key not in posted_today:
            posted_today.add(morning_key)
            threading.Thread(target=run_post, args=('morning',), daemon=True).start()
        elif hhmm == TIME_EVENING and evening_key not in posted_today:
            posted_today.add(evening_key)
            threading.Thread(target=run_post, args=('evening',), daemon=True).start()

        if hhmm == '00:01':
            posted_today = set()

        time.sleep(20)

def safe_scheduler():
    try:
        time.sleep(3)
        scheduler_loop()
    except Exception as e:
        log.error(f'Scheduler crashed: {e}')
        log.error(traceback.format_exc())

_scheduler_thread = threading.Thread(target=safe_scheduler, daemon=True)
_scheduler_thread.start()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    log.info(f'WBG Auto-Poster starting on port {port}')
    app.run(host='0.0.0.0', port=port)
