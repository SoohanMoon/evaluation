# 구글드라이브 + Colab 웹서버 설정
# 이 파일을 구글 Colab에서 실행하세요

# 1. 구글드라이브 마운트
from google.colab import drive
drive.mount('/content/drive')

# 2. 필요한 패키지 설치
!pip install flask flask-sqlalchemy pandas numpy

# 3. 파일들을 구글드라이브에서 복사
import shutil
import os

# 구글드라이브 경로 설정 (본인의 경로로 수정)
drive_path = '/content/drive/MyDrive/인사평가시스템'  # 구글드라이브에 업로드한 폴더명

# 현재 작업 디렉토리로 파일들 복사
if os.path.exists(drive_path):
    for file in os.listdir(drive_path):
        if file.endswith('.py') or file.endswith('.csv') or file.endswith('.html'):
            shutil.copy(os.path.join(drive_path, file), f'/content/{file}')
    print("파일 복사 완료")
else:
    print("구글드라이브 경로를 확인해주세요")

# 4. Flask 앱 실행 (외부 접속 가능)
!python 인사평가시스템.py &

# 5. ngrok 설치 및 실행 (외부 접속용)
!pip install pyngrok
from pyngrok import ngrok

# ngrok 터널 생성
public_url = ngrok.connect(5000)
print(f"외부 접속 URL: {public_url}")

# 6. 서버 상태 확인
import time
time.sleep(3)
print("서버가 실행되었습니다!")
print(f"로컬 접속: http://localhost:5000")
print(f"외부 접속: {public_url}") 