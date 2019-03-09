

from enum import Enum


_space_tokens = {' ', '\t', '\n', '\r', '\f', '\v'}
State = Enum('State', 'SPACE STMT STRING COMM PRE_ML_COMM POST_ML_COMM ML_COMM')
ChunkType = Enum('ChunkType', 'SPACE STMT COMM ML_COMM')

state2chunk = {
    State.SPACE: ChunkType.SPACE,
    State.STMT: ChunkType.STMT,
    State.COMM: ChunkType.COMM,
    State.ML_COMM: ChunkType.ML_COMM
}


def chunk_model(model):
    state, prev_state = State.SPACE, None
    stmts, stmt = [], []

    for ch in model:

        if state is State.SPACE:
            if ch == '%':
                state = State.COMM
            elif ch == '/':
                prev_state = state
                state = State.PRE_ML_COMM
            elif ch == '"':
                state = State.STRING
            elif ch not in _space_tokens:
                state = State.STMT
            else:
                stmt.append(ch)

            if state is not State.SPACE:
                if len(stmt) > 0:
                    stmts.append((ChunkType.SPACE, ''.join(stmt)))
                if state is not State.PRE_ML_COMM:
                    stmt = [ch]
                else:
                    stmt = []

        elif state is State.STMT:
            if ch == '%':
                if len(stmt) > 0:
                    stmts.append((ChunkType.STMT, ''.join(stmt)))
                stmt = [ch]
                state = State.COMM
            elif ch == '/':
                prev_state = state
                state = State.PRE_ML_COMM
            elif ch == '"':
                stmt.append(ch)
                state = State.STRING
            elif ch == ';':
                stmt.append(ch)
                stmts.append((ChunkType.STMT, ''.join(stmt)))
                stmt = []
                state = State.SPACE
            else:
                stmt.append(ch)

        elif state is State.STRING:
            stmt.append(ch)
            if ch == '"':
                state = State.STMT

        elif state is State.COMM:
            if ch == '\n':
                stmts.append((ChunkType.COMM, ''.join(stmt)))
                stmt = [ch]
                state = State.SPACE
            else:
                stmt.append(ch)

        elif state is State.PRE_ML_COMM:
            if ch == '*':
                if len(stmt) > 0:
                    stmts.append((state2chunk[prev_state], ''.join(stmt)))
                stmt = ['/', ch]
                state = State.ML_COMM
            else:
                stmt += ['/', ch]
                state = prev_state
            prev_state = None
        elif state is State.ML_COMM:
            stmt.append(ch)
            if ch == '*':
                state = State.POST_ML_COMM

        elif state is State.POST_ML_COMM:
            if ch == '/':
                stmt.append(ch)
                stmts.append((ChunkType.ML_COMM, ''.join(stmt)))
                stmt = []
                state = State.SPACE
            else:
                stmt += ['*', ch]

    return stmts


def merge_statements(chunks):

    stmts = []
    in_stmt = False
    stmt = []
    for chunk_type, chunk in chunks:
        if in_stmt:
            stmt.append(chunk)
            if chunk_type is ChunkType.STMT and chunk.endswith(';'):
                stmts.append((ChunkType.STMT, ''.join(stmt)))
                stmt = []
                in_stmt = False
        elif chunk_type is ChunkType.STMT:
            if chunk.endswith(';'):
                stmts.append((chunk_type, chunk))
            else:
                stmt.append(chunk)
                in_stmt = True
        else:
            stmts.append((chunk_type, chunk))

    return stmts


def rewrap_statement(s, spaces):
    lines = []
    for line in s.splitlines():
        start = 0
        c = line[start]
        while start < len(line) and start < spaces and c in _space_tokens:
            start += 1
            c = line[start]
        lines.append(line[start:])
    return '\n'.join(lines)


def count_spaces(s, first):
    if s.startswith('\n') or first:
        leading_newlines = 0
        for c in s:
            if c == '\n':
                leading_newlines += 1
            else:
                break
        prev_space = len(s) - leading_newlines
        leading_newlines = min(leading_newlines, 2)
        space = '\n' * leading_newlines
        return space, prev_space
    else:
        return s, None


def rewrap_model(model):

    chunks = chunk_model(model)
    chunks = merge_statements(chunks)

    stmts = []
    first = True
    prev_space = None
    for chunk_type, chunk in chunks:
        if chunk_type is ChunkType.STMT:
            if prev_space:
                stmt = rewrap_statement(chunk, prev_space)
                prev_space = None
            else:
                stmt = chunk
            stmts.append(stmt)
        elif chunk_type is ChunkType.SPACE:
            space, prev_space = count_spaces(chunk, first)
            if chunk.startswith('\n\n'):
                space = '\n\n'
                prev_space = len(chunk) - 2
            elif chunk.startswith('\n'):
                space = '\n'
                prev_space = len(chunk) - 1
            else:
                space = chunk
                prev_space = None
            stmts.append(space)
        else:
            stmts.append(chunk)
            prev_space = None
        first = False

    model = ''.join(stmts)
    return model

