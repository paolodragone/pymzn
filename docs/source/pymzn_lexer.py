
from pygments.lexer import RegexLexer, bygroups, words, include, inherit
from pygments.lexers import DjangoLexer
from pygments.token import *
from minizinc_lexer import MznLexer

import re

__all__=['PyMznLexer']


jinja_root_tokens = DjangoLexer.tokens['root']
jinja_root_tokens.pop(0)


class PyMznLexer(RegexLexer):

    name = 'PyMzn'
    aliases = ['pymzn']
    filenames = ['*.pmzn']

    tokens = {
        'root': jinja_root_tokens + MznLexer.tokens['root'],
        'varnames': DjangoLexer.tokens['varnames'],
        'var': DjangoLexer.tokens['var'],
        'block': DjangoLexer.tokens['block'],
        'main__1': MznLexer.tokens['main__1'],
        'main__2': MznLexer.tokens['main__2'],
        'main__3': MznLexer.tokens['main__3'],
        'main__4': MznLexer.tokens['main__4'],
        'multi_line_comment__1': MznLexer.tokens['multi_line_comment__1'],
        'string__1': MznLexer.tokens['string__1'],
        'string__2': MznLexer.tokens['string__2']
    }

    def analyse_text(text):
        return DjangoLexer.analyse_text(text)
