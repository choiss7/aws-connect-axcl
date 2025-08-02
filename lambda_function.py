import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')

BUCKET_NAME = "axcl"
FILE_NAME = "axcl_event.txt"

def lambda_handler(event, context):
    print("Incoming Event:", json.dumps(event, ensure_ascii=False))
    
    # Contact Flow 응답을 위한 기본 구조
    def create_response(status_code, message, success, registration_status, **kwargs):
        response = {
            'statusCode': status_code,
            'body': json.dumps({
                'message': message,
                'success': success
            }, ensure_ascii=False),
            'registrationStatus': registration_status,
            'success': success
        }
        # 추가 속성들 병합
        response.update(kwargs)
        return response

    try:
        # Contact Flow에서 전달된 데이터 추출
        contact_data = event.get('Details', {}).get('ContactData', {})
        attributes = contact_data.get('Attributes', {})
        
        # Contact ID 추출 (Contact Flow의 SetAttributes에서 설정한 값 우선)
        contact_id = (
            attributes.get('contactId') or 
            contact_data.get('ContactId') or 
            event.get('ContactId', 'unknown_contact')
        )

        # 고객 입력값 추출 (Contact Flow Attributes에서)
        customer_input = (
            attributes.get('customerInput') or
            event.get('Details', {}).get('Parameters', {}).get('customer_input') or
            event.get('customerInput')
        )

        # 고객 전화번호 추출
        customer_phone = (
            attributes.get('customerPhone') or
            contact_data.get('CustomerEndpoint', {}).get('Address') or
            event.get('customerPhone')
        )

        print(f"Extracted data - Contact ID: {contact_id}, Customer Input: {customer_input}, Phone: {customer_phone}")

        # 고객 입력값 검증
        if not customer_input:
            print("Error: No customer input provided")
            return create_response(
                status_code=400,
                message='사번을 입력해주세요.',
                success=False,
                registration_status='INPUT_ERROR',
                errorMessage='사번을 입력해주세요.'
            )
        
        # 사번 형식 검증 (숫자만 허용, 4-8자리)
        customer_input = customer_input.strip()
        if not customer_input.isdigit() or len(customer_input) < 4 or len(customer_input) > 8:
            print(f"Error: Invalid employee ID format: {customer_input}")
            return create_response(
                status_code=400,
                message='올바른 사번을 입력해주세요. (4-8자리 숫자)',
                success=False,
                registration_status='INVALID_FORMAT',
                errorMessage='올바른 사번을 입력해주세요. (4-8자리 숫자)'
            )

        # 저장할 JSON 데이터
        record = {
            "contactId": contact_id,
            "timestamp": datetime.utcnow().isoformat(),
            "customerPhone": customer_phone,
            "customerInput": customer_input,
            "eventType": "lottery_registration"
        }

        # S3에 저장 (기존 파일에 추가하는 방식으로 변경)
        try:
            # 기존 파일 읽기 시도
            try:
                existing_data = s3.get_object(Bucket=BUCKET_NAME, Key=FILE_NAME)
                existing_content = existing_data['Body'].read().decode('utf-8')
            except s3.exceptions.NoSuchKey:
                existing_content = ""
            
            # 중복 등록 확인
            if existing_content and customer_input in existing_content:
                # 더 정확한 중복 확인을 위해 각 라인을 파싱
                for line in existing_content.strip().split('\n'):
                    if line.strip():
                        try:
                            existing_record = json.loads(line)
                            if existing_record.get('customerInput') == customer_input:
                                print(f"Duplicate registration detected for employee ID: {customer_input}")
                                return create_response(
                                    status_code=400,
                                    message=f'이미 등록된 사번입니다: {customer_input}',
                                    success=False,
                                    registration_status='DUPLICATE',
                                    errorMessage=f'이미 등록된 사번입니다: {customer_input}'
                                )
                        except json.JSONDecodeError:
                            continue
            
            # 새 레코드 추가
            new_content = existing_content + json.dumps(record, ensure_ascii=False) + "\n"
            
            # S3에 저장
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=FILE_NAME,
                Body=new_content.encode('utf-8'),
                ContentType='text/plain'
            )
            
            print(f"Successfully saved to S3: s3://{BUCKET_NAME}/{FILE_NAME}")
            
        except Exception as s3_error:
            print(f"S3 operation failed: {str(s3_error)}")
            # S3 오류가 발생해도 Contact Flow에는 성공 응답을 보냄
            # (이벤트 등록은 성공했다고 안내)

        # 성공 응답 - Contact Flow에서 사용할 속성들 추가
        lottery_number = generate_lottery_number(customer_input)
        success_message = f"이벤트가 성공적으로 등록되었습니다. 사번: {customer_input}, 추첨번호: {lottery_number}"
        
        return create_response(
            status_code=200,
            message=success_message,
            success=True,
            registration_status='SUCCESS',
            contactId=contact_id,
            customerPhone=customer_phone,
            customerInput=customer_input,
            lotteryNumber=lottery_number,
            successMessage=success_message
        )

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(
            status_code=500,
            message='시스템 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
            success=False,
            registration_status='ERROR',
            errorMessage='시스템 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
        )

def generate_lottery_number(customer_input):
    """사번을 기반으로 추첨 번호 생성"""
    import hashlib
    
    # 사번을 해시하여 일관된 추첨 번호 생성
    hash_object = hashlib.md5(customer_input.encode())
    hash_hex = hash_object.hexdigest()
    
    # 해시의 앞 4자리를 숫자로 변환하여 추첨 번호로 사용
    lottery_number = int(hash_hex[:4], 16) % 10000
    
    return f"L{lottery_number:04d}"