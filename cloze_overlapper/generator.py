# -*- coding: utf-8 -*-

"""
This file is part of the Cloze Overlapper add-on for Anki

Overlapping Cloze Generator

Copyright: Glutanimate 2016-2017
License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
"""

class ClozeGenerator(object):
    """Cloze generator"""

    cformat = u"{{c%i::%s}}"

    def __init__(self, config, maxfields, settings=None):
        self.config = config
        self.maxfields = maxfields
        if not settings:
            self.settings = config["dflts"]
        else:
            self.settings = settings
        self.start = None
        self.total = None

    def generate(self, items, original=None, keys=None):
        """Returns an array of lists with overlapping cloze deletions"""
        before, prompt, after = self.settings
        length = len(items)
        if self.config["incr"]:
            self.total = length + prompt - 1
            self.start = 1
        else:
            self.total = length
            self.start = prompt
        if self.total > self.maxfields:
            return None, None

        fields = []

        for idx in range(self.start, self.total+1):
            snippets = ["..."] * length
            start_c = self.getClozeStart(idx, prompt)
            start_b = self.getBeforeStart(idx, before, start_c)
            end_a = self.getAfterEnd(idx, after)

            if start_b is not None:
                snippets[start_b:start_c] = items[start_b:start_c]
            if end_a is not None:
                snippets[idx:end_a] = items[idx:end_a]
            snippets[start_c:idx] = self.formatCloze(items[start_c:idx], idx-self.start+1)

            field = self.formatSnippets(snippets, original, keys)
            fields.append(field)

        if self.maxfields > self.total: # delete contents of unused fields
            fields = fields + [""] * (self.maxfields - len(fields))
        fullsnippet = self.formatCloze(items, self.maxfields + 1)
        full = self.formatSnippets(fullsnippet, original, keys)
        return fields, full

    def formatCloze(self, items, nr):
        """Apply cloze deletion syntax to item"""
        res = []
        for item in items:
            if not hasattr(item, "__iter__"): # not an iterable
                res.append(self.cformat % (nr, item))
            else:
                res.append([self.cformat % (nr, i) for i in item])
        return res

    def formatSnippets(self, snippets, original, keys):
        """Insert snippets back into original text, if available"""
        html = original
        if not html:
            return snippets
        for nr, phrase in zip(keys, snippets):
            if phrase == "...": # placeholder, replace all instances
                html = html.replace("{{" + nr + "}}", phrase)
                continue
            if not hasattr(phrase, "__iter__"): # not an iterable
                html = html.replace("{{" + nr + "}}", phrase, 1)
            else:
                for item in phrase:
                    html = html.replace("{{" + nr + "}}", phrase, 1)
        return html

    def getClozeStart(self, idx, target):
        """Determine start index of clozed items"""
        if idx < target or idx > self.total:
            return 0
        return idx-target # looking back from current index

    def getBeforeStart(self, idx, target, start_c):
        """Determine start index of preceding context"""
        if (target == 0 or start_c < 1 
          or (target and self.config["ncl"] and idx == self.total)):
            return None
        if target is None or target > start_c:
            return 0
        return start_c-target

    def getAfterEnd(self, idx, target):
        """Determine end index of following context"""
        left = self.total - idx
        if (target == 0 or left < 1
          or (target and self.config["ncf"] and idx == self.start)):
            return None
        if target is None or target > left:
            return self.total
        return idx+target