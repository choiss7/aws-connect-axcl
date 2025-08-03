#!/usr/bin/env python3
"""
AWS Connect AXCL Lambda 함수 배포 후 테스트

실제 AWS 환경에서 사용하기 전에 로컬에서 다양한 시나리오를 테스트합니다.
"""

import json
import sys
import os

# Lambda 함수 import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lambda-functions'))
from connect_event_registration import lambda_handler

def test_deployment():
    """배포 후 테스트 시나리오"""
    
    print("🚀 AWS Connect AXCL Lambda 함수 배포 테스트")
    print("=" * 60)
    
    # 테스트 시나리오 1: 정상적인 등록 (새로운 사번)
    print("\n📋 테스트 1: 정상적인 등록 프로세스")
    event1 = {
        "Details": {
            "ContactData": {
                "ContactId": "test-deploy-001",
                "CustomerEndpoint": {
                    "Address": "+821012345678"
                }
            },
            "Parameters": {
                "inputValue": "9999"  # 새로운 사번
            }
        }
    }
    
    result1 = lambda_handler(event1, None)
    print(f"결과: {json.dumps(result1, ensure_ascii=False, indent=2)}")
    
    # 테스트 시나리오 2: 잘못된 입력 형식
    print("\n📋 테스트 2: 잘못된 입력 형식")
    event2 = {
        "Details": {
            "Parameters": {
                "inputValue": "abc123"  # 문자 포함
            }
        }
    }
    
    result2 = lambda_handler(event2, None)
    print(f"결과: {json.dumps(result2, ensure_ascii=False, indent=2)}")
    
    # 테스트 시나리오 3: 입력값 누락
    print("\n📋 테스트 3: 입력값 누락")
    event3 = {
        "Details": {
            "Parameters": {}
        }
    }
    
    result3 = lambda_handler(event3, None)
    print(f"결과: {json.dumps(result3, ensure_ascii=False, indent=2)}")
    
    # 테스트 시나리오 4: 중복 등록 (기존 사번)
    print("\n📋 테스트 4: 중복 등록 시도")
    event4 = {
        "Details": {
            "Parameters": {
                "inputValue": "1234"  # 기존에 등록된 사번
            }
        }
    }
    
    result4 = lambda_handler(event4, None)
    print(f"결과: {json.dumps(result4, ensure_ascii=False, indent=2)}")
    
    # 테스트 결과 요약
    print("\n" + "=" * 60)
    print("🎯 테스트 결과 요약")
    
    test_results = [
        ("정상 등록", result1["registrationStatus"] == "SUCCESS"),
        ("잘못된 형식", result2["registrationStatus"] == "INVALID_FORMAT"),
        ("입력값 누락", result3["registrationStatus"] == "INPUT_ERROR"),
        ("중복 등록", result4["registrationStatus"] == "DUPLICATE"),
    ]
    
    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    all_passed = all(result[1] for result in test_results)
    
    if all_passed:
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        print("Lambda 함수가 배포 준비 완료 상태입니다.")
        return True
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        print("배포 전에 문제를 해결해주세요.")
        return False

def deployment_checklist():
    """배포 체크리스트"""
    print("\n📋 배포 체크리스트")
    print("-" * 30)
    
    checklist = [
        "✅ Python 문법 검사 완료",
        "✅ 단위 테스트 실행 완료",
        "✅ Lambda 패키지 생성 완료",
        "⏳ AWS 자격 증명 설정",
        "⏳ Lambda 함수 생성/업데이트",
        "⏳ IAM 권한 설정 (S3 읽기/쓰기)",
        "⏳ Contact Flow 연동",
        "⏳ 실제 전화 테스트"
    ]
    
    for item in checklist:
        print(item)
    
    print("\n💡 다음 단계:")
    print("1. AWS CLI 설정 및 자격 증명")
    print("2. Lambda 함수 배포:")
    print("   aws lambda update-function-code --function-name axcl-event-registration --zip-file fileb://axcl-event-registration-dev.zip")
    print("3. Contact Flow에서 Lambda 함수 테스트")

if __name__ == "__main__":
    test_success = test_deployment()
    deployment_checklist()
    
    if test_success:
        print(f"\n🚀 배포 패키지 준비 완료: axcl-event-registration-dev.zip")
        exit(0)
    else:
        exit(1)