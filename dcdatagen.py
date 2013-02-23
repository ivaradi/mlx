#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Script that generates the delay code data files from a common data base
#
# It generates the following files:
# - src/mlx/gui/dcdata.py: a Python module that contains the data structures
#   describing the delay code information for each aircraft type.
# - locale/en/mlx_delay.po, local/hu/mlx_delay.po: PO files containing the
#   delay code texts. Those texts are referred to from dcdata.py

#----------------------------------------------------------------------------

import os

#----------------------------------------------------------------------------

# The list of language codes. The strings should be arrays of at least this
# length
languageCodes = ["en", "hu"]

#----------------------------------------------------------------------------

# Row type: a caption
CAPTION = 1

# Row type: an actual delay code
DELAYCODE = 2

#----------------------------------------------------------------------------

# Prefixes for the generated tables
tablePrefixes = [ "modern", "ot" ]

# Type groups
typeGroups = [ ["B736", "B737", "B738", "B738C", "B733", "B734", "B735",
                "DH8D", "B762", "B763", "CRJ2", "F70" ],
               ["DC3", "T134", "T154", "YK40"] ]

#----------------------------------------------------------------------------

# The associated row or column is for the modern fleet
FOR_MODERN = 1

# The associated row or column is for the old-timer fleet
FOR_OT = 2

#----------------------------------------------------------------------------

# The complete delay code table
table = (("info_delay_",
          "lambda row: row[0].strip()"),
         [ ["MA", "MA"], ["IATA", "IATA"], ["Code", "Kód"],
           ["Name", "Név"],["Description", "Leírás" ] ],
         [ FOR_OT, FOR_MODERN | FOR_OT, FOR_MODERN,
           FOR_OT | FOR_MODERN, FOR_OT | FOR_MODERN ],
         [ (CAPTION, FOR_MODERN | FOR_OT,
            ["Others", "Egyebek"] ),
           (DELAYCODE, FOR_OT,
            ["012      ", "01      ", None,
             ["LATE PARTS OR MATERIALS", "KÉSEI ALKATRÉSZ VAGY ANYAG"],
             ["Parts and/or materials shipped late from the warehouse",
              "Kései alkatrész és/vagy anyagkiszállítás a raktárból"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "06    ", "OA     ",
             ["NO GATES/STAND AVAILABLE", "NINCS SZABAD KAPU/ÁLLÓHELY"],
             ["Due to own airline activity",
              "Saját tevékenység miatt"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "09", "SG",
             ["SCHEDULED GROUND TIME", "ÜTEMEZETT FORDULÓ IDŐ"],
             ["Planned turnaround time less than declared minimum",
              "A tervezett forduló idő rövidebb a minimálisnál"]]),
           (CAPTION, FOR_MODERN | FOR_OT,
            ["Passenger and baggage",
             "Utas és poggyászkezelés"] ),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["111", "11", "PD",
             ["LATE CHECK-IN", "KÉSEI JEGYKEZELÉS"],
             ["Check-in reopened for late passengers",
              "Check-in járatzárás után"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["121", "12", "PL",
             ["LATE CHECK-IN", "KÉSEI JEGYKEZELÉS"],
             ["Check-in not completed by flight closure time",
              "Torlódás az indulási csarnokban"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["132", "13", "PE",
             ["CHECK-IN ERROR", "JEGYKEZELÉSI HIBA"],
             ["Error with passenger or baggage details",
              "Téves utas és poggyászfelvétel"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["142", "14", "PO",
             ["OVERSALES", "TÚLKÖNYVELÉS"],
             ["Booking errors – not resolved at check-in",
              "Téves könyvelés, a jegykezelés során nem megoldott"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "15", "PH",
             ["BOARDING", "BESZÁLLÍTÁS"],
             ["Discrepancies and paging, missing checked in passengers",
              "Beszállítási rendellenesség, hiányzó utasok"]]),
           (DELAYCODE, FOR_OT,
            ["151", "15", None,
             ["BOARDING", "BESZÁLLÍTÁS"],
             ["Boarding discrepancies due to the passenger's fault",
              "Beszállítási rendellenesség utas hibájából"]]),
           (DELAYCODE, FOR_OT,
            ["152", "", None,
             ["BOARDING", "BESZÁLLÍTÁS"],
             ["Boarding discrepancies due to the tranzit's fault",
              "Beszállítási rendellenesség tranzit hibájából"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["161", "16", "PS",
             ["COMMERCIAL PUBLICITY/\nPASSENGER CONVENIENCE",
              "NYILVÁNOS FOGADÁS/\nUTASKÉNYELMI SZEMPONTOK"],
             ["Local decision to delay for VIP or press; \ndelay due to offload of passengers following family bereavement",
              "Késleltetés helyi döntés alapján reptérzár,\nbetegség/halál, VIP, sajtó, TV miatt"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "17", "PC",
             ["CATERING ORDER", "CATERING MEGRENDELÉS"],
             ["Late or incorrect order given to supplier",
              "Kései vagy téves megrendelés leadása a szállítónak"]]),
           (DELAYCODE, FOR_OT,
            ["171", "17", None,
             ["CATERING ORDER", "CATERING MEGRENDELÉS"],
             ["Late catering order in case of an additional group of people",
              "Kései catering megrendelés, extra csoport jelentkezése esetén"]]),
           (DELAYCODE, FOR_OT,
            ["172", "", None,
             ["CATERING ORDER", "CATERING MEGRENDELÉS"],
             ["Late catering order due to negligence",
              "Kései catering megrendelés gondatlanságból"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["182", "18", "PD",
             ["BAGGAGE PROCESSING", "POGGYÁSZKEZELÉS"],
             ["Késő vagy tévesen szortírozott poggyász",
              "Late or incorrectly sorted baggage"]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           # (DELAYCODE, FOR_MODERN | FOR_OT,
           #  ["", "", "",
           #   ["", ""],
           #   ["",
           #    ""]]),
           ])

#-------------------------------------------------------------------------------

def generateMsgStr(file, text):
    """Generate an 'msgstr' entry for the given text."""
    lines = text.splitlines()
    numLines = len(lines)
    if numLines==0:
        print >> file, "msgstr \"\""
    elif numLines==1:
        print >> file, "msgstr \"%s\"" % (lines[0])
    else:
        print >> file, "msgstr \"\""
        for i in range(0, numLines):
            print >> file, "\"%s%s\"" % (lines[i], "" if i==(numLines-1) else "\\n")
    print >> file

#-------------------------------------------------------------------------------

def generateFiles(baseDir):
    """Generate the various files."""
    dcdata = None
    poFiles = []

    try:
        dcdataPath = os.path.join(baseDir, "src", "mlx", "gui", "dcdata.py")
        dcdata = open(dcdataPath, "wt")

        numLanguages = len(languageCodes)
        for language in languageCodes:
            poPath = os.path.join(baseDir, "locale", language, "mlx_delay.po")
            poFile = open(poPath, "wt")
            poFiles.append(poFile)
            print >> poFile, "msgid \"\""
            print >> poFile, "msgstr \"\""
            print >> poFile, "\"Content-Type: text/plain; charset=utf-8\\n\""
            print >> poFile, "\"Content-Transfer-Encoding: 8bit\\n\""

        (baseData, headings, headingFlags, rows) = table
        (poPrefix, extractor) = baseData

        for i in range(0, len(headings)):
            heading = headings[i]
            for j in range(0, numLanguages):
                poFile = poFiles[j]
                print >> poFile, "msgid \"%sheading%d\"" % (poPrefix, i)
                generateMsgStr(poFile, heading[j])


        rowIndex = 0
        for (type, _tableMask, columns) in rows:
            if type==CAPTION:
                for i in range(0, numLanguages):
                    poFile = poFiles[i]
                    print >> poFile, "msgid \"%srow%d\"" % (poPrefix, rowIndex)
                    generateMsgStr(poFile, columns[i])
            elif type==DELAYCODE:
                columnIndex = 0
                for column in columns:
                    if isinstance(column, list):
                        for i in range(0, numLanguages):
                            poFile = poFiles[i]
                            print >> poFile, "msgid \"%srow%d_col%d\"" % \
                              (poPrefix, rowIndex, columnIndex)
                            generateMsgStr(poFile, column[i])
                    columnIndex += 1
            rowIndex += 1

        print >> dcdata, "import mlx.const as const"
        print >> dcdata, "from mlx.i18n import xstr"
        print >> dcdata
        print >> dcdata, "CAPTION = 1"
        print >> dcdata, "DELAYCODE = 2"

        tableMask = 1
        for i in range(0, len(tablePrefixes)):
            print >> dcdata, "_%s_data = (" % (tablePrefixes[i],)
            print >> dcdata, "    %s," % (extractor,)
            print >> dcdata, "    [",

            columnIndexes = []
            for j in range(0, len(headings)):
                if ( (headingFlags[j]&tableMask)==tableMask ):
                    if columnIndexes:
                        print >> dcdata, ",",
                    print >> dcdata, "xstr(\"%sheading%d\")" % (poPrefix, j),
                    columnIndexes.append(j)

            print >> dcdata, "],"

            print >> dcdata, "    ["

            rowIndex = 0
            for (type, mask, columns) in rows:
                if (mask&tableMask)!=tableMask:
                    rowIndex += 1
                    continue

                if type==CAPTION:
                    print >> dcdata, "        (CAPTION, xstr(\"%srow%d\"))," % \
                      (poPrefix, rowIndex)
                elif type==DELAYCODE:
                    print >> dcdata, "        (DELAYCODE, ["
                    for j in columnIndexes:
                        column = columns[j]
                        if j!=columnIndexes[0]:
                            print >> dcdata, ","
                        if isinstance(column, list):
                            print >> dcdata, "            xstr(\"%srow%d_col%d\")"  % \
                              (poPrefix, rowIndex, j),
                        else:
                            print >> dcdata, "            \"%s\""  % \
                              (column,),
                    print >> dcdata, "] ),"
                rowIndex += 1

            print >> dcdata, "    ]"

            print >> dcdata, ")"
            print >> dcdata

            tableMask <<= 1

        print >> dcdata, "def getTable(aircraftType):"
        first = True
        for i in range(0, len(tablePrefixes)):
            tablePrefix = tablePrefixes[i]
            for typeSuffix in typeGroups[i]:
                print >> dcdata, "    %s aircraftType==const.AIRCRAFT_%s:" % \
                  ("if" if first else "elif", typeSuffix)
                print >> dcdata, "        return _%s_data" % (tablePrefix,)
                first = False

        print >> dcdata, "    else:"
        print >> dcdata, "        return None"
    finally:
        for poFile in poFiles:
            poFile.close()
        if dcdata is not None:
            dcdata.close()

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    generateFiles(os.path.dirname(__file__))
