# Darkhorse Monero-Analyse

Dieses Projekt analysiert historische Monero-Kurse und erstellt einfache Kauf-, Verkaufs- oder Halteempfehlungen. Neben einer Kommandozeilenoberfläche steht ein kleiner WSGI-Webserver zur Verfügung, der die Ergebnisse im Browser visualisiert.

## Voraussetzungen

* Python 3.11 oder neuer
* JSON-Dateien mit Kursdaten (siehe Abschnitt [Datenformat](#datenformat))

Alle Abhängigkeiten befinden sich in der Standardbibliothek, es muss daher nichts installiert werden.

## Datenformat

Die Anwendung erwartet eine JSON-Datei mit historischen Monero-Kursen.

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

Standardmäßig sucht die Anwendung Kursdaten in `data/monero.json`.

## Schnellstart

Für einen schnellen Start ohne weitere Parameter kann die Anwendung direkt
gestartet werden. Dabei wird die Standarddatei `data/monero.json` geladen und die Weboberfläche auf Port 8000 bereitgestellt:

```
python -m darkhorse
```

> **Hinweis:** Seit Python 3.13 existiert bereits ein Standardpaket mit dem
> Namen `app`, wodurch `python -m app` auf manchen Systemen scheitert. Der
> Paketname des Projekts lautet deshalb `darkhorse`.

Falls bestehende Skripte weiterhin `python -m app` verwenden, stellt das
Projekt nun ein dünnes Kompatibilitätspaket bereit, das alle Funktionen an die
neuen `darkhorse`-Module weiterreicht. Für neue Installationen wird dennoch die
Verwendung des Namens `darkhorse` empfohlen.

### Live-Trading-Demo

Wer statt historischer Daten den aktuellen Markt beobachten möchte, kann die
Live-Demo starten. Sie lädt jede Minute aktuelle XMR/USD-Kurse von CoinGecko,
wendet die Analyse darauf an und tauscht den kompletten Bestand zwischen XMR und
USD hin und her. Standardmäßig beginnt die Demo mit **1 XMR** und keinem USD.

```
python -m darkhorse.trader --interval 60 --iterations 5
```

* `--interval` steuert den Abstand zwischen zwei Trades (in Sekunden).
* `--iterations` begrenzt die Laufzeit (0 = endlos).
* `--history-limit` legt fest, wie viele Minutenkerzen zur Analyse geladen
  werden.

> ⚠️ Für die Live-Demo ist ein Internetzugang erforderlich. Bei kurzfristigen
> API-Ausfällen überspringt das Skript die betroffene Runde und versucht es eine
> Minute später erneut.

=======

## Kommandozeilenoberfläche

Die CLI liest historische Daten ein, prüft ob genügend Historie vorliegt und gibt anschließend eine Empfehlung samt Begründung aus.

```

python -m darkhorse.main --data data/monero.json --min-history 60

```

Verfügbare Optionen:

* `--data`: Pfad zur JSON-Datei mit Monero-Kursen (Standard `data/monero.json`).
* `--min-history`: Minimale Anzahl an Handelstagen (Standard 60).

Der Exit-Code ist `0` bei Erfolg und `2`, wenn die Eingabeparameter ungültig sind (z. B. Datei nicht gefunden).

## Weboberfläche

Der Webserver stellt dieselben Daten wie die CLI dar, jedoch in einer kartenbasierten Übersicht im Browser.

```

python -m darkhorse.web --data data/monero.json --port 8000

```

* Nach dem Start ist die Oberfläche unter `http://127.0.0.1:8000` erreichbar.
* Mit `Strg+C` wird der Server beendet.

## Beispiel-Daten

Im Ordner `data/` befindet sich eine Beispiel-Datei (`monero.json`) mit fiktiven Monero-Kursen.

## Entwicklung & Tests

Für manuelle Tests können Sie die oben genannten Befehle verwenden. Automatisierte Tests sind momentan nicht eingerichtet.
