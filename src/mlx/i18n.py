# -*- coding: utf-8 -*-

import gettext
import os
import traceback

#------------------------------------------------------------------------------

## @package mlx.i18n
#
# Internationalization support.
#
# This module handles the internationalization support in the logger. It is
# based on the GNU gettext library, and exports the \ref mlx.i18n.xstr "xstr"
# function that returns the translation for a certain key.

#------------------------------------------------------------------------------

_translation = None
_language = None

#------------------------------------------------------------------------------

def setLanguage(programDirectory, language):
    """Setup the internationalization support for the given language."""
    print("i18n.setLanguage", language)
    translation = _getTranslation(programDirectory, language)
    fallback = _getFallbackFor(programDirectory, language)
    if translation is None:
        translation = fallback
    elif fallback is not None:
        translation.add_fallback(fallback)
    assert translation is not None

    global _translation, _language
    _translation = translation
    _language = language
    
#------------------------------------------------------------------------------

def getLanguage():
    """Get the two-letter language code."""
    underscoreIndex = _language.find("_")
    return _language[:underscoreIndex] if underscoreIndex>0 else _language

#------------------------------------------------------------------------------

def xstr(key):
    """Get the string for the given key in the current language.

    If not found, the fallback language is searched. If that is not found
    either, the key itself is returned within curly braces."""
    return _translation.gettext(key)
    
#------------------------------------------------------------------------------

def _getFallbackFor(programDirectory, language):
    """Get the fallback for the given language.

    If the language is English, None is returned, otherwise the English
    language translation."""
    if language in ["en", "en_GB"]:
        return None
    else:
        return _getTranslation(programDirectory, "en")

#------------------------------------------------------------------------------

def _getTranslation(programDirectory, language):
    """Get the translation for the given language."""
    try:
        return gettext.translation("mlx",
                                   localedir = os.path.join(programDirectory,
                                                            "locale"),
                                   languages = [language])
    except:
        traceback.print_exc()
        return None

#------------------------------------------------------------------------------
