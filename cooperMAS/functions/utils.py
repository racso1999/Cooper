def _text(response) -> str:
# Fixes the fact that some LLM clients return a string, while others return a list of text/dict blocks.

    content = response.content
    if isinstance(content, str):
        return content
    return ''.join(
        block['text'] if isinstance(block, dict) else str(block)
        for block in content
        if not isinstance(block, dict) or block.get('type') == 'text'
    )
