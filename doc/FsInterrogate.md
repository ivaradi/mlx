A logger a Microsoft Flight Simulatorral az FSUIPC nevű kiegészítőn keresztül tartja a kapcsolatot. Az FSUIPC a szimulátor különféle belső paramétereit (pl. a repülőgép magassága, sebessége, stb.) teszi elérhetővé, és sok esetben módosíthatóvá. Az egyes paramétereket egy cím vagy offset azonosítja, ami egy szám.

Egyes repülőgép modellek az egyes paramétereket nem a szabványos offseteken jelenítik meg, vagy olyan, a logger számára érdekes paramétereket is megjelenítenek, amelyekhez nem tartozik "szabványos" vagy "ismert" offset. Ilyen esetben az FSInterrogate programmal lehetséges kideríteni, hogy melyek a kérdéses offsetek. A program használatához töltsük le az ehhez az oldalhoz csatolt két file-t ([FSInterrogate2std.exe](/uploads/fccfc9c5ba7c2c5dd327ce907a499be2/FSInterrogate2std.exe) és [FSUIPC.FSI](/uploads/cf18388bfc40f8fc8e85f1bbf3b0c970/FSUIPC.FSI)) és tegyük őket ugyanabba a könyvtárba. Az alábbiakban leírjuk, hogy hogyan kell egy kérdéses offsetet meghatározni a PMDG FS2004-hez készírett Boeing 737NG modelljének STD gombjának példáján keresztül.

  1. A vizsgálat azon alapul, hogy a vizsgálandó paramétert két érték között kell állítgatni. Ezért először is döntsük el, hogy melyik lesz ez a két érték. Egy kétállású kapcsolónál egyszerű a helyzet: az első érték legyen a kikapcsolt állapot, a másik a bekapcsolt (vagy fordítva, csak határozzuk meg egyértelműen). Egy bonyolultabb esetben, például egy rádió frekvenciánál ez lehet két eltérő frekvenciaérték. Példánkban az STD gombot vizsgáljuk: ennek kikapcsolt állapota lesz az első érték, bekapcsolt állapota a második.
  1. Indítsuk el az FSInterrogate2std.exe programot. Az alábbi ablak jelenik meg:
     ![image](/uploads/c38c9af5c663f09e868a8d85b13d26c3/image.png)
  1. Kattintsunk a piros nyíllal jelzett **Interrogate** gombra. Ekkor ilyenné változik az ablak:
     ![image](/uploads/eb3804d7f2e2515ac92b72b116364c1f/image.png)
  1. Az 1. számú nyíllal jelzett beállításnál ellenőrizzük, hogy _From Addr:_ alatt 0000 szerepeljen, a _To:_ alatt pedig FFFF. A 2. számú nyílnál válasszuk ki a _Both (Byte-Align)_ lehetőséget (ha a fejlesztő nem kér mást). A 3. számú nyílnál pedig legyen _Both "Normal" and 3rd Party_, illetve alatta minden legyen kijelölve a _Simulators_ és a _Categories listában_. Ezután kattintsunk a 4. számú nyíllal jelzett **Setup Fields** gombra.
     ![image](/uploads/1a31f4f2c305dd0029b82b98e2195063/image.png)
  1. A jobb oldali részen megjelentek az offsetek, amelyeket a program figyelni fog. Ha végig legörgetjük a listát, látni fogjuk, hogy az utolsó offset az FFFF. Kattintsunk az 1. számú nyíllal jelzett _Select all_ gombra az összes offset kijelöléséhez, majd a 2. számú nyíllal jelzett **3-Scan Locater** gombra. Ekkor egy kisebb, _3-Scan Locater_ feliratú ablak jelenik meg:
     ![image](/uploads/02d8da7c393a5de8f2ad94bff963ca66/image.png)
  1. Az 1. számú nyíllal jelzett _Treat Unknown variables as_ értéket állítsuk át _U8_-ra (vagy ha mást kért a fejlesztő, akkor arra).
  1. A szimulátorban állítsuk elő a mérni kívánt paraméter első számú értékét, amely esetünkben az STD gomb kikapcsolt állapota. Ezt abból láthatjuk, hogy a nyíllal jelzett légnyomásérték nem STD: 
     
     ![image](/uploads/8a297f404397910ff477b690bcdf7089/image.png)
  1. Ezután a _3-Scan Locater_ ablakban nyomjuk meg a fenti ábrán a 2. számú nyíllal jelzett **1st scan** gombot. Ekkor a program kiolvassa a szimulátorból az értékeket, majd a **2nd scan** gomb válik aktívvá:
     ![image](/uploads/73d8dc151ecbe59224005673fca97318/image.png)
  1. A szimulátorban állítsuk be a második értékét a mérni kívánt paraméternek. Ez esetünkben az STD gomb bekapcsolt állapota:
     ![image](/uploads/2dbde42d059a799c2dc92ddc199c1a27/image.png)
  1. Nyomjuk meg a **2nd scan** gombot a _3-Scan Locater_ ablakban. Ekkor a program kiolvassa az újabb értékeket, és a **3rd scan** gomb válik aktívvá. 
  1. Állítsuk vissza a szimulátorban az első számú értéket, amely a példában az STD gomb kikapcsolt állapot.
  1. Nyomjuk meg a **3rd scan** gombot. Ekkor a program harmadszorra is kiolvassa az értékeket, majd megjeleníti az eredményt:
    ![image](/uploads/2b14d45815673a7594f00ed82b9e365d/image.png)
  1. Láthatjuk, hogy itt több offsetet talált a program. Ezek közül a feszültségeket tartalmazók nyilván kizárhatók, de a többinél nem olyan egyértelmű a helyzet. Ilyenkor végre lehet hajtani az opcionális lekérdezéseket a **4th scan**, majd a **5th scan** gombokkal, ami tovább szűkítheti az offsetek körét. Ezen ismertető szerkesztése közben a 6202-es és a 6225-ös offsetek maradtak. A 6225-ösből lehet látni, hogy több bit is változik, míg a 6202-nél mindig csak egy. Ez igen valószínűvé teszi, hogy a 6202-es a keresett offset. Ha ennél több és nem ennyire egyértelmű offset marad, akkor további próbákat lehet tenni, és megfigyelni, hogy melyik az az offset, amelyik mindig szerepel, és mindig ugyanolyan értékeket vesz fel, vagy legalábbis ugyanúgy változik. 

További megerősítésként, ha van néhány "jelölt" offsetünk, a következő vizsgálatot is elvégezhetjük: 

  1. Lépjünk ki a _3-Scan Locater_ ablakból, majd konfiguráljuk be a programot, hogy csak a kérdéses offsetet vizsgálja:
    ![image](/uploads/73b66b90df4c7434fbd5d647eb97a44a/image.png)
  1. A _From Addr:_ és a _To:_ mezőkbe írjuk bele a vizsgálni kívánt offsetet (1. számú nyíl).
  1. Nyomjuk meg a **Setup Fields** gombot (2. számú nyíl).
  1. Jelöljük ki a sort a táblázatban (3. számú nyíl).
  1. Jelölük be a 4. számú nyíl által jelzett **Continues** checkboxot. 
  1. Ekkor a program elkezdi folyamatosan, újra és újra beolvasni a vizsgált offset értékét. Helyezzük el úgy a program és a szimulátor ablakát, hogy a szimulátorból látszódjék az állítani kívánt kapcsoló vagy gomb, vagy amit vizsgálunk, az FSInterrogate-ből pedig a táblázat kijelölt sora. Állítgassuk a szimulátorban ide-oda a vizsgált paramétert (tehát jelen példánkban nyomogassuk az STD gombot), és figyeljük meg, hogy a táblázatban, a kijelölt sorban az érték szinkronban változik-e azzal, amit a szimulátorban csinálunk.

A fejlesztéshez szükség van a megtalált offset(ek)re és annak (azok) értékeire, amelyeket az ide-oda állítgatás közben felvesz(nek). Ez alapján jó eséllyel készíthető egy teszt verzió, amivel ellenőrizhető , hogy jó offseteket találtunk-e.