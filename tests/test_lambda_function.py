"""
AWS Connect AXCL 이벤트 등록 Lambda 함수 테스트

pytest를 사용한 단위 테스트 및 통합 테스트
"""

import pytest
import json
import boto3
from unittest.mock import patch, MagicMock
import sys
import os

# Lambda 함수 import를 위한 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda-functions'))

from connect_event_registration import (
    lambda_handler,
    extract_contact_data,
    is_duplicate_registration,
    generate_lottery_number,
    create_response
)


class TestLambdaHandler:
    """Lambda 핸들러 테스트"""
    
    @patch('boto3.client')
    def test_successful_registration(self, mock_boto3_client):
        """정상적인 등록 프로세스 테스트"""
        # S3 모킹 설정
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        # NoSuchKey 예외를 시뮬레이션 (새로운 등록)
        from botocore.exceptions import ClientError
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
        )
        
        # 테스트 이벤트
        event = {
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
        
        # Lambda 함수 실행
        result = lambda_handler(event, None)
        
        # 검증
        assert result["registrationStatus"] == "SUCCESS"
        assert result["lotteryNumber"].startswith("L")
        assert "등록이 완료되었습니다" in result["successMessage"]
        assert result["errorMessage"] == ""
        
        # S3 put_object가 호출되었는지 확인
        mock_s3.put_object.assert_called_once()
    
    @patch('boto3.client')
    def test_duplicate_registration(self, mock_boto3_client):
        """중복 등록 방지 테스트"""
        # S3 모킹 설정
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        # 기존 데이터 시뮬레이션
        existing_data = "2025-08-03T10:00:00+00:00,+821012345678,contact-123,1234\n"
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = existing_data.encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        
        # 중복 등록 시도
        event = {
            "Details": {
                "Parameters": {
                    "inputValue": "1234"  # 동일한 사번
                }
            }
        }
        
        result = lambda_handler(event, None)
        
        # 검증
        assert result["registrationStatus"] == "DUPLICATE"
        assert "이미 등록된 사번입니다" in result["errorMessage"]
    
    def test_invalid_input_format(self):
        """잘못된 입력 형식 테스트"""
        event = {
            "Details": {
                "Parameters": {
                    "inputValue": "abc123"  # 문자 포함
                }
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result["registrationStatus"] == "INVALID_FORMAT"
        assert "올바른 사번을 입력해주세요" in result["errorMessage"]
    
    def test_missing_input(self):
        """입력값 누락 테스트"""
        event = {
            "Details": {
                "Parameters": {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result["registrationStatus"] == "INPUT_ERROR"
        assert "사번을 입력해주세요" in result["errorMessage"]


class TestDataExtraction:
    """데이터 추출 기능 테스트"""
    
    def test_extract_standard_format(self):
        """표준 AWS Connect 형식 데이터 추출 테스트"""
        event = {
            "Details": {
                "ContactData": {
                    "ContactId": "contact-123",
                    "CustomerEndpoint": {
                        "Address": "+821012345678"
                    },
                    "Attributes": {
                        "customerInput": "5678"
                    }
                },
                "Parameters": {
                    "inputValue": "1234"
                }
            }
        }
        
        result = extract_contact_data(event)
        
        assert result["customer_input"] == "1234"  # Parameters가 우선순위
        assert result["customer_phone"] == "+821012345678"
        assert result["contact_id"] == "contact-123"
    
    def test_extract_simple_format(self):
        """단순 형식 데이터 추출 테스트"""
        event = {
            "inputValue": "9999",
            "customerPhone": "+821087654321",
            "contactId": "simple-contact-456"
        }
        
        result = extract_contact_data(event)
        
        assert result["customer_input"] == "9999"
        assert result["customer_phone"] == "+821087654321"
        assert result["contact_id"] == "simple-contact-456"


class TestLotteryNumber:
    """추첨번호 생성 테스트"""
    
    def test_generate_lottery_number_consistency(self):
        """동일한 입력에 대한 일관된 추첨번호 생성 테스트"""
        input_value = "1234"
        
        result1 = generate_lottery_number(input_value)
        result2 = generate_lottery_number(input_value)
        
        assert result1 == result2
        assert result1.startswith("L")
        assert len(result1) == 5  # L + 4자리 숫자
    
    def test_generate_lottery_number_different_inputs(self):
        """서로 다른 입력에 대한 다른 추첨번호 생성 테스트"""
        result1 = generate_lottery_number("1234")
        result2 = generate_lottery_number("5678")
        
        assert result1 != result2
        assert result1.startswith("L")
        assert result2.startswith("L")


class TestResponseCreation:
    """응답 생성 테스트"""
    
    def test_create_success_response(self):
        """성공 응답 생성 테스트"""
        result = create_response("SUCCESS", "L1234", "등록 완료")
        
        assert result["registrationStatus"] == "SUCCESS"
        assert result["lotteryNumber"] == "L1234"
        assert result["successMessage"] == "등록 완료"
        assert result["errorMessage"] == ""
    
    def test_create_error_response(self):
        """에러 응답 생성 테스트"""
        result = create_response("ERROR", None, "오류 발생")
        
        assert result["registrationStatus"] == "ERROR"
        assert result["lotteryNumber"] == ""
        assert result["successMessage"] == ""
        assert result["errorMessage"] == "오류 발생"


class TestDuplicateCheck:
    """중복 확인 테스트"""
    
    @patch('boto3.client')
    def test_no_duplicate_empty_file(self, mock_boto3_client):
        """빈 파일에서 중복 확인 테스트"""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        # NoSuchKey 예외 시뮬레이션
        from botocore.exceptions import ClientError
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
        )
        
        result = is_duplicate_registration("1234")
        assert result is False
    
    @patch('boto3.client')
    def test_no_duplicate_with_data(self, mock_boto3_client):
        """데이터가 있지만 중복되지 않는 경우 테스트"""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        existing_data = "2025-08-03T10:00:00+00:00,+821012345678,contact-123,5678\n"
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = existing_data.encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        
        result = is_duplicate_registration("1234")
        assert result is False
    
    @patch('boto3.client')
    def test_duplicate_found(self, mock_boto3_client):
        """중복 발견 테스트"""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        existing_data = (
            "2025-08-03T10:00:00+00:00,+821012345678,contact-123,1234\n"
            "2025-08-03T10:05:00+00:00,+821087654321,contact-456,5678\n"
        )
        mock_response = MagicMock()
        mock_response['Body'].read.return_value = existing_data.encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        
        result = is_duplicate_registration("1234")
        assert result is True


if __name__ == "__main__":
    # pytest 실행
    pytest.main([__file__, "-v"])