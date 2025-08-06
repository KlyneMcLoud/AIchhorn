import sys
import re
from pathlib import Path

def parse_url(path: Path) -> str:
    # Bei URL-Dateitypen oder .url Dateien
    # Einfach den Pfad als String zurückgeben
    return str(path)


def parse_markdown(path: Path) -> str:
    # Beispiel: lokale Markdown-Datei -> convert to HTML path
    html_path = path.with_suffix('.html')
    # Hier könnte Konvertierung stattfinden
    return str(html_path)


def parse_report(path: Path) -> str:
    # Beispiel-Parser für Reports
    report_dir = path.parent / 'parsed_reports'
    report_dir.mkdir(exist_ok=True)
    output = report_dir / f"parsed_{path.stem}.txt"
    # Hier Parsing-Logik implementieren
    return str(output)


def parse_generic(path: Path) -> str:
    # Fallback-Parser
    return str(path)


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_content_io.py <file_path>", file=sys.stderr)
        sys.exit(1)

    file_arg = sys.argv[1]
    path = Path(file_arg)

    name = path.name.lower()
    # Muster-Dispatcher: Schlüsselwort -> Parser
    parsers = [
        (re.compile(r'https?://'), parse_url),
        (re.compile(r'\.url$'), parse_url),
        (re.compile(r'\.md$'), parse_markdown),
        (re.compile(r'report'), parse_report),
    ]

    for pattern, func in parsers:
        if pattern.search(name):
            output = func(path)
            print(output)
            return

    # Default
    print(parse_generic(path))

if __name__ == '__main__':
    main()
