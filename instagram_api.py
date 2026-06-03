"""WBG Instagram API - posts Reels to Instagram and Facebook."""
import os, time, logging, requests
import cloudinary, cloudinary.uploader
log = logging.getLogger('WBG')

# Long-lived token - valid for 60 days from June 2, 2026
IG_ACCESS_TOKEN = "EAAXXdtljzesBRs8Fs38tisah4hBZCAoImisQrTTnfK597QAxpZAY7pLsXCU0eRn7QGczMs0WZCkbrsjUseYGJRnVRVQN0iWc16ycRZAJA5ZAZB9YNjXK4NTjRRhMHnMJZAgZCK6Rq8ZC1ewgZAi6JJSFN62OHO8iMqcF9HU3zclhCW55yhOHM4syfZCbhgQeFb22rv0qZBAL"

def _upload_to_cloudinary(video_path, cloud, key, secret):
    if isinstance(video_path, str) and video_path.startswith('http'):
        log.info(f"Using existing video URL: {video_path}")
        return video_path
    cloudinary.config(cloud_name=cloud, api_key=key, api_secret=secret)
    result = cloudinary.uploader.upload_large(
        video_path, resource_type='video',
        public_id='wbg_daily_reel', overwrite=True
    )
    return result['secure_url']

def _create_container(ig_user_id, video_url, caption):
    log.info('Creating Instagram media container...')
    r = requests.post(
        f'https://graph.facebook.com/v21.0/{ig_user_id}/media',
        params={
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'share_to_feed': 'true',
            'access_token': IG_ACCESS_TOKEN
        }
    )
    r.raise_for_status()
    cid = r.json()['id']
    log.info(f'Container ID: {cid}')
    return cid

def _wait_for_ready(container_id, max_wait=300):
    log.info('Waiting for video to process...')
    for _ in range(max_wait // 10):
        time.sleep(10)
        r = requests.get(
            f'https://graph.facebook.com/v21.0/{container_id}',
            params={'fields': 'status_code', 'access_token': IG_ACCESS_TOKEN}
        )
        status = r.json().get('status_code', '')
        log.info(f'  Status: {status}')
        if status == 'FINISHED': return True
        if status == 'ERROR': raise RuntimeError('Video processing failed')
    raise TimeoutError('Video processing timed out')

def _publish(ig_user_id, container_id):
    log.info('Publishing reel...')
    r = requests.post(
        f'https://graph.facebook.com/v21.0/{ig_user_id}/media_publish',
        params={'creation_id': container_id, 'access_token': IG_ACCESS_TOKEN}
    )
    r.raise_for_status()
    media_id = r.json()['id']
    log.info(f'Published! Media ID: {media_id}')
    return media_id

def post_reel_to_instagram(video_path, caption, ig_user_id, access_token, cld_cloud, cld_key, cld_secret):
    log.info(f'Using token: {IG_ACCESS_TOKEN[:20]}...')
    video_url    = _upload_to_cloudinary(video_path, cld_cloud, cld_key, cld_secret)
    container_id = _create_container(ig_user_id, video_url, caption)
    _wait_for_ready(container_id)
    return _publish(ig_user_id, container_id)
