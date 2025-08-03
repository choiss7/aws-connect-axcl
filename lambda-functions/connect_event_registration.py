"""
AWS Connect AXCL 이벤트 등록 Lambda 함수

이 함수는 AWS Connect Contact Flow에서 사용자의 사번 입력을 받아
S3에 저장하고 추첨번호를 생성하여 응답하는 기능을 제공합니다.

Author: AXCL Team
Version: 1.0.0
Last Updated: 2025-08-03
"""

import json
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import hashlib

# AWS 서비스 클라이언트 초기화
s3 = boto3.client('s3')

# 설정 상수
BUCKET_NAME = "axcl"
FILE_NAME = "axcl_event.txt"


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Connect Contact Flow Lambda Handler
    
    Args:
        event: Contact Flow 이벤트 데이터
        context: Lambda 실행 컨텍스트
        
    Returns:
        Contact Flow 응답 딕셔너리
    """
    try:
        print(f"=== 📞 AWS Connect AXCL 이벤트 등록 시작 ===")
        print(f"Incoming Event: {json.dumps(event, ensure_ascii=False)}")
        
        # Contact 데이터 추출
        contact_data = extract_contact_data(event)
        customer_input = contact_data.get('customer_input')
        customer_phone = contact_data.get('customer_phone')
        contact_id = contact_data.get('contact_id')
        
        # 입력값 검증
        if not customer_input:
            print("❌ Error: No customer input provided")
            return create_response("INPUT_ERROR", None, "사번을 입력해주세요.")
        
        if not customer_input.isdigit() or len(customer_input) < 4 or len(customer_input) > 8:
            print(f"❌ Validation failed: {customer_input}")
            return create_response("INVALID_FORMAT", None, "올바른 사번을 입력해주세요. (4-8자리 숫자)")
        
        # 중복 등록 확인
        if is_duplicate_registration(customer_input):
            print(f"❌ Duplicate registration: {customer_input}")
            return create_response("DUPLICATE", None, "이미 등록된 사번입니다.")
        
        # S3에 데이터 저장
        save_to_s3(customer_input, customer_phone, contact_id)
        
        # 추첨번호 생성
        lottery_number = generate_lottery_number(customer_input)
        
        print(f"✅ Registration successful: {customer_input} -> {lottery_number}")
        return create_response("SUCCESS", lottery_number, f"등록이 완료되었습니다. 추첨번호: {lottery_number}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return create_response("ERROR", None, "시스템 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


def extract_contact_data(event: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Contact Flow 이벤트에서 필요한 데이터 추출"""
    # 이벤트 형식 감지
    is_simple_format = 'Details' not in event
    
    if is_simple_format:
        lambda_parameters = event
        contact_data = {}
        attributes = {}
    else:
        contact_data = event.get('Details', {}).get('ContactData', {})
        attributes = contact_data.get('Attributes', {})
        lambda_parameters = event.get('Details', {}).get('Parameters', {})
    
    # 다중 경로에서 입력값 추출
    possible_inputs = [
        lambda_parameters.get('inputValue'),
        lambda_parameters.get('customerInput'),
        lambda_parameters.get('StoredInput'),
        lambda_parameters.get('userInput'),
        attributes.get('customerInput'),
        contact_data.get('StoredInput'),
    ]
    
    customer_input = None
    for inp in possible_inputs:
        if inp and str(inp).strip():
            customer_input = str(inp).strip()
            break
    
    # 연락처 번호 추출
    customer_phone = (
        contact_data.get('CustomerEndpoint', {}).get('Address') or
        lambda_parameters.get('customerPhone') or
        event.get('customerPhone')
    )
    
    # Contact ID 추출
    contact_id = (
        contact_data.get('ContactId') or
        event.get('contactId') or
        event.get('ContactId')
    )
    
    return {
        'customer_input': customer_input,
        'customer_phone': customer_phone,
        'contact_id': contact_id
    }


def is_duplicate_registration(customer_input: str) -> bool:
    """중복 등록 확인"""
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_NAME)
        content = response['Body'].read().decode('utf-8')
        
        for line in content.strip().split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 4 and parts[3].strip() == customer_input:
                    return True
        return False
        
    except s3.exceptions.NoSuchKey:
        return False
    except Exception:
        return False


def save_to_s3(customer_input: str, customer_phone: str, contact_id: str) -> None:
    """S3에 등록 데이터 저장"""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 새 등록 라인 생성
    new_line = f"{timestamp},{customer_phone or 'UNKNOWN'},{contact_id or 'UNKNOWN'},{customer_input}\n"
    
    try:
        # 기존 내용 읽기
        try:
            response = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_NAME)
            existing_content = response['Body'].read().decode('utf-8')
        except s3.exceptions.NoSuchKey:
            existing_content = ""
        
        # 새 내용 추가하여 저장
        updated_content = existing_content + new_line
        s3.put_object(Bucket=BUCKET_NAME, Key=FILE_NAME, Body=updated_content.encode('utf-8'))
        
        print(f"💾 S3 저장 성공: {customer_input}")
        
    except Exception as e:
        print(f"❌ S3 저장 실패: {str(e)}")
        raise


def generate_lottery_number(customer_input: str) -> str:
    """사번을 기반으로 추첨번호 생성"""
    hash_object = hashlib.md5(customer_input.encode())
    hash_hex = hash_object.hexdigest()
    number_part = ''.join(filter(str.isdigit, hash_hex))
    
    if len(number_part) >= 4:
        lottery_digits = number_part[:4]
    else:
        lottery_digits = (number_part + "0000")[:4]
    
    return f"L{lottery_digits}"


def create_response(
    status: str, 
    lottery_number: Optional[str] = None, 
    message: str = ""
) -> Dict[str, Any]:
    """Contact Flow 응답 생성"""
    return {
        "registrationStatus": status,
        "lotteryNumber": lottery_number or "",
        "successMessage": message if status == "SUCCESS" else "",
        "errorMessage": message if status != "SUCCESS" else ""
    }


# 로컬 테스트용 (개발 환경에서만 사용)
if __name__ == "__main__":
    # 테스트 이벤트
    test_event = {
        "Details": {
            "ContactData": {
                "ContactId": "test-contact-123",
                "CustomerEndpoint": {
                    "Address": "+821012345678"
                }
            },
            "Parameters": {
                "inputValue": "1234"
            }
        }
    }
    
    print("=== 로컬 테스트 시작 ===")
    result = lambda_handler(test_event, None)
    print(f"결과: {json.dumps(result, ensure_ascii=False, indent=2)}")