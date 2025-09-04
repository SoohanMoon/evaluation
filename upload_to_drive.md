# 구글드라이브 업로드 가이드

## 1. 구글드라이브에 폴더 생성
1. 구글드라이브 접속: https://drive.google.com
2. 새 폴더 생성: "인사평가시스템"
3. 폴더명을 정확히 "인사평가시스템"으로 설정

## 2. 업로드할 파일들
다음 파일들을 구글드라이브의 "인사평가시스템" 폴더에 업로드:

### 필수 파일:
- `인사평가시스템.py` (메인 Flask 앱)
- `평가자_피평가자_매핑_utf8.csv` (데이터 파일)
- `templates/` 폴더 전체 (HTML 템플릿들)

### templates 폴더 내용:
- `base.html`
- `index.html`
- `evaluator_login.html`
- `admin_login.html`
- `evaluator_dashboard.html`
- `absolute_evaluation.html`
- `relative_evaluation.html`
- `admin_dashboard.html`
- `department_detail.html`
- `view_data.html`
- `manage_team.html`
- `manage_users.html`

## 3. 업로드 방법
1. 구글드라이브에서 "인사평가시스템" 폴더 열기
2. 파일들을 드래그 앤 드롭으로 업로드
3. templates 폴더는 폴더 그대로 업로드

## 4. 권한 설정
- 폴더 공유 설정: "링크가 있는 모든 사용자"로 설정
- 또는 필요한 사용자에게만 공유 