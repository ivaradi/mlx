# -*- coding: utf-8 -*-

import sys

#-----------------------------------------------------------------------------

## @package mlx.airports
#
# The mapping of ICAO codes to airport names.
#
# This module contains the mapping of ICAO codes to airport cities and names,
# as well as a \ref getWelcomeMessage "function" to produce a welcome message
# for a certain airport.

#-----------------------------------------------------------------------------

## The mapping of the ICAO codes
airportNames = {
    "VTBS" : ("Bangkok", "Suvarnabhumi"),
    "KJFK" : ("New York", "J. F. Kennedy"),
    "CYYZ" : ("Toronto", "Lester B. Pearson"),
    "UUEE" : ("Moscow", "Sheremetevo"),
    "UKBB" : ("Kiev", "Borispol"),
    "UKOO" : ("Odessa", None),
    "USSS" : ("Yekaterinburg", "Koltsovo"),
    "LTBA" : ("Istanbul", "Atatürk"),
    "LLBG" : ("Tel-Aviv", "Ben Gurion"),
    "HECA" : ("Cairo", None),
    "LCLK" : ("Larnaca", None),
    "LGAV" : ("Athens", "Eleftherios Venizelos"),
    "OLBA" : ("Beirut", "Rafic Hariri"),
    "OSDI" : ("Damascus", None),
    "LGTS" : ("Thessaloniki", "Makedonia"),
    "LIRF" : ("Rome", "Fiumicino"),
    "LIPZ" : ("Venezia", "Tessera"),
    "LATI" : ("Tirana", "Rinas"),
    "LWSK" : ("Skopje", None),
    "LQSA" : ("Sarajevo", "Butmir"),
    "BKPR" : ("Pristina", None),
    "LDZA" : ("Zagreb", "Pleso"),
    "LDSP" : ("Split", "Kastela"),
    "LDDU" : ("Dubrovnik", "Cilipi"),
    "LYPG" : ("Podgorica", "Titograd"),
    "EDDS" : ("Stuttgart Echterdingen", None),
    "EDDF" : ("Frankfurt", "Main"),
    "EDDM" : ("Munich", "Franz-Josef Strauss"),
    "EDDH" : ("Hamburg", None),
    "LFPG" : ("Paris", "Charles de Gaulle"),
    "LFLL" : ("Lyon", "Satolas"),
    "LSGG" : ("Geneva", "Cointrin"),
    "LEMD" : ("Madrid", "Barajas"),
    "EBBR" : ("Brussels", "Zaventem"),
    "EGKK" : ("London", "Gatwick"),
    "EIDW" : ("Dublin", "Collinstown"),
    "EICK" : ("Cork", None),
    "EHAM" : ("Amsterdam", "Schiphol"),
    "EDDT" : ("Berlin", "Tegel"),
    "EFHK" : ("Helsinki", "Vantaa"),
    "EKCH" : ("Copenhagen", "Kastrup"),
    "ESSA" : ("Stockholm", "Arlanda"),
    "ESGG" : ("Gothenburg", None),
    "LKPR" : ("Prague", "Ruznye"),
    "LBSF" : ("Sofia", "Vrhazdebna"),
    "EPWA" : ("Warsaw", "Okecie"),
    "LROP" : ("Bucharest", "Otopeni"),
    "LRTR" : ("Timisoara", None),
    "LRCK" : ("Constanta", None),
    "LRTM" : ("Tirgu Mures", "Vidrasau"),
    "LHBP" : ("Budapest", "Ferihegy"),
    "LHDC" : ("Debrecen", None)
}

#-----------------------------------------------------------------------------

def getWelcomeMessage(icao):
    """Get the welcome message for the airport with the given ICAO code."""
    message = "Welcome to "
    if icao in airportNames:
        (town, airportName) = airportNames[icao]
        message += town if airportName is None \
                   else (town + " " + airportName + " Airport")
    else:
        message += icao
    message += "."
    return message

#-----------------------------------------------------------------------------

if __name__ == "__main__":
    for (town, airport) in airportNames.itervalues():
        print town, airport
    print getWelcomeMessage("LIRF")
    print getWelcomeMessage("LHDC")
    print getWelcomeMessage("LIRN")
    print getWelcomeMessage("LHBP")
    print getWelcomeMessage("EDDF")

#-----------------------------------------------------------------------------
