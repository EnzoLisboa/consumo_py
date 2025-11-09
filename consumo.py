"""Ferramenta para estimar consumo de energia a partir de arquivos CSV.

O script percorre um ou mais arquivos (ou diretórios contendo CSVs) e
integra a potência registrada ao longo do tempo para estimar o consumo em
Watt-hora (Wh) e quilowatt-hora (kWh).

Execute ``python consumo.py --help`` para detalhes de uso.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple


@dataclass
class Sample:
    timestamp: datetime
    power_watts: float


@dataclass
class Report:
    path: Path
    samples: List[Sample]
    energy_wh: float

    @property
    def energy_kwh(self) -> float:
        return self.energy_wh / 1000.0

    @property
    def start(self) -> Optional[datetime]:
        return self.samples[0].timestamp if self.samples else None

    @property
    def end(self) -> Optional[datetime]:
        return self.samples[-1].timestamp if self.samples else None

    @property
    def duration_hours(self) -> Optional[float]:
        if len(self.samples) < 2:
            return None
        delta = self.samples[-1].timestamp - self.samples[0].timestamp
        return delta.total_seconds() / 3600.0


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "Arquivos CSV ou diretórios contendo CSVs a serem processados."
        ),
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="Separador de campos do CSV (padrão: ',').",
    )
    parser.add_argument(
        "--time-column",
        default="timestamp",
        help="Nome da coluna contendo os instantes de medição (padrão: 'timestamp').",
    )
    parser.add_argument(
        "--time-format",
        default=None,
        help=(
            "Formato explícito do timestamp usando diretivas strftime. "
            "Se omitido, o valor será interpretado como ISO 8601."
        ),
    )
    parser.add_argument(
        "--power-column",
        default="power",
        help=(
            "Coluna com valores de potência. Informe string vazia quando "
            "usar tensão e corrente."
        ),
    )
    parser.add_argument(
        "--voltage-column",
        default=None,
        help="Coluna com os valores de tensão (em volts).",
    )
    parser.add_argument(
        "--current-column",
        default=None,
        help="Coluna com os valores de corrente (em ampères).",
    )
    parser.add_argument(
        "--power-scale",
        type=float,
        default=1.0,
        help=(
            "Fator multiplicativo aplicado à potência. Útil para converter "
            "porcentagens em watts."
        ),
    )
    return parser.parse_args(argv)


def parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    text = text.replace(" ", "")
    text = text.replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None
    if number != number:  # NaN check
        return None
    return number


def parse_timestamp(value: str, time_format: Optional[str]) -> Optional[datetime]:
    text = (value or "").strip()
    if not text:
        return None
    if time_format:
        try:
            return datetime.strptime(text, time_format)
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def load_samples(
    path: Path,
    *,
    delimiter: str,
    time_column: str,
    time_format: Optional[str],
    power_column: Optional[str],
    voltage_column: Optional[str],
    current_column: Optional[str],
    power_scale: float,
) -> List[Sample]:
    samples: List[Sample] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        headers = reader.fieldnames or []
        if time_column not in headers:
            raise ValueError(
                f"Coluna de tempo '{time_column}' não encontrada em {path.name}."
            )

        use_power_column = bool(power_column)
        if use_power_column and power_column not in headers:
            raise ValueError(
                f"Coluna de potência '{power_column}' não encontrada em {path.name}."
            )
        if not use_power_column:
            if not voltage_column or not current_column:
                raise ValueError(
                    "Informe --voltage-column e --current-column quando não houver "
                    "coluna de potência."
                )
            missing: List[str] = [
                col
                for col in (voltage_column, current_column)
                if col not in headers
            ]
            if missing:
                joined = ", ".join(missing)
                raise ValueError(
                    f"Colunas ausentes no arquivo {path.name}: {joined}."
                )

        for row in reader:
            raw_time = row.get(time_column, "")
            timestamp = parse_timestamp(raw_time, time_format)
            if timestamp is None:
                continue

            if use_power_column:
                power_value = parse_float(row.get(power_column or ""))
            else:
                voltage = parse_float(row.get(voltage_column or ""))
                current = parse_float(row.get(current_column or ""))
                if voltage is None or current is None:
                    continue
                power_value = voltage * current

            if power_value is None:
                continue

            samples.append(Sample(timestamp=timestamp, power_watts=power_value * power_scale))

    samples.sort(key=lambda sample: sample.timestamp)
    return samples


def integrate_energy(samples: Sequence[Sample]) -> float:
    if len(samples) < 2:
        return 0.0
    energy_ws = 0.0
    for previous, current in zip(samples, samples[1:]):
        delta_seconds = (current.timestamp - previous.timestamp).total_seconds()
        if delta_seconds <= 0:
            continue
        average_power = (previous.power_watts + current.power_watts) / 2.0
        energy_ws += average_power * delta_seconds
    return energy_ws / 3600.0


def analyze_file(path: Path, args: argparse.Namespace) -> Report:
    samples = load_samples(
        path,
        delimiter=args.delimiter,
        time_column=args.time_column,
        time_format=args.time_format,
        power_column=args.power_column,
        voltage_column=args.voltage_column,
        current_column=args.current_column,
        power_scale=args.power_scale,
    )
    energy_wh = integrate_energy(samples)
    return Report(path=path, samples=list(samples), energy_wh=energy_wh)


def iter_csv_files(paths: Iterable[Path]) -> Iterator[Path]:
    for path in paths:
        if path.is_dir():
            for csv_file in sorted(path.glob("*.csv")):
                if csv_file.is_file():
                    yield csv_file
        elif path.is_file():
            yield path
        else:
            raise FileNotFoundError(f"Caminho inexistente: {path}")


def format_datetime(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "N/D"


def print_report(report: Report) -> None:
    print(f"Arquivo: {report.path}")
    print("Resumo das medições:")
    print(f"  Início: {format_datetime(report.start)}")
    print(f"  Fim: {format_datetime(report.end)}")
    if report.duration_hours is None:
        print("  Duração: N/D")
    else:
        print(f"  Duração: {report.duration_hours:.2f} h")
    print(f"  Amostras válidas: {len(report.samples)}")
    print("")
    print("Consumo estimado:")
    print(f"  {report.energy_wh:.2f} Wh")
    print(f"  {report.energy_kwh:.4f} kWh")
    print("".rstrip())


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    paths = [Path(p) for p in args.paths]
    reports: List[Report] = []

    for csv_path in iter_csv_files(paths):
        try:
            report = analyze_file(csv_path, args)
        except Exception as exc:  # pragma: no cover - feedback relevante ao usuário
            print(f"Erro ao processar {csv_path}: {exc}")
            continue
        reports.append(report)
        print_report(report)

    if len(reports) > 1:
        total_wh = sum(report.energy_wh for report in reports)
        total_samples = sum(len(report.samples) for report in reports)
        overall_start = min((r.start for r in reports if r.start), default=None)
        overall_end = max((r.end for r in reports if r.end), default=None)
        print("Resumo consolidado:")
        print(f"  Arquivos: {len(reports)}")
        print(f"  Amostras válidas: {total_samples}")
        print(f"  Início: {format_datetime(overall_start)}")
        print(f"  Fim: {format_datetime(overall_end)}")
        if overall_start and overall_end:
            total_hours = (overall_end - overall_start).total_seconds() / 3600.0
            print(f"  Intervalo: {total_hours:.2f} h")
        else:
            print("  Intervalo: N/D")
        print("  Consumo total:")
        print(f"    {total_wh:.2f} Wh")
        print(f"    {total_wh/1000.0:.4f} kWh")


if __name__ == "__main__":
    main()

