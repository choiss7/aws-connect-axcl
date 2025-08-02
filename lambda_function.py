import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')

BUCKET_NAME = "axcl"
FILE_NAME = "axcl_event.txt"

def lambda_handler(event, context):
    print("Incoming Event:", json.dumps(event, ensure_ascii=False))

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
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'No customer input provided',
                    'success': False
                }, ensure_ascii=False)
            }

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

        # 성공 응답
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"이벤트가 성공적으로 등록되었습니다. 사번: {customer_input}",
                "success": True,
                "lottery_number": generate_lottery_number(customer_input)
            }, ensure_ascii=False),
            "contactId": contact_id,
            "customerPhone": customer_phone,
            "customerInput": customer_input
        }

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': '시스템 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
                'success': False
            }, ensure_ascii=False)
        }

def generate_lottery_number(customer_input):
    """사번을 기반으로 추첨 번호 생성"""
    import hashlib
    
    # 사번을 해시하여 일관된 추첨 번호 생성
    hash_object = hashlib.md5(customer_input.encode())
    hash_hex = hash_object.hexdigest()
    
    # 해시의 앞 4자리를 숫자로 변환하여 추첨 번호로 사용
    lottery_number = int(hash_hex[:4], 16) % 10000
    
    return f"L{lottery_number:04d}"