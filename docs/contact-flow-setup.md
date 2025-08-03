# AWS Connect Contact Flow 설정 가이드

## 📞 AXCL 이벤트 등록 Contact Flow 구성

### 개요
이 문서는 AWS Connect에서 AXCL 이벤트 등록을 위한 Contact Flow 설정 방법을 설명합니다.

### 전체 플로우 구조

```
Entry Point
    ↓
Set Logging Behavior
    ↓
Play Prompt (안내 멘트)
    ↓
Store User Input (사번 입력 받기)
    ↓
Invoke Lambda Function (등록 처리)
    ↓
Check Lambda Response
    ├── Success → Play Success Message
    └── Error → Play Error Message
    ↓
Disconnect
```

## 🔧 상세 설정 가이드

### 1. Set Logging Behavior
**목적**: Contact Flow 로그 활성화
```json
{
  "LoggingBehavior": "Enable",
  "LogLevel": "INFO"
}
```

### 2. Play Prompt (안내 멘트)
**목적**: 사용자에게 안내 메시지 제공

**설정값**:
- **Text-to-speech**: "안녕하세요. AXCL 이벤트 등록을 위해 사번 4자리를 입력해주세요."
- **Voice**: Korean - Seoyeon
- **SSML**: 
```xml
<speak>
안녕하세요. <break time="0.5s"/>
AXCL 이벤트 등록을 위해 사번 <emphasis level="strong">4자리</emphasis>를 입력해주세요.
</speak>
```

### 3. Store User Input ⭐ **핵심 설정**
**목적**: 사용자로부터 사번 입력 받기

**중요 설정값**:
- **Text-to-speech**: "사번을 입력 후 샵(#)을 눌러주세요"
- **Max digits**: `8` (4-8자리 허용)
- **Timeout**: `5000ms` (5초)
- **End digit**: `#`
- **Encrypted**: `No`

**⚠️ 주의사항**:
- DTMF 톤이 정상 전송되는지 확인
- 휴대폰에서 숫자 키패드 사용 시 긴 터치 방지
- 일반 전화기 사용 권장

### 4. Invoke Lambda Function ⭐ **핵심 설정**
**목적**: Lambda 함수를 호출하여 등록 처리

**Function ARN**: `arn:aws:lambda:ap-northeast-2:계정번호:function:axcl-event-registration`

**Parameters** (필수):
```json
{
  "inputValue": "$.StoredInput",
  "customerPhone": "$.CustomerEndpoint.Address",
  "contactId": "$.ContactId"
}
```

**⚠️ 문제해결**:
만약 `$.StoredInput`이 작동하지 않는 경우 대안:
- `$.StoredCustomerInput`
- `$.StoredUserInput`
- `$.CustomerInput`
- `$.UserInput`

**Timeout**: `8000ms` (8초)

### 5. Check Lambda Response
**목적**: Lambda 응답에 따른 분기 처리

**Conditions**:
- **Success**: `$.External.registrationStatus` Equals `SUCCESS`
- **Error**: `$.External.registrationStatus` Not Equals `SUCCESS`

### 6-A. Play Success Message
**목적**: 등록 성공 시 안내

**Text-to-speech**: `$.External.successMessage`
- 동적 메시지 예시: "등록이 완료되었습니다. 추첨번호는 L1234입니다."

### 6-B. Play Error Message  
**목적**: 등록 실패 시 안내

**Text-to-speech**: `$.External.errorMessage`
- 동적 메시지 예시:
  - "올바른 사번을 입력해주세요. (4-8자리 숫자)"
  - "이미 등록된 사번입니다."
  - "시스템 오류가 발생했습니다."

## 🐛 문제해결 가이드

### 문제 1: StoreUserInput에서 입력값이 전달되지 않음
**증상**: Lambda에서 `inputValue`가 빈 문자열
**해결책**:
1. StoreUserInput의 MaxDigits를 충분히 설정 (8자리)
2. Timeout을 5초 이상으로 설정
3. 전화기 DTMF 설정 확인
4. Contact Flow 로그에서 StoreUserInput Results 확인

### 문제 2: Lambda Parameters가 비어있음
**증상**: Lambda에서 Parameters = {}
**해결책**:
1. Lambda Function 블록의 Parameters 설정 재확인
2. SetAttributes 블록 제거하고 직접 연동
3. 시스템 변수 `$.StoredInput` 대신 다른 변수 시도

### 문제 3: Lambda 응답이 Contact Flow에 반영되지 않음
**증상**: 성공/실패 분기가 작동하지 않음
**해결책**:
1. Lambda 응답 구조 확인 (`registrationStatus`, `successMessage`, `errorMessage`)
2. Check conditions에서 `$.External.registrationStatus` 경로 확인
3. Lambda 함수 실행 권한 확인

## 📊 성공적인 로그 예시

### StoreUserInput 성공
```json
{
  "ContactId": "12345678-1234-1234-1234-123456789012",
  "Type": "StoreUserInput",
  "Results": "1234",
  "Timestamp": "2025-08-03T14:30:00.000Z"
}
```

### Lambda 호출 성공
```json
{
  "ContactId": "12345678-1234-1234-1234-123456789012",
  "Type": "Lambda",
  "Parameters": {
    "inputValue": "1234",
    "customerPhone": "+821012345678",
    "contactId": "12345678-1234-1234-1234-123456789012"
  },
  "Results": {
    "registrationStatus": "SUCCESS",
    "lotteryNumber": "L3244",
    "successMessage": "등록이 완료되었습니다. 추첨번호: L3244",
    "errorMessage": ""
  },
  "ExecutionTime": "306ms"
}
```

## 🚀 배포 체크리스트

- [ ] Set Logging Behavior 활성화
- [ ] Play Prompt SSML 설정
- [ ] StoreUserInput MaxDigits = 8, Timeout = 5000ms
- [ ] Lambda Function ARN 정확히 입력
- [ ] Lambda Parameters 올바르게 설정
- [ ] Success/Error 분기 조건 정확히 설정
- [ ] 동적 메시지 경로 확인 (`$.External.*`)
- [ ] Contact Flow 게시 (Publish)
- [ ] 전화번호에 Contact Flow 할당
- [ ] 실제 전화 테스트 수행

## 📞 테스트 시나리오

### 성공 케이스
1. 전화 연결
2. 안내 멘트 듣기
3. 4자리 사번 입력 (예: 1234)
4. `#` 키 누르기
5. "등록이 완료되었습니다. 추첨번호: L****" 확인

### 실패 케이스
1. **잘못된 형식**: abc123 입력 → "올바른 사번을 입력해주세요"
2. **중복 등록**: 이미 등록된 사번 → "이미 등록된 사번입니다"
3. **입력 없음**: 아무것도 입력하지 않음 → "사번을 입력해주세요"

## 📈 모니터링

- **CloudWatch Logs**: Contact Flow 실행 로그 확인
- **Lambda Logs**: 등록 처리 상세 로그 확인  
- **S3 Bucket**: 실제 등록 데이터 확인 (`s3://axcl/axcl_event.txt`)
- **Contact Flow 메트릭**: 성공률, 평균 처리 시간 추적