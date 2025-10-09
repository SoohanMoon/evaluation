# Railway 배포 가이드

## 🚀 Railway를 통한 인사평가 시스템 배포

### 1. Railway 계정 생성 및 준비

1. **Railway 웹사이트 접속**
   - https://railway.app 접속
   - GitHub 계정으로 로그인

2. **프로젝트 준비**
   - 현재 프로젝트를 GitHub에 푸시 (이미 완료됨)

### 2. Railway 배포 단계

#### Step 1: 새 프로젝트 생성
1. Railway 대시보드에서 "New Project" 클릭
2. "Deploy from GitHub repo" 선택
3. GitHub 저장소 선택

#### Step 2: 환경변수 설정
Railway 대시보드에서 Variables 탭에서 다음 환경변수 설정:

```
FLASK_DEBUG=False
PORT=8000
```

#### Step 3: 데이터베이스 설정
1. Railway 대시보드에서 "Add Service" 클릭
2. "Database" → "PostgreSQL" 선택
3. 생성된 PostgreSQL 서비스의 연결 정보를 확인

#### Step 4: 배포 확인
1. 배포가 완료되면 Railway에서 제공하는 URL로 접속
2. 애플리케이션이 정상 작동하는지 확인

### 3. 배포 후 확인사항

#### ✅ 기능 테스트
- [ ] 메인 페이지 접속
- [ ] 로그인 기능
- [ ] 피평가자 실적 작성
- [ ] 평가자 평가 기능
- [ ] 관리자 대시보드

#### ✅ 데이터베이스 확인
- [ ] SQLite → PostgreSQL 자동 전환 확인
- [ ] 데이터 저장/조회 기능

### 4. 도메인 설정 (선택사항)

1. Railway 대시보드에서 "Settings" → "Domains"
2. "Custom Domain" 추가
3. DNS 설정 (CNAME 레코드)

### 5. 모니터링 및 로그

- Railway 대시보드에서 실시간 로그 확인
- 배포 상태 및 성능 모니터링
- 오류 발생 시 로그 분석

### 6. 백업 및 복구

- Railway는 자동 백업 제공
- 필요시 수동 백업 설정 가능
- 데이터베이스 백업 정책 수립

## 🔧 문제 해결

### 일반적인 문제들

1. **배포 실패**
   - requirements.txt 확인
   - 로그에서 오류 메시지 확인
   - 환경변수 설정 확인

2. **데이터베이스 연결 오류**
   - PostgreSQL 연결 정보 확인
   - DATABASE_URL 환경변수 설정

3. **정적 파일 로딩 오류**
   - 템플릿 파일 경로 확인
   - CSS/JS 파일 경로 확인

## 📞 지원

배포 중 문제가 발생하면:
1. Railway 로그 확인
2. GitHub Issues에 문제 보고
3. 개발팀에 문의

---

**배포 완료 후 URL**: `https://your-app-name.railway.app`
