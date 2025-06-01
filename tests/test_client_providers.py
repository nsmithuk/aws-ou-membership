from datetime import datetime, timedelta, timezone

import pytest

from aws_ou_membership.client import (
    AssumeRoleClientProvider,
    DefaultSessionClientProvider,
)


def test_default_session_client_provider(mock_boto3_client):
    provider = DefaultSessionClientProvider()
    client = provider.get_client()

    assert client == mock_boto3_client


class TestAssumeRoleClientProvider:
    @pytest.fixture
    def provider(self, mock_sts_client):
        return AssumeRoleClientProvider(
            sts_client=mock_sts_client,
            role_arn="arn:aws:iam::123456789012:role/test-role",
            role_session_name="test-session",
            role_session_ttl=3600,
        )

    def test_get_client_assumes_role(
        self, provider, mock_sts_client, mock_boto3_session
    ):
        client = provider.get_client()

        mock_sts_client.assume_role.assert_called_once_with(
            RoleArn="arn:aws:iam::123456789012:role/test-role",
            RoleSessionName="test-session",
            DurationSeconds=3600,
        )
        assert client == mock_boto3_session.client.return_value

    def test_get_client_caches_credentials(
        self, provider, mock_sts_client, mock_boto3_session
    ):
        # First call
        client1 = provider.get_client()
        # Second call
        client2 = provider.get_client()

        # Should only assume role once
        assert mock_sts_client.assume_role.call_count == 1
        assert client1 == client2

    def test_get_client_refreshes_expired_credentials(
        self, provider, mock_sts_client, mock_boto3_session, mocker
    ):
        # Mock datetime.now() to control time
        mock_now = mocker.patch("aws_ou_membership.client.datetime")
        mock_now.now.return_value = datetime.now(timezone.utc) - timedelta(hours=24)

        # First call
        client1 = provider.get_client()

        # Move time forward past expiration
        mock_now.now.return_value = datetime.now(timezone.utc) + timedelta(hours=24)

        # Second call
        client2 = provider.get_client()

        assert mock_sts_client.assume_role.call_count == 2
