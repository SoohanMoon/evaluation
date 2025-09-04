# 구글 Colab에서 웹서버 실행 방법

## 1단계: 구글 Colab 접속
1. https://colab.research.google.com 접속
2. 새 노트북 생성

## 2단계: 구글드라이브 마운트
첫 번째 셀에 다음 코드 입력:

```python
from google.colab import drive
drive.mount('/content/drive')
```

실행 후 구글 계정 인증

## 3단계: 필요한 패키지 설치
두 번째 셀에 다음 코드 입력:

```python
!pip install flask flask-sqlalchemy pandas numpy pyngrok
```

## 4단계: 파일 복사
세 번째 셀에 다음 코드 입력:

```python
import shutil
import os

# 구글드라이브 경로 설정
drive_path = '/content/drive/MyDrive/인사평가시스템'

# 현재 작업 디렉토리로 파일들 복사
if os.path.exists(drive_path):
    for file in os.listdir(drive_path):
        if file.endswith('.py') or file.endswith('.csv'):
            shutil.copy(os.path.join(drive_path, file), f'/content/{file}')
    
    # templates 폴더 복사
    templates_path = os.path.join(drive_path, 'templates')
    if os.path.exists(templates_path):
        shutil.copytree(templates_path, '/content/templates', dirs_exist_ok=True)
    
    print("파일 복사 완료")
else:
    print("구글드라이브 경로를 확인해주세요")
```

## 5단계: Flask 앱 실행
네 번째 셀에 다음 코드 입력:

```python
!python 인사평가시스템_colab.py &
```

## 6단계: ngrok 터널 생성
다섯 번째 셀에 다음 코드 입력:

```python
from pyngrok import ngrok

# ngrok 터널 생성
public_url = ngrok.connect(5000)
print(f"외부 접속 URL: {public_url}")
```

## 7단계: 서버 상태 확인
여섯 번째 셀에 다음 코드 입력:

```python
import time
time.sleep(3)
print("서버가 실행되었습니다!")
print(f"외부 접속: {public_url}")
```

## 장점:
- ✅ 무료로 사용 가능
- ✅ 외부에서 접속 가능 (ngrok 터널)
- ✅ 구글드라이브와 연동
- ✅ 설정이 간단함

## 주의사항:
- ⚠️ Colab 세션은 12시간 후 자동 종료
- ⚠️ 무료 버전은 GPU 사용 시간 제한
- ⚠️ ngrok 무료 버전은 연결 수 제한

## 대안:
1. **유료 Colab Pro**: 더 긴 세션 시간
2. **Google Cloud Platform**: 안정적인 서버 운영
3. **Heroku**: 무료 티어 제공
4. **Railway**: 간단한 배포 