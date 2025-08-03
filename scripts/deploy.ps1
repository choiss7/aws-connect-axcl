# AWS Connect AXCL 프로젝트 배포 스크립트
# PowerShell Script for Windows Environment

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,
    
    [string]$FunctionName = "axcl-event-registration",
    [string]$S3Bucket = "axcl-lambda-deployment",
    [string]$Region = "ap-northeast-2"
)

Write-Host "🚀 AWS Connect AXCL Lambda 배포 시작" -ForegroundColor Green
Write-Host "환경: $Environment" -ForegroundColor Yellow
Write-Host "함수명: $FunctionName-$Environment" -ForegroundColor Yellow

try {
    # 1. 코드 품질 검사
    Write-Host "`n📋 1. 코드 품질 검사 중..." -ForegroundColor Blue
    
    # Python 문법 검사
    python -m py_compile lambda-functions/connect_event_registration.py
    if ($LASTEXITCODE -ne 0) {
        throw "Python 문법 오류가 발견되었습니다."
    }
    Write-Host "✅ Python 문법 검사 통과" -ForegroundColor Green
    
    # 2. 테스트 실행
    Write-Host "`n🧪 2. 단위 테스트 실행 중..." -ForegroundColor Blue
    pytest tests/ -v
    if ($LASTEXITCODE -ne 0) {
        throw "테스트 실패"
    }
    Write-Host "✅ 모든 테스트 통과" -ForegroundColor Green
    
    # 3. Lambda 패키지 생성
    Write-Host "`n📦 3. Lambda 배포 패키지 생성 중..." -ForegroundColor Blue
    
    $PackageDir = "temp-package"
    $ZipFile = "$FunctionName-$Environment.zip"
    
    # 임시 디렉토리 생성
    if (Test-Path $PackageDir) {
        Remove-Item -Recurse -Force $PackageDir
    }
    New-Item -ItemType Directory -Path $PackageDir | Out-Null
    
    # Lambda 함수 복사
    Copy-Item lambda-functions/connect_event_registration.py $PackageDir/lambda_function.py
    
    # ZIP 파일 생성
    Compress-Archive -Path "$PackageDir/*" -DestinationPath $ZipFile -Force
    Remove-Item -Recurse -Force $PackageDir
    
    Write-Host "✅ 배포 패키지 생성 완료: $ZipFile" -ForegroundColor Green
    
    # 4. S3에 업로드
    Write-Host "`n☁️ 4. S3에 배포 패키지 업로드 중..." -ForegroundColor Blue
    aws s3 cp $ZipFile s3://$S3Bucket/$Environment/ --region $Region
    if ($LASTEXITCODE -ne 0) {
        throw "S3 업로드 실패"
    }
    Write-Host "✅ S3 업로드 완료" -ForegroundColor Green
    
    # 5. Lambda 함수 업데이트
    Write-Host "`n⚡ 5. Lambda 함수 업데이트 중..." -ForegroundColor Blue
    
    $UpdateResult = aws lambda update-function-code `
        --function-name "$FunctionName-$Environment" `
        --s3-bucket $S3Bucket `
        --s3-key "$Environment/$ZipFile" `
        --region $Region `
        --output json
    
    if ($LASTEXITCODE -ne 0) {
        throw "Lambda 함수 업데이트 실패"
    }
    
    $UpdateInfo = $UpdateResult | ConvertFrom-Json
    Write-Host "✅ Lambda 함수 업데이트 완료" -ForegroundColor Green
    Write-Host "   버전: $($UpdateInfo.Version)" -ForegroundColor Gray
    Write-Host "   크기: $($UpdateInfo.CodeSize) bytes" -ForegroundColor Gray
    
    # 6. 환경변수 설정 (필요시)
    Write-Host "`n⚙️ 6. 환경변수 확인 중..." -ForegroundColor Blue
    
    $EnvVars = @{
        "BUCKET_NAME" = "axcl"
        "ENVIRONMENT" = $Environment
    }
    
    $EnvVarsJson = $EnvVars | ConvertTo-Json -Compress
    aws lambda update-function-configuration `
        --function-name "$FunctionName-$Environment" `
        --environment "Variables=$EnvVarsJson" `
        --region $Region | Out-Null
    
    Write-Host "✅ 환경변수 설정 완료" -ForegroundColor Green
    
    # 7. 정리
    Remove-Item $ZipFile -Force
    
    Write-Host "`n🎉 배포 완료!" -ForegroundColor Green
    Write-Host "함수명: $FunctionName-$Environment" -ForegroundColor Yellow
    Write-Host "리전: $Region" -ForegroundColor Yellow
    Write-Host "환경: $Environment" -ForegroundColor Yellow
    
    # 8. 배포 후 테스트 (선택사항)
    $TestChoice = Read-Host "`n🧪 배포된 함수를 테스트하시겠습니까? (y/N)"
    if ($TestChoice -eq "y" -or $TestChoice -eq "Y") {
        Write-Host "`n🧪 Lambda 함수 테스트 중..." -ForegroundColor Blue
        
        $TestPayload = @{
            "Details" = @{
                "ContactData" = @{
                    "ContactId" = "test-deploy-$(Get-Date -Format 'yyyyMMddHHmmss')"
                    "CustomerEndpoint" = @{
                        "Address" = "+821012345678"
                    }
                }
                "Parameters" = @{
                    "inputValue" = "1234"
                }
            }
        } | ConvertTo-Json -Depth 5
        
        $TestResult = aws lambda invoke `
            --function-name "$FunctionName-$Environment" `
            --payload $TestPayload `
            --region $Region `
            --output json `
            response.json
        
        if ($LASTEXITCODE -eq 0) {
            $Response = Get-Content response.json | ConvertFrom-Json
            Write-Host "✅ 테스트 성공!" -ForegroundColor Green
            Write-Host "응답: $($Response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
        } else {
            Write-Host "❌ 테스트 실패" -ForegroundColor Red
        }
        
        Remove-Item response.json -Force -ErrorAction SilentlyContinue
    }
    
} catch {
    Write-Host "`n❌ 배포 실패: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ 배포 프로세스 완료" -ForegroundColor Green