from datetime import datetime, timedelta, timezone

import pytest
from boto3.session import Session
from mypy_boto3_organizations import OrganizationsClient
from mypy_boto3_sts import STSClient


@pytest.fixture
def mock_sts_client(mocker):
    mock_client = mocker.Mock(spec=STSClient)
    mock_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "test-access-key",
            "SecretAccessKey": "test-secret-key",
            "SessionToken": "test-session-token",
            "Expiration": datetime.now(timezone.utc) + timedelta(hours=6),
        }
    }
    return mock_client


@pytest.fixture
def mock_org_client(mocker):
    return mocker.Mock(spec=OrganizationsClient)


@pytest.fixture
def mock_boto3_client(mocker):
    mock_client = mocker.Mock(spec=OrganizationsClient)
    mocker.patch("boto3.client", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_boto3_session(mocker):
    mock_session = mocker.Mock(spec=Session)
    mock_session.client.return_value = mocker.Mock(spec=OrganizationsClient)
    mocker.patch("boto3.Session", return_value=mock_session)
    return mock_session
