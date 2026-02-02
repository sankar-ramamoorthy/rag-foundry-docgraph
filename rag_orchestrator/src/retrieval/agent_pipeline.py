import logging
from typing import List, Dict, Optional, Callable

from .types import RetrievedContext
from .agent_adapter import prepare_chunks_for_agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AgentPromptPipeline:
    """
    Feed retrieved chunks into an LLM agent prompt while enforcing:
      - Deterministic document + chunk ordering
      - Token budget limits
      - Optional scoring/filtering
      - Provenance tracing
    """

    def __init__(
        self,
        max_chunks_per_doc: int = 5,
        max_total_chunks: int = 50,
        max_tokens: Optional[int] = None,
        chunk_token_count: Optional[Callable] = None,
        filter_chunk: Optional[Callable] = None,
        debug: bool = False,
    ):
        self.max_chunks_per_doc = max_chunks_per_doc
        self.max_total_chunks = max_total_chunks
        self.max_tokens = max_tokens
        self.chunk_token_count = chunk_token_count
        self.filter_chunk = filter_chunk
        self.debug = debug

    def build_prompt_input(
        self,
        retrieved: RetrievedContext,
        document_order: Optional[List[str]] = None,
    ) -> List[Dict[str, object]]:
        """
        Convert RetrievedContext into agent-ready chunks and optionally enforce
        token budgets and filtering before sending to the LLM.
        """

        chunks = prepare_chunks_for_agent(
            retrieved,
            document_order=document_order,
            max_chunks_per_doc=self.max_chunks_per_doc,
            max_total_chunks=self.max_total_chunks,
            max_tokens=self.max_tokens,
            chunk_token_count=self.chunk_token_count,
            filter_chunk=self.filter_chunk,
            debug=self.debug,
        )

        if self.debug:
            logger.debug(f"Agent prompt input prepared with {len(chunks)} chunks")

        return chunks

    def build_prompt_text(
        self,
        retrieved: RetrievedContext,
        document_order: Optional[List[str]] = None,
        template: Optional[str] = None,
    ) -> str:
        """
        Flatten chunks into a single prompt string for the LLM,
        preserving provenance and deterministic order.
        """

        chunks = self.build_prompt_input(retrieved, document_order=document_order)

        # Default template: concatenate chunk text
        if template is None:
            prompt_parts = []
            for c in chunks:
                part = f"[{c['document_id']}/{c['chunk_id']}] {c['text']}"
                prompt_parts.append(part)
            return "\n\n".join(prompt_parts)
        else:
            # Template could be a callable or a string with placeholders
            # Placeholder example: "{document_id}:{chunk_id}:{text}"
            prompt_parts = []
            for c in chunks:
                prompt_parts.append(template.format(**c))
            return "\n\n".join(prompt_parts)
