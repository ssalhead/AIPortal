#!/usr/bin/env python3
"""
API 키 설정 및 검증 도구
"""

import os
import sys
from pathlib import Path

def check_env_file():
    """환경 변수 파일 확인 및 생성"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("📄 .env.example을 복사하여 .env 파일을 생성합니다...")
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ .env 파일이 생성되었습니다.")
        else:
            print("❌ .env.example 파일이 없습니다.")
            return False
    
    return True

def get_api_key_info():
    """API 키 정보 및 가이드"""
    return {
        "OPENAI_API_KEY": {
            "name": "OpenAI API",
            "url": "https://platform.openai.com/api-keys",
            "models": ["gpt-4", "gpt-3.5-turbo"],
            "required": False
        },
        "ANTHROPIC_API_KEY": {
            "name": "Anthropic Claude API",
            "url": "https://console.anthropic.com/",
            "models": ["claude-3-haiku", "claude-3-sonnet", "claude-3-opus"],
            "required": True  # 주력 모델
        },
        "GOOGLE_API_KEY": {
            "name": "Google AI (Gemini)",
            "url": "https://makersuite.google.com/app/apikey",
            "models": ["gemini-pro", "gemini-pro-vision"],
            "required": True  # 주력 모델
        }
    }

def check_api_keys():
    """현재 설정된 API 키 확인"""
    from app.core.config import settings
    
    api_info = get_api_key_info()
    results = {}
    
    print("\n🔑 API 키 설정 상태:")
    print("=" * 50)
    
    for key, info in api_info.items():
        value = getattr(settings, key, None)
        is_set = value and value.strip() and value != ""
        status = "✅ 설정됨" if is_set else "❌ 미설정"
        required = "필수" if info["required"] else "선택"
        
        print(f"{info['name']:20} | {status:10} | {required}")
        print(f"  └─ 모델: {', '.join(info['models'])}")
        print(f"  └─ 발급: {info['url']}")
        print()
        
        results[key] = is_set
    
    return results

def test_api_connections():
    """API 연결 테스트"""
    print("\n🧪 API 연결 테스트:")
    print("=" * 50)
    
    # OpenAI 테스트
    try:
        from app.core.config import settings
        if settings.OPENAI_API_KEY:
            print("OpenAI API 테스트...")
            # 실제 API 호출은 비용이 발생하므로 키 형식만 검증
            if settings.OPENAI_API_KEY.startswith("sk-"):
                print("  ✅ OpenAI API 키 형식 올바름")
            else:
                print("  ⚠️  OpenAI API 키 형식이 올바르지 않을 수 있습니다")
        else:
            print("  ❌ OpenAI API 키 미설정")
    except Exception as e:
        print(f"  ❌ OpenAI 설정 오류: {e}")
    
    # Anthropic 테스트
    try:
        if settings.ANTHROPIC_API_KEY:
            print("\nAnthropic API 테스트...")
            if settings.ANTHROPIC_API_KEY.startswith("sk-ant-"):
                print("  ✅ Anthropic API 키 형식 올바름")
            else:
                print("  ⚠️  Anthropic API 키 형식이 올바르지 않을 수 있습니다")
        else:
            print("  ❌ Anthropic API 키 미설정")
    except Exception as e:
        print(f"  ❌ Anthropic 설정 오류: {e}")
    
    # Google 테스트
    try:
        if settings.GOOGLE_API_KEY:
            print("\nGoogle AI API 테스트...")
            if len(settings.GOOGLE_API_KEY) > 30:  # Google API 키는 긴 문자열
                print("  ✅ Google API 키 형식 올바름")
            else:
                print("  ⚠️  Google API 키 형식이 올바르지 않을 수 있습니다")
        else:
            print("  ❌ Google API 키 미설정")
    except Exception as e:
        print(f"  ❌ Google 설정 오류: {e}")

def setup_mock_environment():
    """Mock 환경 설정 (API 키 없이 테스트용)"""
    print("\n🔧 Mock 환경 설정:")
    print("=" * 50)
    
    mock_env = """
# Mock LLM 설정 (테스트용)
MOCK_LLM_ENABLED=true
MOCK_RESPONSES_ENABLED=true

# 실제 API 키가 없을 때 대체 응답
FALLBACK_RESPONSE="안녕하세요! 현재 Mock 모드로 실행 중입니다. 실제 LLM 응답을 받으려면 API 키를 설정해주세요."
"""
    
    env_file = Path(".env")
    with open(env_file, "a") as f:
        f.write(mock_env)
    
    print("✅ Mock 환경 설정이 .env에 추가되었습니다.")
    print("📝 실제 API를 사용하려면 다음 키들을 .env 파일에 설정하세요:")
    
    api_info = get_api_key_info()
    for key, info in api_info.items():
        if info["required"]:
            print(f"  {key}=your_api_key_here")
    
def interactive_setup():
    """대화형 설정"""
    print("\n🛠️  대화형 API 키 설정:")
    print("=" * 50)
    
    api_info = get_api_key_info()
    env_updates = {}
    
    for key, info in api_info.items():
        required_text = "(필수)" if info["required"] else "(선택)"
        print(f"\n{info['name']} {required_text}")
        print(f"발급 URL: {info['url']}")
        
        current_key = os.getenv(key, "")
        if current_key:
            print(f"현재 설정: {current_key[:10]}...")
            
        new_key = input(f"{key} 입력 (Enter로 건너뛰기): ").strip()
        
        if new_key:
            env_updates[key] = new_key
    
    if env_updates:
        print("\n📝 .env 파일 업데이트 중...")
        
        # .env 파일 읽기
        env_file = Path(".env")
        lines = []
        if env_file.exists():
            with open(env_file, 'r') as f:
                lines = f.readlines()
        
        # 키 업데이트
        for key, value in env_updates.items():
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"{key}={value}\n")
        
        # 파일 저장
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ {len(env_updates)}개 키가 업데이트되었습니다.")
    else:
        print("변경사항이 없습니다.")

def main():
    """메인 함수"""
    print("""
╔══════════════════════════════════════════╗
║        AI 포탈 API 키 설정 도구          ║
╚══════════════════════════════════════════╝
""")
    
    # 환경 파일 확인
    if not check_env_file():
        sys.exit(1)
    
    # 현재 상태 확인
    try:
        results = check_api_keys()
    except ImportError as e:
        print(f"⚠️  설정 모듈 로드 실패: {e}")
        print("패키지 설치 후 다시 시도해주세요.")
        return
    
    # API 연결 테스트
    test_api_connections()
    
    # 메뉴
    print("\n📋 옵션:")
    print("1. 대화형 API 키 설정")
    print("2. Mock 환경 설정 (API 키 없이 테스트)")
    print("3. 종료")
    
    choice = input("\n선택 (1-3): ").strip()
    
    if choice == "1":
        interactive_setup()
    elif choice == "2":
        setup_mock_environment()
    elif choice == "3":
        print("설정을 완료했습니다.")
    else:
        print("올바른 옵션을 선택해주세요.")

if __name__ == "__main__":
    main()