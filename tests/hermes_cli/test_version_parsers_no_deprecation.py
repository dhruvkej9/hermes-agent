"""Version parsers must not use APIs deprecated on the supported Pythons."""

import warnings

from hermes_cli.plugins_manifest import _version_tuple
from hermes_cli.profile_distribution import _parse_semver


def test_version_parsers_raise_no_deprecation_warning():
    # Python 3.13+ warns when re.split gets maxsplit positionally.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _version_tuple("v1.2.3-rc1") == (1, 2, 3)
        assert _parse_semver("0.12.0-rc1+abc") == (0, 12, 0)
