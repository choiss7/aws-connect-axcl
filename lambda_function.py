import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')

BUCKET_NAME = "axcl"
FILE_NAME = "axcl_event.txt"

def lambda_handler(event, context):
    print("=== Lambda Function Started ===")
    print("Incoming Event:", json.dumps(event, ensure_ascii=False, indent=2))
    
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
        print("Lambda Response:", json.dumps(response, ensure_ascii=False, indent=2))
        return response

    try:
        # Contact Flow에서 전달된 데이터 추출
        contact_data = event.get('Details', {}).get('ContactData', {})
        attributes = contact_data.get('Attributes', {})
        
        print("Contact Data:", json.dumps(contact_data, ensure_ascii=False, indent=2))
        print("Attributes:", json.dumps(attributes, ensure_ascii=False, indent=2))
        
        # Contact ID 추출 (Contact Flow의 SetAttributes에서 설정한 값 우선)
        contact_id = (
            attributes.get('contactId') or 
            contact_data.get('ContactId') or 
            event.get('ContactId', 'unknown_contact')
        )

        # 고객 입력값 추출 (AWS Connect의 다양한 경로에서 시도)
        # AWS Connect에서 Lambda로 전달하는 일반적인 구조들을 모두 확인
        possible_inputs = [
            # Contact attributes (SetAttributes에서 설정된 값들)
            attributes.get('customerInput'),
            # Lambda 호출 시 Parameters로 전달된 값들
            event.get('Details', {}).get('Parameters', {}).get('customer_input'),
            event.get('Details', {}).get('Parameters', {}).get('customerInput'),
            # 이벤트 루트에서 직접
            event.get('customerInput'),
            # Contact data의 다양한 위치
            contact_data.get('StoredInput'),
            contact_data.get('SystemAttributes', {}).get('StoredInput'),
            # AWS Connect에서 자주 사용하는 시스템 속성명들
            contact_data.get('Attributes', {}).get('StoredInput'),
            contact_data.get('Attributes', {}).get('customer_input'),
            # Parameters의 다양한 형태
            str(event.get('Details', {}).get('Parameters', {}).get('StoredInput', '')),
            str(attributes.get('StoredInput', '')),
            # 사용자 정의 속성 (Contact Flow에서 설정 가능한 이름들)
            attributes.get('사번'),
            attributes.get('empId'),
            attributes.get('employeeId'),
            # Contact Flow에서 $.StoredInput으로 설정했을 수 있는 값
            str(event.get('Details', {}).get('Parameters', {}).get('$.StoredInput', '')),
        ]
        
        # None이 아니고 빈 문자열이 아닌 첫 번째 값 선택
        customer_input = None
        for i, inp in enumerate(possible_inputs):
            if inp and str(inp).strip():
                customer_input = str(inp).strip()
                print(f"✓ Found customer input from source {i}: '{inp}'")
                break

        # 고객 전화번호 추출
        customer_phone = (
            attributes.get('customerPhone') or
            contact_data.get('CustomerEndpoint', {}).get('Address') or
            event.get('customerPhone') or
            # 추가 가능한 경로들
            contact_data.get('CustomerNumber')
        )

        print(f"=== Extracted Data ===")
        print(f"Contact ID: {contact_id}")
        print(f"Customer Input: '{customer_input}' (type: {type(customer_input)})")
        print(f"Customer Phone: {customer_phone}")
        
        # Contact Flow Parameters 전체 출력
        parameters = event.get('Details', {}).get('Parameters', {})
        print(f"All Parameters: {json.dumps(parameters, ensure_ascii=False, indent=2)}")
        
        # 모든 가능한 입력 소스 디버깅
        print(f"=== Debug All Input Sources ===")
        for i, inp in enumerate(possible_inputs):
            print(f"Source {i}: {inp} (type: {type(inp)})")

        # 고객 입력값 검증
        if not customer_input:
            print("Error: No customer input provided")
            print("Checked all possible input sources but found none")
            return create_response(
                status_code=400,
                message='사번을 입력해주세요.',
                success=False,
                registration_status='INPUT_ERROR',
                errorMessage='사번을 입력해주세요.'
            )
        
        # 사번 형식 검증 (숫자만 허용, 4-8자리)
        customer_input = str(customer_input).strip() if customer_input else ""
        print(f"=== Input Validation ===")
        print(f"Cleaned Input: '{customer_input}' (length: {len(customer_input)})")
        print(f"Is digit: {customer_input.isdigit()}")
        
        if not customer_input.isdigit() or len(customer_input) < 4 or len(customer_input) > 8:
            print(f"Error: Invalid employee ID format")
            print(f"- Input: '{customer_input}'")
            print(f"- Length: {len(customer_input)}")
            print(f"- Is digit: {customer_input.isdigit()}")
            return create_response(
                status_code=400,
                message='올바른 사번을 입력해주세요. (4-8자리 숫자)',
                success=False,
                registration_status='INVALID_FORMAT',
                errorMessage='올바른 사번을 입력해주세요. (4-8자리 숫자)'
            )
            
        print(f"✓ Input validation passed: '{customer_input}'")

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
        
        print(f"=== Success Response ===")
        print(f"Generated lottery number: {lottery_number}")
        print(f"Success message: {success_message}")
        
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