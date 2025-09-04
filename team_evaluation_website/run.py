#!/usr/bin/env python3
"""
인사평가 시스템 실행 스크립트
"""

import os
import sys
import subprocess

def check_python_version():
    """Python 버전 확인"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 이상이 필요합니다.")
        print(f"현재 버전: {sys.version}")
        return False
    print(f"✅ Python 버전 확인 완료: {sys.version}")
    return True

def install_requirements():
    """필요한 패키지 설치"""
    try:
        print("📦 필요한 패키지를 설치하고 있습니다...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 패키지 설치 완료")
        return True
    except subprocess.CalledProcessError:
        print("❌ 패키지 설치에 실패했습니다.")
        return False

def run_app():
    """Flask 애플리케이션 실행"""
    try:
        print("🚀 인사평가 시스템을 시작합니다...")
        print("🌐 웹 브라우저에서 http://localhost:5000 으로 접속하세요")
        print("⏹️  종료하려면 Ctrl+C를 누르세요")
        print("-" * 50)
        
        # Flask 애플리케이션 실행
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except ImportError as e:
        print(f"❌ 모듈을 불러올 수 없습니다: {e}")
        print("requirements.txt의 패키지들이 제대로 설치되었는지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 애플리케이션 실행 중 오류가 발생했습니다: {e}")
        return False

def main():
    """메인 함수"""
    print("=" * 50)
    print("🏢 인사평가 시스템")
    print("=" * 50)
    
    # Python 버전 확인
    if not check_python_version():
        return
    
    # 현재 디렉토리 확인
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    
    # requirements.txt 존재 확인
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt 파일을 찾을 수 없습니다.")
        return
    
    # 패키지 설치
    if not install_requirements():
        return
    
    # 애플리케이션 실행
    run_app()

if __name__ == "__main__":
    main() 