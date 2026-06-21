from .models import Block


def get_last_block():
    return Block.objects.order_by('-index').first()


def append_block(event_type: str, data: dict) -> Block:
    """
    Call this whenever you want to log an event to the chain.
    Returns the newly created Block.
    """
    last = get_last_block()

    if last is None:
        # Genesis block
        previous_hash = '0' * 64
        index = 0
    else:
        previous_hash = last.hash
        index = last.index + 1

    block = Block(
        index=index,
        event_type=event_type,
        data=data,
        previous_hash=previous_hash,
    )
    block.save()
    return block


def verify_chain() -> dict:
    """
    Walks every block and checks:
    1. Its stored hash matches a fresh recompute
    2. Its previous_hash matches the actual previous block's hash
    Returns a dict with is_valid bool + details on any broken link.
    """
    blocks = Block.objects.order_by('index')

    if not blocks.exists():
        return {'is_valid': True, 'message': 'Chain is empty.', 'broken_at': None}

    previous_hash = '0' * 64

    for block in blocks:
        # Check 1 — recompute hash
        recomputed = block.compute_hash()
        if recomputed != block.hash:
            return {
                'is_valid': False,
                'message': f'Block #{block.index} hash is corrupted.',
                'broken_at': block.index,
            }

        # Check 2 — chain linkage
        if block.previous_hash != previous_hash:
            return {
                'is_valid': False,
                'message': f'Block #{block.index} is delinked from previous block.',
                'broken_at': block.index,
            }

        previous_hash = block.hash

    return {'is_valid': True, 'message': 'Chain integrity verified.', 'broken_at': None}