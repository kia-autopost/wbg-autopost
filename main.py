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

# Audio: posts go out silent, add trending audio via Instagram after posting

# Lock prevents two posts running simultaneously (avoids caption/video mismatch)
_post_lock = threading.Lock()

def run_post(slot='morning'):
    # If another post is already generating, skip
    if not _post_lock.acquire(blocking=False):
        log.warning(f'Post skipped — another post is already in progress')
        return False, 'locked'

    try:
        import random as _r
        log.info(f'--- Starting {slot} post ---')
        ct        = _r.choice(CONTENT_TYPES)
        post_data = generate_post(ct, ANTHROPIC_KEY)
        log.info(f'Content: {ct} | {post_data.get("neighborhood","")}')

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

    finally:
        _post_lock.release()

@app.route('/test', methods=['GET', 'POST'])
def test_post():
    if _post_lock.locked():
        return jsonify({'status': 'busy', 'message': 'A post is already generating. Try again in a few minutes.'}), 429
    log.info('Manual test triggered via /test')
    t = threading.Thread(target=run_post, kwargs={'slot': 'test'}, daemon=True)
    t.start()
    return jsonify({'status': 'started', 'message': 'Generating — check Instagram in ~4 min!'}), 200

@app.route('/test_market', methods=['GET', 'POST'])
def test_market():
    if _post_lock.locked():
        return jsonify({'status': 'busy'}), 429
    log.info('Market data test triggered')
    def _run():
        from content_generator import generate_post
        import random as _r
        if not _post_lock.acquire(blocking=False): return
        try:
            post_data = generate_post('market_data', ANTHROPIC_KEY)
            log.info(f'Market data: {post_data.get("neighborhood","")}')
            video_url = generate_reel(post_data)
            result = post_reel_to_instagram(video_url, post_data['caption'],
                IG_USER_ID, IG_TOKEN, CLD_CLOUD, CLD_KEY, CLD_SECRET)
            log.info(f'Posted market data! ID: {result}')
        except Exception as e:
            log.error(f'Market test failed: {e}')
            log.error(traceback.format_exc())
        finally:
            _post_lock.release()
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'type': 'market_data'}), 200

@app.route('/test_hometour', methods=['GET', 'POST'])
def test_hometour():
    if _post_lock.locked():
        return jsonify({'status': 'busy'}), 429
    log.info('Home tour test triggered')
    def _run():
        import random as _r
        from content_generator import generate_post
        if not _post_lock.acquire(blocking=False): return
        try:
            post_data = generate_post('home_tour', ANTHROPIC_KEY)
            log.info(f'Home tour: {post_data.get("neighborhood","")} {post_data.get("price","")}')
            video_url = generate_reel(post_data)
            result = post_reel_to_instagram(video_url, post_data['caption'],
                IG_USER_ID, IG_TOKEN, CLD_CLOUD, CLD_KEY, CLD_SECRET)
            log.info(f'Posted home tour! ID: {result}')
        except Exception as e:
            log.error(f'Home tour test failed: {e}')
            log.error(traceback.format_exc())
        finally:
            _post_lock.release()
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'type': 'home_tour'}), 200

@app.route('/health')
def health():
    return jsonify({
        'status':   'running',
        'busy':     _post_lock.locked(),
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

        # Parse scheduled times for window comparison
        def _past_time(target_hhmm):
            th, tm = map(int, target_hhmm.split(':'))
            nh, nm = now.hour, now.minute
            return (nh * 60 + nm) >= (th * 60 + tm)

        def _within_window(target_hhmm, window_mins=5):
            th, tm = map(int, target_hhmm.split(':'))
            nh, nm = now.hour, now.minute
            diff = (nh * 60 + nm) - (th * 60 + tm)
            return 0 <= diff <= window_mins

        # Fire if within 5-minute window after scheduled time (catches sleep drift)
        if _within_window(TIME_MORNING) and morning_key not in posted_today:
            posted_today.add(morning_key)
            log.info(f'Firing morning post at {hhmm}')
            threading.Thread(target=run_post, args=('morning',), daemon=True).start()
        elif _within_window(TIME_EVENING) and evening_key not in posted_today:
            posted_today.add(evening_key)
            log.info(f'Firing evening post at {hhmm}')
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
