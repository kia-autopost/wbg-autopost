"""WBG Instagram API - posts Reels to Instagram and Facebook."""
import os, time, logging, requests
import cloudinary, cloudinary.uploader
log = logging.getLogger('WBG')

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

def _refresh_token(access_token):
    # Long-lived token managed manually — no refresh needed
    return access_token

def _create_container(ig_user_id, access_token, video_url, caption):
    log.info('Creating Instagram media container...')
    r = requests.post(
        f'https://graph.facebook.com/v21.0/{ig_user_id}/media',
        params={'media_type':'REELS','video_url':video_url,
                'caption':caption,'share_to_feed':'true',
                'access_token':access_token}
    )
    r.raise_for_status()
    cid = r.json()['id']
    log.info(f'Container ID: {cid}')
    return cid

def _wait_for_ready(container_id, access_token, max_wait=300):
    log.info('Waiting for video to process...')
    for _ in range(max_wait // 10):
        time.sleep(10)
        r = requests.get(
            f'https://graph.facebook.com/v21.0/{container_id}',
            params={'fields':'status_code','access_token':access_token}
        )
        status = r.json().get('status_code','')
        log.info(f'  Status: {status}')
        if status == 'FINISHED': return True
        if status == 'ERROR': raise RuntimeError('Video processing failed')
    raise TimeoutError('Video processing timed out')

def _publish(ig_user_id, access_token, container_id):
    log.info('Publishing reel...')
    r = requests.post(
        f'https://graph.facebook.com/v21.0/{ig_user_id}/media_publish',
        params={'creation_id':container_id,'access_token':access_token}
    )
    r.raise_for_status()
    media_id = r.json()['id']
    log.info(f'Published! Media ID: {media_id}')
    return media_id

def post_reel_to_instagram(video_path, caption, ig_user_id, access_token, cld_cloud, cld_key, cld_secret):
    access_token = _refresh_token(access_token)
    video_url    = _upload_to_cloudinary(video_path, cld_cloud, cld_key, cld_secret)
    container_id = _create_container(ig_user_id, access_token, video_url, caption)
    _wait_for_ready(container_id, access_token)
    return _publish(ig_user_id, access_token, container_id)
