# Changelog

## 0.1.1 — unreleased

- `encode_create_deposit` defaults `intent_guardian` to the protocol guardian
  instead of `address(0)`. Deposits created by `0.1.0` encoded
  `intentGuardian = 0x0000000000000000000000000000000000000000`; this restores
  parity with `@usdctofiat/offramp` 8.0.0. (#3, #4)
- Version is single-sourced from `usdctofiat.__version__`; `pyproject.toml`
  derives it.
- Releases are cut by pushing a `v*` tag, which runs `.github/workflows/release.yml`
  and publishes to PyPI via Trusted Publishing after the `pypi` environment
  approval.

## 0.1.0 — 2026-08-14

- First PyPI upload. `cashout(mode="fast"|"best")` on Base, attribution locked to
  `peer-ref-TOFIAT` then `galleonlabs`, no private-key handling.
