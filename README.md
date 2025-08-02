# AWS Connect AXCL 이벤트 등록 시스템

AWS Connect와 Lambda를 연동한 전화 기반 이벤트 등록 시스템입니다.

## 시스템 개요

이 시스템은 AWS Connect Contact Flow를 통해 고객으로부터 사번을 입력받아 이벤트에 등록하고, S3에 데이터를 저장하는 시스템입니다.

## 아키텍처

```
고객 전화 → AWS Connect → Contact Flow → Lambda Function → S3 Storage
```

## 주요 구성 요소

### 1. AWS Connect Contact Flow
- 고객으로부터 사번 입력 수집
- 입력값 검증 및 Lambda 함수 호출
- 응답 메시지 전달

### 2. Lambda Function (`lambda_function.py`)
- Contact Flow에서 전달받은 데이터 처리
- 고객 정보 추출 및 검증
- S3에 이벤트 데이터 저장
- 추첨 번호 생성 및 응답

### 3. S3 Storage
- 버킷명: `axcl`
- 파일명: `axcl_event.txt`
- 이벤트 등록 데이터를 JSON 형태로 저장

## 데이터 구조

저장되는 데이터 형식:
```json
{
    "contactId": "contact-uuid",
    "timestamp": "2024-01-01T00:00:00.000000",
    "customerPhone": "+82-10-1234-5678",
    "customerInput": "사번",
    "eventType": "lottery_registration"
}
```

## Lambda 함수 주요 기능

1. **데이터 추출**: Contact Flow에서 전달된 고객 정보 추출
2. **입력 검증**: 사번 입력값 유효성 검사 (4-8자리 숫자)
3. **중복 확인**: 이미 등록된 사번 중복 등록 방지
4. **S3 저장**: 이벤트 데이터를 S3에 추가 저장
5. **추첨 번호 생성**: 사번 기반 해시를 이용한 고유 추첨 번호 생성
6. **표준화된 응답**: Contact Flow에서 사용하기 쉬운 표준화된 응답 형식
7. **에러 처리**: 시스템 오류 및 S3 저장 실패에 대한 적절한 처리

## 설정 요구사항

### AWS Lambda
- Runtime: Python 3.9+
- IAM Role: S3 읽기/쓰기 권한 필요
- Environment Variables: 필요시 BUCKET_NAME 설정

### AWS Connect
- Contact Flow에서 Lambda 함수 연동 설정
- 고객 입력을 Lambda로 전달하는 Invoke AWS Lambda 블록 구성

### S3 Bucket
- 버킷명: `axcl`
- 적절한 접근 권한 설정

## 사용법

1. AWS Connect에서 Contact Flow 설정
2. Lambda 함수 배포 및 Connect와 연동
3. S3 버킷 생성 및 권한 설정
4. 시스템 테스트

## Lambda 응답 속성

Contact Flow에서 사용할 수 있는 Lambda 응답 속성들:

### 성공 시
- `registrationStatus`: "SUCCESS"
- `contactId`: Contact ID
- `customerPhone`: 고객 전화번호
- `customerInput`: 입력된 사번
- `lotteryNumber`: 생성된 추첨번호 (L0001-L9999)
- `successMessage`: 성공 메시지

### 에러 시
- `registrationStatus`: "INPUT_ERROR" | "INVALID_FORMAT" | "DUPLICATE" | "ERROR"
- `errorMessage`: 에러 메시지
- `success`: false

## 추첨 번호 생성 로직

사번을 MD5 해시로 변환한 후, 앞 4자리를 16진수에서 10진수로 변환하여 10000으로 나눈 나머지를 사용합니다. 형식: `L0001` - `L9999`

## Contact Flow 설정 가이드

### 필수 설정 순서

1. **StoreUserInput 블록**: 고객으로부터 사번 입력 받기
2. **SetAttributes 블록**: 입력된 값을 속성으로 저장
   ```
   키: customerInput
   값: $.StoredInput
   ```
3. **AWS Lambda 함수 호출 블록**: 파라미터 설정
   ```
   customerInput: $.Attributes.customerInput
   customerPhone: $.CustomerEndpoint.Address
   contactId: $.ContactId
   ```

### 중요 주의사항
- **SetAttributes 블록이 Lambda 호출 전에 반드시 실행되어야 함**
- **StoreUserInput 결과는 $.StoredInput으로 접근**
- **Lambda에서는 $.Attributes.customerInput으로 전달받음**

### 🚨 SetAttributes가 작동하지 않는 경우

만약 SetAttributes에서 `customerInput = ""` (빈값)이 설정되는 경우:

**즉시 해결 방법**: Lambda 파라미터에서 직접 설정
```
키: StoredInput
값: $.StoredInput

또는

키: userInput  
값: $.StoredInput
```

이렇게 하면 SetAttributes 없이도 직접 사용자 입력을 Lambda로 전달할 수 있습니다.

## Contact Flow 연동 예시

Lambda 함수 호출 후 응답 속성을 사용하는 방법:

1. **성공 분기**: `$.External.registrationStatus` == "SUCCESS"
2. **에러 분기**: `$.External.registrationStatus` != "SUCCESS"
3. **메시지 출력**: `$.External.successMessage` 또는 `$.External.errorMessage`
4. **추첨번호 안내**: `$.External.lotteryNumber`

<img width="1051" height="711" alt="image" src="https://github.com/user-attachments/assets/4e0b61c1-b731-4a02-9efc-dff4af38078d" />

<img width="1573" height="835" alt="image" src="https://github.com/user-attachments/assets/1aaf24ba-06f1-4297-9d00-67e6df19945f" />


<img width="1839" height="829" alt="image" src="https://github.com/user-attachments/assets/982c5969-a559-4e08-9815-18086fb4be9f" />


