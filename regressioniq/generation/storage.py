from __future__ import annotations

import json
import shutil
from pathlib import Path

from regressioniq.generation.models import GeneratedTest, ReviewState


class ReviewStore:
    def __init__(self, repo_path: str = ".", review_dir: str = ".regressioniq/reviews") -> None:
        self.repo_path = Path(repo_path)
        self.review_root = self.repo_path / review_dir
        self.tests_dir = self.review_root / "tests"
        self.metadata_dir = self.review_root / "metadata"

    def save(self, proposal: GeneratedTest) -> GeneratedTest:
        review_path = self.repo_path / proposal.review_file
        metadata_path = self.repo_path / proposal.metadata_file
        review_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(proposal.test_code, encoding="utf-8")
        metadata_path.write_text(json.dumps(proposal.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        return proposal

    def list(self) -> list[GeneratedTest]:
        if not self.metadata_dir.exists():
            return []
        proposals: list[GeneratedTest] = []
        for path in sorted(self.metadata_dir.glob("*.json")):
            proposals.append(GeneratedTest.model_validate_json(path.read_text(encoding="utf-8")))
        return proposals

    def get(self, proposal_id: str) -> GeneratedTest:
        metadata = self.metadata_dir / f"{proposal_id}.json"
        if not metadata.exists():
            raise FileNotFoundError(f"No generated test found for id: {proposal_id}")
        return GeneratedTest.model_validate_json(metadata.read_text(encoding="utf-8"))

    def update_state(self, proposal_id: str, state: ReviewState) -> GeneratedTest:
        proposal = self.get(proposal_id)
        proposal.state = state
        return self.save(proposal)

    def approve(self, proposal_id: str) -> GeneratedTest:
        proposal = self.update_state(proposal_id, ReviewState.APPROVED)
        source = self.repo_path / proposal.review_file
        target = self.repo_path / proposal.target_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return proposal
