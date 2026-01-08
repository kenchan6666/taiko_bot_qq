"""
Temporal Workflow for processing messages.

This workflow orchestrates all 5 steps of message processing:
1. Parse input and validate (name detection, content filtering)
2. Retrieve user context from MongoDB
3. Query song information (if applicable)
4. Invoke LLM to generate response
5. Update impression and save conversation

Per T047: Create src/workflows/message_workflow.py with process_message_workflow.
Per T048: Configure retry policies (exponential backoff: 1s, 2s, 4s, 8s, max 5 attempts).
"""

from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

from src.activities.step1_activity import step1_parse_input_activity
from src.activities.step2_activity import step2_retrieve_context_activity
from src.activities.step3_activity import step3_query_song_activity
from src.activities.step4_activity import step4_invoke_llm_activity
from src.activities.step5_activity import step5_update_impression_activity


# Retry policy configuration
# Per FR-009: Exponential backoff retry (1s, 2s, 4s, 8s intervals, max 5 attempts)
RETRY_POLICY = RetryPolicy(
    initial_interval=1.0,  # 1 second
    backoff_coefficient=2.0,  # Double each time: 1s, 2s, 4s, 8s
    maximum_interval=8.0,  # Maximum 8 seconds
    maximum_attempts=5,  # Max 5 retry attempts
)


@workflow.defn(name="process_message_workflow")
class ProcessMessageWorkflow:
    """
    Temporal Workflow for processing a single message.

    Orchestrates all 5 steps of message processing with retry logic
    and fault tolerance. Each step is executed as a Temporal Activity
    with exponential backoff retry policy.

    Per FR-009: Exponential backoff retry strategy for transient failures.
    """

    @workflow.run
    async def run(
        self,
        user_id: str,
        group_id: str,
        message: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Execute the message processing workflow.

        This workflow:
        1. Parses and validates input (step1)
        2. Retrieves user context (step2)
        3. Queries song information (step3)
        4. Invokes LLM to generate response (step4)
        5. Updates impression and saves conversation (step5)

        Args:
            user_id: Plaintext QQ user ID.
            group_id: QQ group ID where message was sent.
            message: User's message content.
            images: Optional list of base64-encoded images.

        Returns:
            Dictionary with processing results:
            {
                "success": bool,
                "response": str,  # Generated response (empty if filtered)
                "parsed_input": dict | None,
                "context": dict | None,
                "song_info": dict | None,
                "impression_update": dict | None
            }

        Example:
            >>> result = await workflow.execute(
            ...     ProcessMessageWorkflow.run,
            ...     user_id="123456789",
            ...     group_id="987654321",
            ...     message="Mika, hello!"
            ... )
            >>> print(result["response"])
        """
        # Step 1: Parse input and validate
        # Per FR-001: Only respond to messages mentioning "Mika"
        # Per FR-007: Content filtering
        # Per FR-011: User ID hashing
        parsed_input_dict = await workflow.execute_activity(
            step1_parse_input_activity,
            user_id,
            group_id,
            message,
            images,
            start_to_close_timeout=30.0,  # 30 second timeout
            retry_policy=RETRY_POLICY,
        )

        # If message doesn't mention "Mika" or is filtered, return early
        if parsed_input_dict is None:
            return {
                "success": False,
                "response": "",
                "parsed_input": None,
                "context": None,
                "song_info": None,
                "impression_update": None,
            }

        # Step 2: Retrieve user context from MongoDB
        # Per FR-005: Retrieve conversation history for context
        context_dict = await workflow.execute_activity(
            step2_retrieve_context_activity,
            parsed_input_dict["hashed_user_id"],
            start_to_close_timeout=30.0,  # 30 second timeout
            retry_policy=RETRY_POLICY,
        )

        # Step 3: Query song information (if applicable)
        # Per FR-002: Query song data with fuzzy matching
        song_info = await workflow.execute_activity(
            step3_query_song_activity,
            parsed_input_dict["message"],
            start_to_close_timeout=30.0,  # 30 second timeout
            retry_policy=RETRY_POLICY,
        )

        # Step 4: Invoke LLM to generate response
        # Per FR-003: Incorporate thematic game elements
        # Per FR-013: Use structured prompt template system
        try:
            response = await workflow.execute_activity(
                step4_invoke_llm_activity,
                parsed_input_dict,
                context_dict,
                song_info,
                start_to_close_timeout=60.0,  # 60 second timeout (LLM can be slow)
                retry_policy=RETRY_POLICY,
            )
        except Exception:
            # Per FR-009: Graceful degradation
            # Return fallback response if LLM fails
            response = "Don! Mika暂时无法回应，但我会尽快回来的！🥁"

        # Step 5: Update impression and save conversation
        # Per FR-005: Store conversation history (90-day auto-deletion)
        # Per FR-010: Update impression when bot learns
        impression_update = await workflow.execute_activity(
            step5_update_impression_activity,
            parsed_input_dict,
            context_dict,
            response,
            start_to_close_timeout=30.0,  # 30 second timeout
            retry_policy=RETRY_POLICY,
        )

        # Return complete result
        return {
            "success": True,
            "response": response,
            "parsed_input": parsed_input_dict,
            "context": context_dict,
            "song_info": song_info,
            "impression_update": impression_update,
        }
