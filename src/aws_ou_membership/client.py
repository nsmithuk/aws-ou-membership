from datetime import datetime, timedelta, timezone
from typing import Protocol

import boto3
from mypy_boto3_organizations import OrganizationsClient
from mypy_boto3_sts import STSClient


class ClientProvider(Protocol):
    """Protocol defining the interface for AWS Organizations client providers."""

    def get_client(self) -> OrganizationsClient:
        """Retrieve an AWS Organizations client.

        Returns:
            OrganizationsClient: A configured AWS Organizations client
        """
        ...


class DefaultSessionClientProvider:
    """Provides an AWS Organizations client using the default session credentials."""

    def get_client(self) -> OrganizationsClient:
        """Create an Organizations client using default boto3 session.

        Returns:
            OrganizationsClient: A configured AWS Organizations client
        """
        return boto3.client("organizations")


class AssumeRoleClientProvider:
    """Provides an AWS Organizations client by assuming an IAM role.

    This provider caches the client and automatically refreshes the credentials
    when they expire.
    """

    def __init__(
        self,
        sts_client: STSClient,
        role_arn: str,
        role_session_name: str = "ou-checker",
        role_session_ttl: int = 3600,
    ):
        """Initialize the provider with STS client and role details.

        Args:
            sts_client: AWS Security Token Service client
            role_arn: ARN of the IAM role to assume
            role_session_name: Name for the assumed role session
            role_session_ttl: Duration in seconds for the assumed role session
        """
        self._sts_client: STSClient = sts_client
        self._role_arn: str = role_arn
        self._role_session_name: str = role_session_name
        self._role_session_ttl: int = role_session_ttl

        self._org_client: OrganizationsClient | None = None

    def get_client(self) -> OrganizationsClient:
        """Get an AWS Organizations client using assumed role credentials.

        Returns a cached client if the credentials are still valid, otherwise
        assumes the role again and creates a new client.

        Returns:
            OrganizationsClient: A configured AWS Organizations client using
                assumed role credentials
        """
        if self._org_client:
            client, expires = self._org_client
            if expires > datetime.now(timezone.utc):
                return client

        sts_response = self._sts_client.assume_role(
            RoleArn=self._role_arn,
            RoleSessionName=self._role_session_name,
            DurationSeconds=self._role_session_ttl,
        )

        credentials = sts_response["Credentials"]
        expiration = credentials["Expiration"]

        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
        client = session.client("organizations")

        # Leave 60 seconds of headroom before actual expiration
        expire_at = expiration - timedelta(seconds=60)
        self._org_client = (client, expire_at)

        return client
