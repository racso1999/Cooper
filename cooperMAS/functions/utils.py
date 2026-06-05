def _text(response) -> str:
    """Extract plain text from an LLM response regardless of provider format."""
    content = response.content
    if isinstance(content, str):
        return content
    return ''.join(
        block['text'] if isinstance(block, dict) else str(block)
        for block in content
        if not isinstance(block, dict) or block.get('type') == 'text'
    )
