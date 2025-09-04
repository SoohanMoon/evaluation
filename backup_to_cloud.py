import os
import shutil
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# Google Drive API 설정
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveBackup:
    def __init__(self):
        self.service = self.get_drive_service()
        self.backup_folder_id = self.get_or_create_backup_folder()
    
    def get_drive_service(self):
        """Google Drive API 서비스 생성"""
        creds = None
        
        # 토큰 파일이 있으면 로드
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # 유효한 인증 정보가 없으면 새로 생성
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    def get_or_create_backup_folder(self):
        """백업 폴더 생성 또는 가져오기"""
        # 기존 백업 폴더 검색
        results = self.service.files().list(
            q="name='평가시스템_백업' and mimeType='application/vnd.google-apps.folder'",
            spaces='drive'
        ).execute()
        
        if results['files']:
            return results['files'][0]['id']
        
        # 새 백업 폴더 생성
        folder_metadata = {
            'name': '평가시스템_백업',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = self.service.files().create(
            body=folder_metadata, fields='id'
        ).execute()
        
        return folder['id']
    
    def upload_file(self, file_path, file_name):
        """파일을 Google Drive에 업로드"""
        if not os.path.exists(file_path):
            print(f"파일이 존재하지 않습니다: {file_path}")
            return None
        
        # 파일 메타데이터
        file_metadata = {
            'name': file_name,
            'parents': [self.backup_folder_id]
        }
        
        # 파일 업로드
        media = MediaFileUpload(file_path, resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"파일 업로드 완료: {file_name}")
        return file['id']
    
    def backup_data(self):
        """모든 데이터 파일 백업"""
        today = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 백업할 파일들
        files_to_backup = [
            ('evaluation_data.csv', f'evaluation_data_{today}.csv'),
            ('team_members.json', f'team_members_{today}.json'),
            ('users.json', f'users_{today}.json')
        ]
        
        uploaded_files = []
        for file_path, backup_name in files_to_backup:
            if os.path.exists(file_path):
                file_id = self.upload_file(file_path, backup_name)
                if file_id:
                    uploaded_files.append((backup_name, file_id))
        
        return uploaded_files

# 간단한 백업 함수 (Google Drive API 없이)
def simple_backup():
    """간단한 로컬 백업"""
    today = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_{today}"
    
    # 백업 디렉토리 생성
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # 백업할 파일들
    files_to_backup = [
        'evaluation_data.csv',
        'team_members.json',
        'users.json'
    ]
    
    for file_name in files_to_backup:
        if os.path.exists(file_name):
            shutil.copy2(file_name, os.path.join(backup_dir, file_name))
            print(f"백업 완료: {file_name}")
    
    return backup_dir

if __name__ == "__main__":
    print("데이터 백업을 시작합니다...")
    
    # 간단한 로컬 백업
    backup_dir = simple_backup()
    print(f"로컬 백업 완료: {backup_dir}")
    
    # Google Drive 백업 (credentials.json 파일이 있는 경우)
    if os.path.exists('credentials.json'):
        try:
            drive_backup = GoogleDriveBackup()
            uploaded_files = drive_backup.backup_data()
            print(f"Google Drive 백업 완료: {len(uploaded_files)}개 파일")
        except Exception as e:
            print(f"Google Drive 백업 실패: {e}")
    else:
        print("Google Drive 백업을 위해 credentials.json 파일이 필요합니다.") 