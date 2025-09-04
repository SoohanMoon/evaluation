# Colab 간단 버전 - 이 코드를 Colab에 직접 복사해서 실행하세요

# 1. 필요한 패키지 설치
!pip install flask flask-sqlalchemy pandas numpy pyngrok

# 2. 파일들을 직접 업로드 (Colab 파일 탭에서)
print("파일 탭에서 다음 파일들을 업로드하세요:")
print("- 인사평가시스템.py")
print("- 평가자_피평가자_매핑_utf8.csv")
print("- templates 폴더")

# 3. Flask 앱 실행
!python 인사평가시스템.py &

# 4. ngrok 터널 생성
from pyngrok import ngrok
import time

time.sleep(3)  # 서버 시작 대기
public_url = ngrok.connect(5000)
print(f"외부 접속 URL: {public_url}")
print("서버가 실행되었습니다!") 