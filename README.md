# AWS Connect AXCL 이벤트 등록 시스템

AWS Connect와 Lambda를 연동한 전화 기반 이벤트 등록 시스템입니다.

## 📁 프로젝트 구조

```
aws-connect-axcl/
├── contact-flows/              # Contact Flow 설정 이미지 및 JSON
├── lambda-functions/           # Lambda 함수 코드
│   └── connect_event_registration.py
├── scripts/                    # 배포 및 유틸리티 스크립트
│   ├── deploy.ps1             # PowerShell 배포 스크립트
│   └── requirements.txt       # Python 의존성
├── tests/                      # 테스트 코드
│   └── test_lambda_function.py
├── docs/                       # 문서화
│   └── contact-flow-setup.md  # Contact Flow 설정 가이드
├── .cursor/rules/              # Cursor AI 개발 룰
│   └── cursorruls.txt
└── README.md                   # 프로젝트 문서
```

## 📞 시스템 개요

이 시스템은 AWS Connect Contact Flow를 통해 고객으로부터 사번을 입력받아 이벤트에 등록하고, S3에 데이터를 저장하는 시스템입니다.

## 🏗️ 아키텍처

```
고객 전화 
    ↓
AWS Connect Contact Flow
    ↓ (사번 입력)
Lambda Function (이벤트 등록)
    ↓ (데이터 저장)
S3 (axcl/axcl_event.txt)
    ↓ (응답)
고객에게 추첨번호 안내
```

## 🔧 주요 구성요소

### 1. AWS Connect
- **Contact Flow**: 고객 입력 처리 및 Lambda 호출
- **Phone Number**: 이벤트 등록용 전화번호

### 2. Lambda Function (`connect_event_registration.py`)
- **입력 검증**: 4-8자리 숫자 사번 검증
- **중복 확인**: 동일 사번 재등록 방지
- **S3 저장**: 등록 데이터 저장
- **추첨번호 생성**: MD5 해시 기반 고유번호 생성

### 3. S3 Storage
- **Bucket**: `axcl`
- **File**: `axcl_event.txt`
- **Format**: `timestamp,phone,contact_id,employee_id`

## 📊 데이터 구조

### S3 저장 형식
```
2025-08-03T14:30:15.123Z,+821012345678,contact-123,1234
2025-08-03T14:35:22.456Z,+821087654321,contact-456,5678
```

### Lambda 응답 속성
- `registrationStatus`: SUCCESS | INPUT_ERROR | INVALID_FORMAT | DUPLICATE | ERROR
- `lotteryNumber`: L#### (성공시에만)
- `successMessage`: 성공 메시지 (성공시에만)
- `errorMessage`: 오류 메시지 (실패시에만)

## 🚀 빠른 시작

### 1. 의존성 설치
```powershell
# Python 의존성 설치
pip install -r scripts/requirements.txt
```

### 2. 테스트 실행
```powershell
# 단위 테스트
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=lambda-functions --cov-report=html
```

### 3. Lambda 함수 배포
```powershell
# 개발 환경 배포
.\scripts\deploy.ps1 -Environment dev

# 운영 환경 배포
.\scripts\deploy.ps1 -Environment prod
```

## 📋 Contact Flow 설정

자세한 Contact Flow 설정 방법은 [Contact Flow 설정 가이드](docs/contact-flow-setup.md)를 참조하세요.

### 핵심 설정 요약

1. **StoreUserInput**
   - MaxDigits: 8
   - Timeout: 5000ms
   - End digit: #

2. **Lambda Parameters**
   ```json
   {
     "inputValue": "$.StoredInput",
     "customerPhone": "$.CustomerEndpoint.Address",
     "contactId": "$.ContactId"
   }
   ```

3. **응답 분기**
   - 성공: `$.External.registrationStatus` == "SUCCESS"
   - 실패: `$.External.registrationStatus` != "SUCCESS"

## 🐛 문제해결

### 일반적인 문제들

#### 1. StoreUserInput 값이 전달되지 않음
**해결책**: Lambda 파라미터에서 `inputValue: $.StoredInput` 직접 설정

#### 2. Lambda Parameters가 비어있음
**해결책**: SetAttributes 블록 제거하고 Lambda 직접 연동

#### 3. DTMF 입력이 감지되지 않음
**해결책**: 
- 전화기 DTMF 설정 확인
- MaxDigits 충분히 설정 (8자리)
- Timeout 5초 이상 설정

### 로그 확인 방법

1. **Contact Flow 로그**: CloudWatch Logs
2. **Lambda 로그**: CloudWatch Logs
3. **등록 데이터**: S3 bucket `axcl/axcl_event.txt`

## 🧪 테스트 시나리오

### 성공 케이스
- 4자리 사번 입력: "1234" → 추첨번호 생성
- 8자리 사번 입력: "12345678" → 추첨번호 생성

### 실패 케이스
- 문자 포함: "abc123" → "올바른 사번을 입력해주세요"
- 중복 등록: 기존 사번 → "이미 등록된 사번입니다"
- 입력 없음: "" → "사번을 입력해주세요"

## 📈 모니터링

### CloudWatch 메트릭
- Lambda Duration
- Lambda Errors
- Contact Flow 성공률

### 알람 설정
- Lambda 에러율 > 5%
- 응답 시간 > 5초
- Contact Flow 실패율 > 10%

## 🔒 보안 고려사항

1. **IAM 권한**: Lambda 함수에 S3 최소 권한만 부여
2. **데이터 암호화**: S3 저장시 암호화 활성화
3. **로그 마스킹**: 민감정보 로그 출력 방지
4. **VPC**: 필요시 Lambda를 VPC에 배치

## 🛠️ 개발 환경

- **Python**: 3.9+
- **AWS SDK**: boto3
- **테스트**: pytest, moto
- **CI/CD**: GitHub Actions (예정)
- **모니터링**: CloudWatch

## 📚 관련 문서

- [Contact Flow 설정 가이드](docs/contact-flow-setup.md)
- [CloudWatch 로그 확인 가이드](docs/cloudwatch-logs-guide.md)
- [Cursor AI 개발 룰](.cursor/rules/cursorruls.txt)
- [AWS Connect 공식 문서](https://docs.aws.amazon.com/connect/)
- [AWS Lambda 공식 문서](https://docs.aws.amazon.com/lambda/)

<img width="1460" height="690" alt="image" src="https://github.com/user-attachments/assets/cc5af9e1-f3ac-4676-b852-6bbf00d1128f" />



## 🤝 기여 가이드

1. 코드 스타일: Black, flake8 준수
2. 테스트: 모든 변경사항에 대한 테스트 필수
3. 문서화: README 및 코드 주석 업데이트
4. 커밋: Conventional Commits 형식 사용

## 📄 라이선스

이 프로젝트는 AXCL 내부 사용을 위한 것입니다.

---

**개발팀**: AXCL 팀
**마지막 업데이트**: 2025-08-03  
**버전**: 2.0.0
