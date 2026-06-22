# T-224 — engine_c_portfolio code-health: removed dead/duplicate code (archived per [NN-ARCHIVE])

All removals below are behavior/canon-preserving (dead, no-op, or stdout-only).
2022 trades_canon_md5 unchanged across the pass.

## portfolio_engine.py — dead function `is_portfolio_debug()` (0 callers repo-wide; also buggy — returned a (bool, function) tuple, the function never called)
```python
def is_portfolio_debug():
    return is_debug_enabled("PORTFOLIO"), is_info_enabled
```

## portfolio_engine.py — duplicate `Position.edge_id` dataclass field (declared twice; second is a no-op redeclaration)
```python
    edge_id: Optional[str] = None
    edge_id: Optional[str] = None   # <- removed the duplicate
```

## portfolio_engine.py — duplicate dict keys in `_as_dict` (`edge_id`, `edge_category` each written twice; the second silently wins → no-op)
```python
        "edge_id": pos.edge_id,
        "edge_id": pos.edge_id,            # <- removed
        "edge_category": pos.edge_category,
        "edge_category": pos.edge_category, # <- removed
```

## portfolio_engine.py — redundant re-assignment of pos.edge_group / pos.edge_id to the same values they already hold (lines ~248-249)
```python
        pos.edge_group = pos.edge_group
        pos.edge_id = pos.edge_id   # <- removed (no-op self-assignment)
```
