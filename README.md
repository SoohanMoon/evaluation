# 인사평가 시스템

Flask 기반의 인사평가 시스템입니다.

## Railway 배포 가이드

### 1. Railway에 프로젝트 배포

1. [Railway.app](https://railway.app)에 로그인
2. "New Project" 클릭
3. "Deploy from GitHub repo" 선택
4. GitHub 저장소 연결
5. 자동으로 배포 시작

### 2. 환경변수 설정

Railway 대시보드에서 다음 환경변수들을 설정하세요:

#### 필수 환경변수
- `FLASK_DEBUG`: `False` (프로덕션 환경)
- `PORT`: Railway가 자동으로 설정 (수정 불필요)

#### 선택적 환경변수
- `DATABASE_URL`: PostgreSQL 데이터베이스 URL (Railway PostgreSQL 서비스 사용 시)

### 3. 데이터베이스 설정

#### 옵션 1: Railway PostgreSQL 사용 (권장)
1. Railway에서 PostgreSQL 서비스 추가
2. 자동으로 생성되는 `DATABASE_URL` 환경변수 사용
3. 애플리케이션이 자동으로 PostgreSQL 연결

#### 옵션 2: SQLite 사용 (개발용)
- 별도 설정 없이 SQLite 데이터베이스 자동 생성
- Railway의 임시 파일 시스템 사용 (재시작 시 데이터 손실 가능)

### 4. CSV 파일 업로드

다음 CSV 파일들을 프로젝트 루트 디렉토리에 업로드하세요:

- `backdata.csv`: 사용자 정보 (ID, 비밀번호, 이름, 팀, 직급 등)
- `평가자(팀장)_사원.csv`: 팀장-사원 평가 매핑
- `평가자(팀장)_대리이상.csv`: 팀장-대리이상 평가 매핑
- `평가자(팀장)_일반직.csv`: 팀장-일반직 평가 매핑
- `평가자(임원)_팀장.csv`: 임원-팀장 평가 매핑
- `평가자(임원)_팀원 관리직.csv`: 임원-팀원 관리직 평가 매핑
- `평가자(임원)_팀원 일반직.csv`: 임원-팀원 일반직 평가 매핑
- `Jikkeup.csv`: 직급별 역할 정의

### 5. 배포 확인

배포 완료 후:
1. Railway에서 제공하는 URL로 접속
2. `/health` 엔드포인트로 헬스체크 확인
3. 관리자 계정으로 로그인하여 시스템 확인

### 6. 관리자 계정

기본 관리자 계정:
- ID: `11210110` (backdata.csv에 등록된 계정)
- 또는 ID: `admin`, 비밀번호: `admin123`

## 로컬 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# 애플리케이션 실행
python eva.py
```

## 주요 기능

- **피평가자**: 실적 작성 및 등록
- **평가자(팀장)**: 팀원 평가
- **평가자(임원)**: 팀장 및 팀원 평가
- **관리자**: 전체 시스템 관리 및 데이터 조회

## 기술 스택

- **Backend**: Flask, SQLite/PostgreSQL
- **Frontend**: HTML, CSS, JavaScript
- **Data Processing**: pandas
- **Deployment**: Railway