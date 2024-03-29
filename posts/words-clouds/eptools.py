# Utils script for working with Latin text

__author__ = [
    "Patrick J. Burns <patrick@diyclassics.org>",
]

import re
import html
import unicodedata
from cltk.alphabet.lat import JVReplacer

replacer = JVReplacer()

# function for removing diacriticals

import sys
import unicodedata

def remove_diacriticals(text_with_diacriticals):
    ''''''
    combining_character_table = dict.fromkeys(c for c in range(sys.maxunicode) 
                                          if unicodedata.combining(chr(c))
                                         )
    
    text_with_diacriticals = unicodedata.normalize('NFD', text_with_diacriticals)
    
    text_without_diacriticals = text_with_diacriticals.translate(combining_character_table)
    
    return text_without_diacriticals

# Helper function for preprocessing
def preprocess(
    text,
    lower=True,
    normalize=True,
    punctuation=False,
    numbers=False,
    unhyphenate=False,
    remove_lines=False,
    remove_spaces=False,
    entities=False,
    diacriticals=True,
    fill=" ",
):

    if not entities:
        text = html.unescape(text)

    if unhyphenate:
        text = re.sub(r"[-»—]\s?\n", "", text, flags=re.MULTILINE)

    if lower:
        text = text.lower()  # Lowercase

    if normalize:
        text = replacer.replace(text)

    if not punctuation:
        # Remove punctuation
        punctuation = "\"#$%&'()*+,/:;<=>@[\]^_`{|}~.?!«»—“-”"
        misc = "¡£¤¥¦§¨©¯°±²³´µ¶·¸¹º¼½¾¿÷·–‘’†•ↄ∞⏑〈〉（）"
        misc += punctuation
        translator = str.maketrans({key: fill for key in misc})
        text = text.translate(translator)

    if not numbers:
        # Remove numbers
        translator = str.maketrans({key: fill for key in "0123456789"})
        text = text.translate(translator)

    if remove_lines:
        text = " ".join(text.split("\n"))

    if remove_spaces:
        text = fill.join(text.split())

    if not diacriticals:
        text = remove_diacriticals(text)
        pass

    # Fix spacing
    text = re.sub(" +", " ", text)

    text = unicodedata.normalize("NFC", text)

    return text.strip()
