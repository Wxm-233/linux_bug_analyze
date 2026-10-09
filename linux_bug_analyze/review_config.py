"""Configuration for the local, human-in-the-loop review workbench."""
from dataclasses import dataclass
from pathlib import Path
import math


@dataclass(frozen=True)
class ReviewSettings:
    output_dir: Path | None = None
    port: int = 8765
    training_target: int = 160
    validation_size: int = 40
    random_seed: int = 42
    exploration_every: int = 5
    audit_rate: float = 0.01
    audit_minimum: int = 100
    boundary_sample: int = 20
    max_requests: int = 100
    token_budget: int = 2_000_000
    workers: int = 4
    summary_max_requests: int = 500
    summary_token_budget: int = 4_000_000
    summary_diff_chars: int = 12000
    summary_retries: int = 3


def parse_review_settings(data, base_dir):
    if not isinstance(data, dict):
        raise ValueError("[review] 必须是 TOML 表")
    unknown = set(data) - set(ReviewSettings.__dataclass_fields__)
    if unknown:
        raise ValueError(f"[review] 未知字段：{', '.join(sorted(unknown))}")
    values = dict(data)
    path = values.pop('output_dir', '')
    if not isinstance(path, str):
        raise ValueError('review.output_dir 必须是字符串')
    values['output_dir'] = (base_dir / Path(path).expanduser()).resolve() if path else None
    for key, value in values.items():
        if key == 'output_dir':
            continue
        if key == 'audit_rate':
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1:
                raise ValueError('review.audit_rate 必须在 (0, 1] 内')
        elif type(value) is not int or value < (0 if key in ('random_seed', 'boundary_sample', 'summary_retries') else 1):
            raise ValueError(f'review.{key} 必须是有效的非负/正整数')
    result = ReviewSettings(**values)
    if not 1 <= result.port <= 65535 or result.workers > 16:
        raise ValueError('review.port 必须在 1–65535，workers 不超过 16')
    if result.training_target < 2:
        raise ValueError('review.training_target 至少为 2（需要正负两类）')
    if result.summary_retries > 10:
        raise ValueError('review.summary_retries 不超过 10')
    return result
