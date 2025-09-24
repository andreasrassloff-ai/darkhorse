# Darkhorse Aktienanalyse

Dieses Projekt analysiert historische Kursdaten und erstellt einfache Kauf-, Verkaufs- oder Halteempfehlungen. Neben einer Kommandozeilenoberfläche steht ein kleiner WSGI-Webserver zur Verfügung, der die Ergebnisse im Browser visualisiert.

## Voraussetzungen

* Python 3.11 oder neuer
* JSON-Dateien mit Kursdaten (siehe Abschnitt [Datenformat](#datenformat))

Alle Abhängigkeiten befinden sich in der Standardbibliothek, es muss daher nichts installiert werden.

## Datenformat

Die Anwendung erwartet für jede WKN eine JSON-Datei mit historischen Kursen.

```json
{
  "prices": [
    {
      "date": "2024-01-02T00:00:00",
      "open": 190.82,
      "high": 193.50,
      "low": 189.35,
      "close": 192.53,
      "volume": 51234567
    }
  ]
}
```

* Alternativ kann die Datei direkt eine Liste solcher Objekte enthalten.
* `date` muss ein ISO-8601 Datum (mit Uhrzeit) sein. Die Einträge werden automatisch nach Datum sortiert.
* `open`, `high`, `low` und `close` sind Pflichtfelder.
* `volume` ist optional und kann weggelassen oder als `null` angegeben werden.

Standardmäßig sucht die Anwendung Kursdaten in `data/<WKN>.json`.

## Watchlists und WKN-Angaben

Für die Analyse können WKNs direkt auf der Kommandozeile übergeben oder aus einer Watchlist geladen werden.

**Direkte Angabe**

```
python -m app.main --wkn US0378331005
```

Optional lässt sich ein alternativer Pfad zur Kursdatei angeben:

```
python -m app.main --wkn US0378331005=/pfad/zu/apple.json
```

**Watchlist-Dateien**

Watchlists sind JSON-Dateien, die entweder eine Liste oder ein Objekt enthalten dürfen:

```json
[
  "US0378331005",
  { "wkn": "DE0007664039", "path": "../daten/vw.json" }
]
```

```json
{
  "US0378331005": null,
  "DE0007664039": "../daten/vw.json"
}
```

Relative Pfade werden relativ zum Speicherort der Watchlist aufgelöst.


## Schnellstart

Für einen schnellen Start ohne weitere Parameter kann die Anwendung direkt
gestartet werden. Dabei wird die Standard-Watchlist aus
`watchlists/beobachtungsliste.json` geladen und die Weboberfläche auf Port 8000
bereitgestellt:

```
python -m app
```

## Kommandozeilenoberfläche

Die CLI liest historische Daten ein, prüft ob genügend Historie vorliegt und gibt anschließend eine Empfehlung samt Begründung aus.

```
python -m app.main --watchlist watchlists/beobachtungsliste.json --min-history 60
```

Verfügbare Optionen:

* `--wkn`: WKN mit optionalem Pfad zur Kursdatei (`WKN=pfad`). Kann mehrfach angegeben werden.
* `--watchlist`: Pfad zu einer JSON-Watchlist.
* `--min-history`: Minimale Anzahl an Handelstagen (Standard 60).

Der Exit-Code ist `0` bei Erfolg und `1`, wenn eine oder mehrere WKNs nicht verarbeitet werden konnten.

## Weboberfläche

Der Webserver stellt dieselben Daten wie die CLI dar, jedoch in einer kartenbasierten Übersicht im Browser.

```
python -m app.web --watchlist watchlists/beobachtungsliste.json --port 8000
```

* Nach dem Start ist die Oberfläche unter `http://127.0.0.1:8000` erreichbar.
* Weitere WKNs können per Query-Parameter hinzugefügt werden, z. B. `http://127.0.0.1:8000/?wkn=US0378331005`.
* Mit `Strg+C` wird der Server beendet.

## Beispiel-Daten

Im Ordner `data/` befindet sich eine Beispiel-Datei (`US0378331005.json`) für Apple. `watchlists/beobachtungsliste.json` zeigt die erlaubten Watchlist-Formate.

## Entwicklung & Tests

Für manuelle Tests können Sie die oben genannten Befehle verwenden. Automatisierte Tests sind momentan nicht eingerichtet.
