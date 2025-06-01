from cachetools import TTLCache

from .client import ClientProvider


class OUMembershipChecker:
    """Checks AWS account membership in Organization Units (OUs).

    This class provides functionality to verify if an AWS account belongs to
    specific OUs or their parent OUs in the AWS Organizations hierarchy.
    """

    def __init__(
        self,
        org_client_provider: ClientProvider,
        cache_ttl: int = 3600,
        cache_maxsize: int = 512,
    ):
        """Initialize the OU checker.

        Args:
            org_client_provider: Provider for AWS Organizations client
            cache_ttl: Time-to-live in seconds for cached parent lookups (default: 3600)
            cache_maxsize: Maximum number of entries in the parent lookup cache (default: 512)
        """
        self._org_client_provider = org_client_provider
        self._cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)

    def _get_parent(self, child_id: str) -> str | None:
        """Get the parent OU or root ID for a given child ID.

        Uses a TTL cache to reduce API calls to AWS Organizations.

        Args:
            child_id: ID of the child account or OU to find parent for

        Returns:
            str | None: ID of the parent OU or root, None if not found

        Raises:
            ValueError: If the child has no parent or multiple parents
        """
        if child_id in self._cache:
            return self._cache[child_id]

        response = self._org_client_provider.get_client().list_parents(ChildId=child_id)
        parents = response["Parents"]

        if len(parents) != 1:
            raise ValueError(f"Unable to determine parent for child {child_id}")

        parent_id = parents[0].get("Id", None)
        self._cache[child_id] = parent_id
        return parent_id

    def is_in_any_ou_or_descendant(
        self, account_id: str, target_haystack: set[str] | list[str]
    ) -> bool:
        """Check if an account belongs to any of the specified OUs or their descendants.

        This method traverses up the OU hierarchy from the account to the root,
        checking at each level if the current OU matches any of the target OUs.

        Args:
            account_id: The AWS account ID to check
            target_haystack: Set or list of account IDs or OU IDs to check against. Can include
                          account IDs, OU IDs (ou-*) and root IDs (r-*).

        Returns:
            bool: True if the account is in any of the target OUs or their
                 descendants, False otherwise

        Note:
            - The method will traverse up to 6 levels (5 OUs + root) as per AWS
              Organizations limits
            - The search stops when:
                1. A matching OU is found
                2. The root level is reached
                3. No parent is found
                4. Maximum depth is reached
        """
        current_id = account_id

        # AWS supports a max depth of 5 OUs, plus the root.
        for _ in range(6):
            if current_id in target_haystack:
                return True

            # We've hit the root.
            if current_id.startswith("r-"):
                break

            current_id = self._get_parent(current_id)
            if not current_id:
                break

        return False
