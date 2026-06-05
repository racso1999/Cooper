from pathlib import Path

_BASE = Path(__file__).parent.parent


def _load_prompt(filename: str) -> str:
    return (_BASE / 'prompts' / filename).read_text(encoding='utf-8').strip()


COOPER_SYSTEM_PROMPT   = _load_prompt('cooper_system.md')
COOPER_COMPILER_PROMPT = _load_prompt('cooper_compiler.md')
