import os
import sys
import pickle
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service(project_root):
    credentials_file = os.path.join(project_root, 'client_secret.json')
    token_file = os.path.join(project_root, 'token.pickle')
    
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
            
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                print(f"Error: Credentials file not found at {credentials_file}.")
                print("\n==================================================================")
                print("ACTION REQUIRED:")
                print(f"Please download your OAuth client credential JSON file from Google")
                print(f"Console, rename it to 'client_secret.json', and save it to:")
                print(f"{credentials_file}")
                print("==================================================================\n")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

def upload_video(youtube, video_path, title, description, privacy_status="public"):
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return False
        
    print(f"Uploading {video_path} to YouTube...")
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'categoryId': '22'  # People & Blogs
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }

    # Call the API's videos.insert method to create and upload the video.
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
            
    print(f"SUCCESS: Video uploaded! Video ID is: {response['id']}")
    return response['id']

if __name__ == '__main__':
    project_root = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) < 4:
        print("Usage: python youtube_uploader.py [video_path] [title] [description] [optional: privacy_status]")
        sys.exit(1)
        
    video_path = sys.argv[1]
    title = sys.argv[2]
    description = sys.argv[3]
    privacy_status = sys.argv[4] if len(sys.argv) > 4 else "public"
    
    youtube = get_authenticated_service(project_root)
    upload_video(youtube, video_path, title, description, privacy_status)
