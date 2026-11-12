import copy
import re
from typing import Tuple

import logging
logger = logging.getLogger(__name__)


class WrongAdobeTablePathError(Exception):
    def __init__(self, path):
        super().__init__(f"Invalid adobe table path, {path=}")


def get_path_nodes(path: str):
    path_nodes = []
    for node in path.split("/"):
        if (subnodes := node.split("[")) and len(subnodes) > 1:
            if node == "TR[2]":
                node = node  # special case to create the second row in table
            elif subnodes[0] in ("TR", "TH", "TD"):
                node = subnodes[0] + "[*]"  # eg. TR[3] -> TR[*]
            else:
                node = subnodes[0]  # eg. P[3] -> P
        if node not in ("", "Document", "Sect"):
            path_nodes.append(node)
    return path_nodes


def get_table_col_n(path) -> int:
    for node in reversed(path.split("/")):
        if node.startswith("TH"):
            subnodes = node.split("[")
            if len(subnodes) == 1:
                return 1
            return int(subnodes[-1].replace("]", ""))

    logger.error("Invalid adobe table path: %s", path)
    return 0


def adobe_elem_to_markdown(path: str, text: str, prev_path: str = "") -> Tuple[str, str | None]:
    """
    Not implemented:
        * multiline cells
        * bullet lists in cells
        * rows w/ different cell number (eg. multi header)

    """
    text = text or ""

    if not (path_nodes := get_path_nodes(path)):
        return text, None

    elem_type = path_nodes[0]

    if prev_path_nodes := get_path_nodes(prev_path):
        prev_elem_type = prev_path_nodes[0]
        if prev_elem_type == "Table" and elem_type != prev_elem_type:
            text = f"|\n\n{text}"

    match path_nodes:
        case ["H1", *_] if text:
            text = f"# {text}\n\n"
        case ["H2", *_] if text:
            text = f"## {text}\n\n"
        case ["H3", *_] if text:
            text = f"### {text}\n\n"
        case ["P"] if text:
            text = f"{text}\n"
        case ["P", *rest] if rest:
            text = text  # No new line for sub-paragraphs
        case [*_, "Lbl"] if text:
            pad_left = path_nodes.count("L") * "  "
            text = f"\n{pad_left}{text}"
        case ["L", *_]:  # All list items except for points (captured above)
            text = text
        case ["Table", "TR", "TH"]:
            text = "\n|"
        case ["Table", "TR", "TH[*]"] | ["Table", "TR", "TD[*]"]:
            text = "|"
        case ["Table", "TR[2]", "TH"]:  # second row, first col
            col_n = get_table_col_n(prev_path)
            sep_col = "| - " * col_n
            text = f"|\n{sep_col}|\n|"
        case ["Table", "TR[2]", "TH[*]"] | ["Table", "TR[2]", "TD"] | ["Table", "TR[2]", "TD[*]"]:
            text = "|"
        case ["Table", "TR[*]", "TH"]:
            text = "|\n|"
        case ["Table", "TR[*]", "TH[*]"] | ["Table", "TR[*]", "TD"] | ["Table", "TR[*]", "TD[*]"]:
            text = "|"
        case (
            ["Table", "TR", "TH", *_]
            | ["Table", "TR", "TH[*]", *_]
            | ["Table", "TR", "TD[*]", *_]
            | ["Table", "TR[2]", "TH", *_]
            | ["Table", "TR[2]", "TD", *_]
            | ["Table", "TR[2]", "TH[*]", *_]
            | ["Table", "TR[2]", "TD[*]", *_]
            | ["Table", "TR[*]", "TH[*]", *_]
            | ["Table", "TR[*]", "TH", *_]
            | ["Table", "TR[*]", "TD", *_]
            | ["Table", "TR[*]", "TD[*]", *_]
        ) if text:
            text = f"  {text}  "
        case _:
            text = ""

    return text, elem_type


def extract_ascii_sentence(markdown_text, num_words=4, reverse=False):
    sentences = markdown_text.split("\n")
    for line in sentences[:: -1 if reverse else 1]:
        line_text = markdown_to_plain_text(line)
        words = line_text.split()[:: -1 if reverse else 1]
        for i in range(len(words) - num_words + 1):  # +1 to ensure we have num_words words
            window = " ".join(words[i : i + num_words][:: -1 if reverse else 1])
            if is_ascii(window):
                return window


def markdown_to_plain_text(md):
    # Remove code blocks
    md = re.sub(r"```.*?```", "", md, flags=re.DOTALL)
    # Remove inline code
    md = re.sub(r"`.*?`", "", md)
    # Remove images ![alt](url)
    md = re.sub(r"!\[.*?\]\(.*?\)", "", md)
    # Remove links [text](url)
    md = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", md)
    # Remove emphasis **text**, *text*, __text__, _text_
    md = re.sub(r"(\*\*|__)(.*?)\1", r"\2", md)
    md = re.sub(r"(\*|_)(.*?)\1", r"\2", md)
    # Remove headers # Header
    md = re.sub(r"^\s*#+\s*(.*)", r"\1", md, flags=re.MULTILINE)
    # Remove blockquotes > quote
    md = re.sub(r"^>\s*", "", md, flags=re.MULTILINE)
    # Remove lists - item, * item, + item
    md = re.sub(r"^\s*[-\*\+]\s+", "", md, flags=re.MULTILINE)
    # Remove horizontal rules --- or ***
    md = re.sub(r"\n-{3,}\n", "\n", md)
    md = re.sub(r"\n\*{3,}\n", "\n", md)
    # Remove extra whitespace
    md = re.sub(r"\s+", " ", md)
    return md.strip()


def html_bold_to_markdown(html):
    return re.sub(r"<b>(.*?)</b>", r"**\1**", html)


def is_ascii(s):
    string = copy.deepcopy(s)
    try:
        string.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def word_count(s):
    return len(s.strip().split())
