"""Rebase guard for this branch's inherited policy levers.

This branch USES route_revenue / industry_registry / resolve_industry (channel-exploration calls
route_revenue in channels.py; scenario-builder-ux names them in the scenario catalog + experiments/),
but it only INHERITED the three from an older `main`. The current `main` has since REMOVED them --
they were unwired on the trunk (the "lean-structure" cleanup, 2026-07-06). Because this branch never
authored the functions itself, a rebase onto the current `main` would drop them SILENTLY, with no
merge conflict.

This test converts that silent loss into a LOUD failure. If it fails after a rebase, re-add the three
functions to ogclews_link/policy_levers.py as a commit OWNED BY THIS BRANCH -- recover the code from
git history, e.g.:  git show <pre-removal-ref>:ogclews_link/policy_levers.py
"""


def test_branch_retains_inherited_policy_lever_trio():
    from ogclews_link.policy_levers import (
        industry_registry,
        resolve_industry,
        route_revenue,
    )

    assert callable(route_revenue)
    assert callable(industry_registry)
    assert callable(resolve_industry)
