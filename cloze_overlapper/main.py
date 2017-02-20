# -*- coding: utf-8 -*-

"""
This file is part of the Cloze Overlapper add-on for Anki

Copyright: Glutanimate 2016-2017
License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
"""

from aqt import editor
from aqt.utils import tooltip
from anki.utils import stripHTML
from anki.hooks import addHook

from BeautifulSoup import BeautifulSoup

# CONSTANTS

ol_cloze_max = 20
ol_cloze_dfltopts = (1,1,0)
ol_cloze_no_context_first = False
ol_cloze_no_context_last = False
ol_cloze_incremental_ends = False
ol_cloze_model = "Overlapping Cloze"
ol_cloze_fld_prefix = "Text"
ol_cloze_fld_full = "Full"
ol_cloze_fld_options = "Options"
ol_cloze_fld_original = "Original"

def getOptions(field):
    """Return options tuple. Fall back to defaults if necessary."""
    options = field.replace(" ", "").split(",")
    dflts = ol_cloze_dfltopts
    if not field or not options:
        return ol_cloze_dfltopts, True
    opts = []
    for i in options:
        try:
            opts.append(int(i))
        except ValueError:
            opts.append(None)
    length = len(opts)
    if length == 3 and isinstance(opts[1], int):
        return tuple(opts), False
    elif length == 2 and isinstance(opts[0], int):
        return (opts[1], opts[0], opts[1]), False
    elif length == 1 and isinstance(opts[0], int):
        return (dflts[0], opts[0], dflts[2]), False
    return False, False

def getClozeStart(idx, target, total):
    """Determine start index of clozed items"""
    if idx < target or idx > total:
        return 0
    return idx-target # looking back from current index

def getBeforeStart(start, idx, target, total, start_c):
    """Determine start index of preceding context"""
    if (target == 0 or start_c < 1 
      or (target and ol_cloze_no_context_last and idx == total)):
        return None
    if target is None or target > start_c:
        return 0
    return start_c-target

def getAfterEnd(start, idx, target, total):
    """Determine ending index of following context"""
    left = total - idx
    if (target == 0 or left < 1
      or (target and ol_cloze_no_context_first and idx == start)):
        return None
    if target is None or target > left:
        return total
    return idx+target

def generateOlClozes(self, items, options):
    """Returns an array of lists with overlapping cloze deletions"""
    before, prompt, after = options
    length = len(items)
    if ol_cloze_incremental_ends:
        total = length + prompt - 1
        start = 1
    else:
        total = length
        start = prompt
    if total > ol_cloze_max:
        return False
    fields = []
    cloze_format = u"{{c%i::%s}}"
    for idx in range(start,total+1):
        field = ["..."] * length
        start_c = getClozeStart(idx, prompt, total)
        start_b = getBeforeStart(start, idx, before, total, start_c)
        end_a = getAfterEnd(start, idx, after, total)
        if start_b is not None:
            field[start_b:start_c] = items[start_b:start_c]
        if end_a is not None:
            field[idx:end_a] = items[idx:end_a]
        field[start_c:idx] = [cloze_format % (idx-start+1, l) for l in items[start_c:idx]]
        fields.append(field)
    if ol_cloze_max > total: # delete contents of unused fields
        fields = fields + [""] * (ol_cloze_max - len(fields))
    full = [cloze_format % (ol_cloze_max+1, l) for l in items]

    return fields, full

def processOriginalText(html):
    """Convert original field HTML to plain text and determine markup tags"""
    soup = BeautifulSoup(html)
    text = soup.getText("\n") # will need to be updated for bs4
    items = text.splitlines()
    if soup.findAll("ol"):
        markup = "ol"
    elif soup.findAll("ul"):
        markup = "ul"
    else:
        markup = "div"
    return items, markup

def processField(field, markup):
    """Convert field contents back to HTML"""
    if markup == "div":
        tag_start, tag_end = "", ""
        tag_items = "<div>{0}</div>"
    else:
        tag_start = '<{0}>'.format(markup)
        tag_end = '</{0}>'.format(markup)
        tag_items = "<li>{0}</li>"
    lines = "".join(tag_items.format(line) for line in field)
    return tag_start + lines + tag_end

def updateNote(note, fields, full, markup, defaults):
    """Write changes to note"""
    for idx, field in enumerate(fields):
        name = ol_cloze_fld_prefix + str(idx+1)
        note[name] = processField(field, markup)

    note[ol_cloze_fld_full] = processField(full, markup)

    if defaults:
        note[ol_cloze_fld_options] = ",".join(str(i) for i in ol_cloze_dfltopts)

def insertOverlappingCloze(self):
    """Main function, called on button press"""
    mname = self.note.model()["name"] # make sure the right model is set
    if mname != ol_cloze_model:
        tooltip(u"Can only generate overlapping clozes on<br>'%s' note type" % ol_cloze_model)
        return False

    self.web.eval("""saveField("key");""") # save field
    original = self.note[ol_cloze_fld_original]

    if not original:
        tooltip(u"Please enter some text in the %s field" % ol_cloze_fld_original)
        return False

    items, markup = processOriginalText(original)

    if not items:
        tooltip("Could not find items to cloze. Please check your input.")
        return False
    if len(items) < 3:
        tooltip("Please enter at least three items to cloze.")
        return False

    fld_opts = self.note[ol_cloze_fld_options]
    options, defaults = getOptions(fld_opts)

    fields, full = self.generateOlClozes(items, options)
    if not fields:
        tooltip("Error: More clozes than the note type can handle.")
        return False

    updateNote(self.note, fields, full, markup, defaults)

    self.web.eval("saveField('key');") # save current field
    self.loadNote()
    self.web.eval("focusField(%d);" % self.currentField)


def onSetupButtons(self):
    self._addButton("Cloze Overlapper", self.insertOverlappingCloze,
        _("Alt+Shift+C"), "Insert Overlapping Clozes (Alt+Shift+C)", 
        text="[.]]", size=True)

editor.Editor.insertOverlappingCloze = insertOverlappingCloze
editor.Editor.generateOlClozes = generateOlClozes
addHook("setupEditorButtons", onSetupButtons)