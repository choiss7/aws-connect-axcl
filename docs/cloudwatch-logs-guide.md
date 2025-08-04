# AWS Connect CloudWatch 로그 확인 가이드

AWS Connect 시스템의 CloudWatch 로그를 확인하고 모니터링하는 방법을 설명합니다.

## 📋 목차

- [로그 그룹 정보](#로그-그룹-정보)
- [기본 로그 확인 명령어](#기본-로그-확인-명령어)
- [실시간 로그 모니터링](#실시간-로그-모니터링)
- [로그 필터링](#로그-필터링)
- [문제해결](#문제해결)
- [자주 사용하는 명령어](#자주-사용하는-명령어)

## 📊 로그 그룹 정보

### 프로젝트 로그 그룹
- **로그 그룹명**: `/aws/connect/uplus-aicc`
- **리전**: `ap-northeast-2` (서울)
- **로그 스트림 형식**: `YYYY/MM/DD/HH/stream-{ID}`

### 로그 내용 예시
```json
{
  "ContactId": "87367aaf-99c3-441c-89c1-c8c25bf379a7",
  "ContactFlowId": "arn:aws:connect:ap-northeast-2:564929925185:instance/0145fce9-86f3-48a2-b4a9-cb8826940b5b/contact-flow/a9607398-8aff-48",
  "ContactFlowName": "AX채널Lab",
  "ContactFlowModuleType": "SetLoggingBehavior",
  "Parameters": {
    "LoggingBehavior": "Enable"
  },
  "Identifier": "103b9bc6-d842-4fbd-984d-75cc7fbb0785",
  "Timestamp": "2025-08-04T01:43:19.241Z"
}
```

## 🔍 기본 로그 확인 명령어

### 1. 로그 그룹 목록 확인
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/connect"
```

### 2. 특정 로그 그룹의 로그 스트림 목록 확인
```bash
aws logs describe-log-streams --log-group-name "/aws/connect/uplus-aicc" --order-by LastEventTime --descending
```

### 3. 가장 최근 로그 스트림의 로그 이벤트 확인
```bash
# 가장 최근 로그 스트림 이름 가져오기
aws logs describe-log-streams --log-group-name "/aws/connect/uplus-aicc" --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text

# 위 명령어로 얻은 스트림 이름을 사용하여 최근 로그 확인
aws logs get-log-events --log-group-name "/aws/connect/uplus-aicc" --log-stream-name "2025/08/04/01/stream-Fk547S6NEZtds2AXjKs8Jg==" --start-from-head false --limit 10
```

### 4. PowerShell에서 한 번에 최근 로그 확인
```powershell
# PowerShell에서 실행
$logGroupName = "/aws/connect/uplus-aicc"
$latestStream = aws logs describe-log-streams --log-group-name $logGroupName --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text
aws logs get-log-events --log-group-name $logGroupName --log-stream-name $latestStream --start-from-head false --limit 10
```

### 5. 특정 시간 범위의 로그 확인
```bash
# 최근 1시간 로그 확인
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --start-time $(date -d '1 hour ago' +%s)000 --limit 20
```

### 6. JSON 형식으로 보기 좋게 출력
```bash
aws logs get-log-events --log-group-name "/aws/connect/uplus-aicc" --log-stream-name "2025/08/04/01/stream-Fk547S6NEZtds2AXjKs8Jg==" --start-from-head false --limit 5 --output table
```

## 📺 실시간 로그 모니터링

### 1. 실시간 로그 모니터링 (tail 기능)
```bash
# 실시간으로 로그 모니터링
aws logs tail "/aws/connect/uplus-aicc" --follow
```

### 2. 특정 시간부터 실시간 모니터링
```bash
# 최근 10분부터 실시간 모니터링
aws logs tail "/aws/connect/uplus-aicc" --since 10m --follow
```

### 3. 특정 로그 스트림만 모니터링
```bash
# 특정 스트림만 실시간 모니터링
aws logs tail "/aws/connect/uplus-aicc" --log-stream-names "2025/08/04/01/stream-Fk547S6NEZtds2AXjKs8Jg==" --follow
```

## 🔍 로그 필터링

### 1. 특정 키워드로 로그 필터링
```bash
# "ContactId"가 포함된 로그만 확인
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --filter-pattern "ContactId" --limit 10

# "ERROR"가 포함된 로그만 확인
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --filter-pattern "ERROR" --limit 10
```

### 2. 복합 필터링
```bash
# ContactId와 특정 값이 포함된 로그
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --filter-pattern "ContactId 87367aaf-99c3-441c-89c1-c8c25bf379a7" --limit 10
```

### 3. 특정 모듈 타입 필터링
```bash
# SetLoggingBehavior 모듈 로그만 확인
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --filter-pattern "SetLoggingBehavior" --limit 10
```

## 🛠️ 문제해결

### 1. 리전 설정 확인
```bash
# 현재 리전 확인
aws configure get region

# 리전 설정 (서울)
aws configure set region ap-northeast-2
```

### 2. 권한 확인
```bash
# CloudWatch Logs 권한 테스트
aws logs describe-log-groups --log-group-name-prefix "/aws/connect" --max-items 1
```

### 3. 로그 그룹 존재 확인
```bash
# 로그 그룹 상세 정보 확인
aws logs describe-log-groups --log-group-names "/aws/connect/uplus-aicc"
```

### 4. 로그 스트림 존재 확인
```bash
# 오늘 날짜의 모든 로그 스트림 확인
aws logs describe-log-streams --log-group-name "/aws/connect/uplus-aicc" --log-stream-name-prefix "2025/08/04/"
```

## ⚡ 자주 사용하는 명령어

### 빠른 로그 확인 (가장 최근 10개)
```bash
aws logs tail "/aws/connect/uplus-aicc" --since 1h
```

### 오늘 로그 확인
```bash
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --start-time $(date -d 'today 00:00:00' +%s)000
```

### 에러 로그만 확인
```bash
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --filter-pattern "ERROR" --since 1h
```

### 특정 ContactId 로그 확인
```bash
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --filter-pattern "ContactId" --since 1h
```

## 📝 로그 분석 팁

### 1. 로그 구조 이해
- **ContactId**: 각 통화의 고유 식별자
- **ContactFlowName**: 사용된 Contact Flow 이름
- **ContactFlowModuleType**: 실행된 모듈 타입
- **Parameters**: 모듈별 파라미터
- **Timestamp**: 이벤트 발생 시간

### 2. 모니터링 포인트
- **SetLoggingBehavior**: 로깅 시작
- **SetVoice**: 음성 설정
- **GetUserInput**: 사용자 입력 처리
- **Lambda**: Lambda 함수 호출

### 3. 디버깅 시 확인사항
- ContactId로 특정 통화 추적
- ContactFlowModuleType으로 실행 흐름 확인
- Parameters로 입력값 검증
- Timestamp로 시간 순서 확인

## 🔧 고급 사용법

### 1. 로그 내보내기
```bash
# 특정 기간 로그를 파일로 저장
aws logs filter-log-events --log-group-name "/aws/connect/uplus-aicc" --start-time $(date -d '1 hour ago' +%s)000 --output json > logs_$(date +%Y%m%d_%H%M%S).json
```

### 2. 로그 통계 확인
```bash
# 로그 스트림 수 확인
aws logs describe-log-streams --log-group-name "/aws/connect/uplus-aicc" --query 'length(logStreams)'

# 오늘 생성된 로그 스트림 수
aws logs describe-log-streams --log-group-name "/aws/connect/uplus-aicc" --log-stream-name-prefix "$(date +%Y/%m/%d)/" --query 'length(logStreams)'
```

### 3. 로그 보존 기간 확인
```bash
aws logs describe-log-groups --log-group-names "/aws/connect/uplus-aicc" --query 'logGroups[0].retentionInDays'
```

## 📚 참고 자료

- [AWS CLI CloudWatch Logs 명령어 참조](https://docs.aws.amazon.com/cli/latest/reference/logs/)
- [AWS Connect 로깅 가이드](https://docs.aws.amazon.com/connect/latest/adminguide/monitoring-cloudwatch.html)
- [CloudWatch Logs 필터 패턴](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html)

---

**마지막 업데이트**: 2025-08-04  
**버전**: 1.0.0 