import markdown
from markdown import Extension
from markdown.postprocessors import Postprocessor
from pymdownx import util
import os
import re
from urllib.parse import urlunparse


RE_TAG_HTML = r'''(?xus)
    (?:
        (?P<avoid>
            <\s*(?P<script_name>script|style)[^>]*>.*?</\s*(?P=script_name)\s*> |
            (?:(\r?\n?\s*)<!--[\s\S]*?-->(\s*)(?=\r?\n)|<!--[\s\S]*?-->)
        )|
        (?P<open><\s*(?P<tag>(?:%s)))
        (?P<attr>(?:\s+[\w\-:]+(?:\s*=\s*(?:"[^"]*"|'[^']*'))?)*)
        (?P<close>\s*(?:\/?)>)
    )
    '''

RE_TAG_LINK_ATTR = re.compile(
    r'''(?xus)
    (?P<attr>
        (?:
            (?P<name>\s+(?:href|src)\s*=\s*)
            (?P<path>"[^"]*"|'[^']*')
        )
    )
    '''
)


def repl_relative(m, base_path, relative_path):
    """Replace path with relative path."""

    link = m.group(0)
    try:
        scheme, netloc, path, params, query, fragment, is_url, is_absolute = util.parse_url(m.group('path')[1:-1])
        
        if not is_url:
            # Get the absolute path of the file or return
            # if we can't resolve the path
            path = util.url2path(path)
            
            if (not is_absolute):
                # print(os.path.normpath(os.path.join(base_path, path)))
                # print(os.path.normpath(relative_path))
                # Convert current relative path to absolute
                path = os.path.relpath(
                    os.path.normpath(os.path.join(base_path, path)),
                    os.path.normpath(relative_path)
                )
                
                # Convert the path, URL encode it, and format it as a link
                path = util.path2url(path)
                link = '{}"{}"'.format(
                    m.group('name'),
                    urlunparse((scheme, netloc, path, params, query, fragment))
                )
    except Exception:  # pragma: no cover
        # Parsing crashed and burned; no need to continue.
        pass

    return link


def repl_absolute(m, base_path, file_scheme):
    """Replace path with absolute path."""

    link = m.group(0)
    try:
        scheme, netloc, path, params, query, fragment, is_url, is_absolute = util.parse_url(m.group('path')[1:-1])

        if (not is_absolute and not is_url):
            path = util.url2path(path)
            path = os.path.normpath(os.path.join(base_path, path))
            path = util.path2url(path)
            if file_scheme:
                if not path.startswith('/'):
                    path = '/' + path
                link = '{}"{}"'.format(
                    m.group('name'),
                    urlunparse(("file", netloc, path, params, query, fragment))
                )
            else:
                start = '/' if not path.startswith('/') else ''
                link = '{}"{}{}"'.format(
                    m.group('name'),
                    start,
                    urlunparse((scheme, netloc, path, params, query, fragment))
                )
    except Exception:  # pragma: no cover
        # Parsing crashed and burned; no need to continue.
        pass

    return link


def repl(m, base_path, rel_path=None, file_scheme=None):
    """Replace."""
    # print(f"m={m}")
    if m.group('avoid'):
        
        tag = m.group('avoid')
    else:
        tag = m.group('open')
        attr = m.group('attr')
        if attr.endswith("ignore_pathconverter"):
            # print("ignore_pathconverter end")
            tag += attr
        elif rel_path is None:
            tag += RE_TAG_LINK_ATTR.sub(lambda m2: repl_absolute(m2, base_path, file_scheme), attr)
        else:
            tag += RE_TAG_LINK_ATTR.sub(lambda m2: repl_relative(m2, base_path, rel_path), attr)
        tag += m.group('close')
    return tag



class PathConverterPostprocessor(Postprocessor):
    """Post process to find tag lings to convert."""

    def run(self, text):
        """Find and convert paths."""
        basepath = self.config['base_path']
        relativepath = self.config['relative_path']
        absolute = bool(self.config['absolute'])
        filescheme = bool(self.config['file_scheme'])
        tags = re.compile(RE_TAG_HTML % '|'.join(self.config['tags'].split()))
        if not absolute and basepath and relativepath:
            text = tags.sub(lambda m: repl(m, basepath, rel_path=relativepath), text)
        elif absolute and basepath:
            
            text = tags.sub(lambda m: repl(m, basepath, file_scheme=filescheme), text)
        return text


class PathConverterExtension(Extension):
    """PathConverter extension."""

    def __init__(self, *args, **kwargs):
        """Initialize."""

        self.config = {
            'base_path': ["", "Base path used to find files - Default: \"\""],
            'relative_path': ["", "Path that files will be relative to (not needed if using absolute) - Default: \"\""],
            'absolute': [False, "Paths are absolute by default; disable for relative - Default: False"],
            'tags': ["img script a link", "tags to convert src and/or href in - Default: 'img scripts a link'"],
            'file_scheme': [False, "Use file:// scheme for absolute paths - Default: False"],
        }

        super().__init__(*args, **kwargs)

    def extendMarkdown(self, md):
        """Add post processor to Markdown instance."""

        rel_path = PathConverterPostprocessor(md)
        rel_path.config = self.getConfigs()
        md.postprocessors.register(rel_path, "path-converter", 2)
        md.registerExtension(self)


def makeExtension(*args, **kwargs):
    """Return extension."""
    # print("makeExtension")
    return PathConverterExtension(*args, **kwargs)





# md = markdown.Markdown(extensions=[
#     PathConverterExtension(
#         base_path='docs/zh',
#         relative_path="/Users/yang/WorkSpace/Projects/bigModel/llm-eval-opensource/docs/zh/component/",
#         tags="img"
#     )
# ])
# # print(md.postprocessors)
# html = md.convert("""
# <img src="images/param.png" alt="评测指标" width="300"  ignore_pathconverter/>
# """)

# print(html)