import pytest

from aws_ou_membership.checker import OUMembershipChecker


@pytest.fixture
def mock_client_provider(mock_org_client):
    class MockProvider:
        def get_client(self):
            return mock_org_client

    return MockProvider()


class TestOUChecker:
    @pytest.fixture
    def checker(self, mock_client_provider):
        return OUMembershipChecker(
            org_client_provider=mock_client_provider,
            cache_ttl=3600,
            cache_maxsize=512,
        )

    def test_get_parent_returns_parent_id(self, checker, mock_client_provider):
        mock_client_provider.get_client().list_parents.return_value = {
            "Parents": [{"Id": "ou-test-parent"}]
        }

        result = checker._get_parent("account-123")

        assert result == "ou-test-parent"
        mock_client_provider.get_client().list_parents.assert_called_once_with(
            ChildId="account-123"
        )

    def test_get_parent_raises_error_on_multiple_parents(
        self, checker, mock_client_provider
    ):
        mock_client_provider.get_client().list_parents.return_value = {
            "Parents": [{"Id": "ou-1"}, {"Id": "ou-2"}]
        }

        with pytest.raises(ValueError):
            checker._get_parent("account-123")

    def test_get_parent_uses_cache(self, checker, mock_client_provider):
        mock_client_provider.get_client().list_parents.return_value = {
            "Parents": [{"Id": "ou-test-parent"}]
        }

        # First call
        result1 = checker._get_parent("account-123")
        # Second call
        result2 = checker._get_parent("account-123")

        assert result1 == result2
        assert mock_client_provider.get_client().list_parents.call_count == 1

    @pytest.mark.parametrize(
        "account_id,target_haystack,parent_responses,expected",
        [
            # Direct match
            (
                "account-123",
                {"ou-target"},
                [{"Parents": [{"Id": "ou-target"}]}],
                True,
            ),
            # Match in ancestor
            (
                "account-123",
                {"ou-ancestor"},
                [
                    {"Parents": [{"Id": "ou-parent"}]},
                    {"Parents": [{"Id": "ou-ancestor"}]},
                ],
                True,
            ),
            # No match
            (
                "account-123",
                {"ou-other"},
                [
                    {"Parents": [{"Id": "ou-parent"}]},
                    {"Parents": [{"Id": "r-root"}]},
                ],
                False,
            ),
            # Root match
            (
                "account-123",
                {"r-root"},
                [
                    {"Parents": [{"Id": "ou-parent"}]},
                    {"Parents": [{"Id": "r-root"}]},
                ],
                True,
            ),
        ],
    )
    def test_is_in_any_ou_or_descendant(
        self,
        checker,
        mock_client_provider,
        account_id,
        target_haystack,
        parent_responses,
        expected,
    ):
        mock_client = mock_client_provider.get_client()
        mock_client.list_parents.side_effect = parent_responses

        result = checker.is_in_any_ou_or_descendant(account_id, target_haystack)

        assert result == expected
