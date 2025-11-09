"""Ferramenta para estimar consumo de energia a partir de arquivos CSV.

O script percorre um ou mais arquivos (ou diretórios contendo CSVs) e
integra a potência registrada ao longo do tempo para estimar o consumo em
quilowatt por hora (kW/h).

Execute ``python consumo.py --help`` para detalhes de uso.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence


SYSTEM_TOTAL_POWER_WATTS = 60.0


@dataclass
class Sample:
    timestamp: datetime
    power_percent: float
    power_watts: float
    power_watts_without_control: float


@dataclass
class Report:
    path: Path
    samples: List[Sample]
    energy_wh_with_control: float
    energy_wh_without_control: float

    @property
    def energy_wh(self) -> float:
        return self.energy_wh_with_control

    @property
    def energy_kwh(self) -> float:
        return self.energy_wh_with_control / 1000.0

    @property
    def energy_kw_per_hour(self) -> float:
        return self.energy_wh_with_control / 1000.0

    @property
    def energy_kw_per_hour_without_control(self) -> float:
        return self.energy_wh_without_control / 1000.0

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
        default="Timestamp_PC",
        help=(
            "Nome da coluna contendo os instantes de medição "
            "(padrão: 'Timestamp_PC')."
        ),
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
        "--percent-column",
        default="Lamp_Power_Percent",
        help=(
            "Coluna contendo a potência relativa da lâmpada em porcentagem "
            "(padrão: 'Lamp_Power_Percent')."
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
    percent_column: str,
) -> List[Sample]:
    samples: List[Sample] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        headers = reader.fieldnames or []
        if time_column not in headers:
            raise ValueError(
                f"Coluna de tempo '{time_column}' não encontrada em {path.name}."
            )
        if percent_column not in headers:
            raise ValueError(
                f"Coluna de porcentagem '{percent_column}' não encontrada em {path.name}."
            )

        for row in reader:
            raw_time = row.get(time_column, "")
            timestamp = parse_timestamp(raw_time, time_format)
            if timestamp is None:
                continue

            percent_value = parse_float(row.get(percent_column))
            if percent_value is None:
                continue

            bounded_percent = max(percent_value, 0.0)
            power_value = (bounded_percent / 100.0) * SYSTEM_TOTAL_POWER_WATTS

            percent_without_control = 100.0 if bounded_percent > 0.0 else 0.0
            power_without_control = (
                percent_without_control / 100.0 * SYSTEM_TOTAL_POWER_WATTS
            )

            samples.append(
                Sample(
                    timestamp=timestamp,
                    power_percent=bounded_percent,
                    power_watts=power_value,
                    power_watts_without_control=power_without_control,
                )
            )

    samples.sort(key=lambda sample: sample.timestamp)
    return samples


def integrate_energy(samples: Sequence[Sample]) -> tuple[float, float]:
    if len(samples) < 2:
        return 0.0, 0.0
    energy_ws_with_control = 0.0
    energy_ws_without_control = 0.0
    for current, nxt in zip(samples, samples[1:]):
        delta_seconds = (nxt.timestamp - current.timestamp).total_seconds()
        if delta_seconds <= 0:
            continue
        energy_ws_with_control += current.power_watts * delta_seconds
        energy_ws_without_control += (
            current.power_watts_without_control * delta_seconds
        )
    return energy_ws_with_control / 3600.0, energy_ws_without_control / 3600.0


def analyze_file(path: Path, args: argparse.Namespace) -> Report:
    samples = load_samples(
        path,
        delimiter=args.delimiter,
        time_column=args.time_column,
        time_format=args.time_format,
        percent_column=args.percent_column,
    )
    energy_with_control, energy_without_control = integrate_energy(samples)
    return Report(
        path=path,
        samples=list(samples),
        energy_wh_with_control=energy_with_control,
        energy_wh_without_control=energy_without_control,
    )


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
    print(
        "  Com controle de potência: "
        f"{report.energy_kw_per_hour:.4f} kW/h"
    )
    print(
        "  Sem controle de potência: "
        f"{report.energy_kw_per_hour_without_control:.4f} kW/h"
    )
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
        total_wh_with_control = sum(
            report.energy_wh_with_control for report in reports
        )
        total_wh_without_control = sum(
            report.energy_wh_without_control for report in reports
        )
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
        print(
            "    Com controle de potência: "
            f"{total_wh_with_control/1000.0:.4f} kW/h"
        )
        print(
            "    Sem controle de potência: "
            f"{total_wh_without_control/1000.0:.4f} kW/h"
        )


if __name__ == "__main__":
    main()

