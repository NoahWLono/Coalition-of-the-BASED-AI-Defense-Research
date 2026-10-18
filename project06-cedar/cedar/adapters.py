"""Optional future proposal adapter contract. No live model client is implemented."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class ExtractionProposal:
    document_id: str
    document_hash: str
    start_line: int
    end_line: int
    proposed_key: str
    proposed_value: str
    rationale: str
    model_identifier: str

class ProposalAdapter(Protocol):
    """Receives only explicitly selected synthetic document text and its hash.

    A future implementation must log exact transmitted inputs and real model outputs.
    Proposals are untrusted and cannot mutate policy, roles, reviews or approvals.
    This interface is not called by the demonstrated deterministic workflow.
    """
    def propose(self, document_id:str, document_hash:str, content:str)->list[ExtractionProposal]: ...
