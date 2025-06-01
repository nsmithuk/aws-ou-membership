# AWS Account OU Membership

**Checks whether an AWS account sits within a set of OUs - or their descendants - within an AWS Organization.**

`aws_ou_membership` is a lightweight Python library that determines if a given AWS account resides within a target Organizational Unit (OU) or one of its ancestors. It uses the AWS Organizations API and supports caching for performance.

## Features

- Traverse the OU hierarchy to check account membership.
- Supports custom caching using `cachetools`.
- Pluggable client providers (default session or STS-based assume-role).

## Installation

## Usage

```python
from aws_ou_membership import OUMembershipChecker, DefaultSessionClientProvider

# Create the checker
checker = OUMembershipChecker(DefaultSessionClientProvider())

# Check if an account is in a specific OU or its ancestors
result = checker.is_in_any_ou_or_descendant(account_id="123456789012", target_haystack={"ou-abcd-efgh"})
print(result)  # True or False
```

## Custom Client Provider (Assume Role)

The `organizations:ListParents` action must be called from a principal within the AWS Organization's management account. It's common therefore assume a role into the management account to use this tool.

```python
from aws_ou_membership import OUMembershipChecker, AssumeRoleClientProvider
import boto3

sts = boto3.client("sts")
provider = AssumeRoleClientProvider(
    sts_client=sts,
    role_arn="arn:aws:iam::111122223333:role/OrgAuditRole"
)

checker = OUMembershipChecker(provider)
```

## Caching

You can customise the cache's TTL and max size:

```python
checker = OUMembershipChecker(org_client_provider=..., cache_ttl=1800, cache_maxsize=256)
```

## License

MIT License
