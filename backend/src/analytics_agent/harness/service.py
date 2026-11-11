"""Single-run application boundary shared by HTTP and batch orchestration."""

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from analytics_agent.db.models import Conversation
from analytics_agent.harness import runner, store
from analytics_agent.harness.contracts import RunRequest
from analytics_agent.harness.models import Run


class ConversationNotFound(ValueError):
    pass


async def run_case(
    request: RunRequest,
    session: AsyncSession,
    *,
    on_persisted: Callable[[str], None] | None = None,
) -> Run:
    """Persist initial/final snapshots; caller owns a dedicated session.

    Execution errors become tool_error reports in runner.execute. Persistence
    failures and cancellation propagate; they must not look like saved success.
    No checkpoint/resume or background-task guarantee is provided here.
    on_persisted is a synchronous identity notification after the initial commit;
    it must not perform I/O or mutate execution. It is not a success notification.
    """
    if request.conversation_id and await session.get(Conversation, request.conversation_id) is None:
        raise ConversationNotFound("Conversation not found")
    run = Run(
        schema_version=2,
        source=request.source,
        conversation_id=request.conversation_id,
        case_id=request.case_id,
        rule_id=request.rule_id,
        dataset_version=request.dataset_version,
    )
    await store.save(session, run)
    if on_persisted is not None:
        on_persisted(run.id)
    await runner.execute(run, request.claimed_value)
    await store.save(session, run)
    return run
