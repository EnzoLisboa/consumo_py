"""Ferramenta de linha de comando para cálculo de consumo de energia a partir de dados CSV.

O script aceita uma tabela com pelo menos uma coluna temporal e outra com
medições de potência ou com tensão/corrente. O consumo é estimado pela
integração trapezoidal da potência ao longo do tempo, retornando o total
em watt-hora e quilowatt-hora.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class Measurement:
    """Representa uma amostra de potência em um instante específico."""

    timestamp: datetime
    power_w: float


def parse_timestamp(value: str, fmt: Optional[str]) -> datetime:
    """Converte o texto ``value`` para :class:`datetime`.

    Se ``fmt`` for fornecido, utiliza :func:`datetime.strptime`. Caso
    contrário, tenta interpretar o valor como ISO 8601.
    """

    value = value.strip()
    if not value:
        raise ValueError("timestamp vazio")

    if fmt:
        return datetime.strptime(value, fmt)

    # Normaliza o sufixo Z (UTC) para o formato aceito pelo fromisoformat
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - caminho de erro
        raise ValueError(
            f"Não foi possível interpretar o timestamp '{value}'. "
            "Use --time-format para especificar o formato."
        ) from exc


def parse_float(value: str, column: str) -> float:
    """Converte ``value`` em ``float`` tratando vírgulas decimais."""

    text = value.strip().replace(",", ".")
    if not text:
        raise ValueError(f"Coluna '{column}' possui valor vazio")
    try:
        return float(text)
    except ValueError as exc:  # pragma: no cover - caminho de erro
        raise ValueError(
            f"Não foi possível converter o valor '{value}' da coluna '{column}' para número."
        ) from exc


def read_measurements(
    csv_path: Path,
    delimiter: str,
    time_column: str,
    power_column: Optional[str],
    voltage_column: Optional[str],
    current_column: Optional[str],
    time_format: Optional[str],
) -> List[Measurement]:
    """Lê o arquivo CSV e retorna as amostras ordenadas por tempo."""

    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

    if not power_column and not (voltage_column and current_column):
        raise ValueError(
            "É necessário informar a coluna de potência ou as colunas de tensão e corrente."
        )

    measurements: List[Measurement] = []

    with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        missing_columns = [
            column
            for column in [time_column, power_column, voltage_column, current_column]
            if column and column not in reader.fieldnames
        ]
        if missing_columns:
            raise KeyError(
                "Colunas ausentes no CSV: " + ", ".join(sorted(set(missing_columns)))
            )

        for row in reader:
            timestamp = parse_timestamp(row[time_column], time_format)

            if power_column:
                power = parse_float(row[power_column], power_column)
            else:
                voltage = parse_float(row[voltage_column], voltage_column)
                current = parse_float(row[current_column], current_column)
                power = voltage * current

            measurements.append(Measurement(timestamp=timestamp, power_w=power))

    measurements.sort(key=lambda measurement: measurement.timestamp)
    return measurements


def integrate_energy(measurements: Iterable[Measurement]) -> float:
    """Calcula o consumo total em watt-hora usando integração trapezoidal."""

    iterator = iter(measurements)
    try:
        previous = next(iterator)
    except StopIteration:
        return 0.0

    total_wh = 0.0
    for current in iterator:
        delta_hours = (current.timestamp - previous.timestamp).total_seconds() / 3600
        if delta_hours < 0:
            raise ValueError("As medições não estão em ordem cronológica.")

        avg_power = (previous.power_w + current.power_w) / 2
        total_wh += avg_power * delta_hours
        previous = current

    return total_wh


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calcula o consumo de energia a partir de leituras de potência registradas em CSV.",
    )
    parser.add_argument("csv_path", type=Path, help="Caminho do arquivo CSV contendo as medições")
    parser.add_argument(
        "--delimiter",
        default=",",
        help="Delimitador usado no arquivo (padrão: ',').",
    )
    parser.add_argument(
        "--time-column",
        default="timestamp",
        help="Nome da coluna com o instante de cada medição (padrão: 'timestamp').",
    )
    parser.add_argument(
        "--power-column",
        default="power",
        help="Nome da coluna que contém a potência em watts. Informe vazio para usar tensão e corrente.",
    )
    parser.add_argument(
        "--voltage-column",
        default="",
        help="Nome da coluna com a tensão em volts (usado quando não há coluna de potência).",
    )
    parser.add_argument(
        "--current-column",
        default="",
        help="Nome da coluna com a corrente em ampères (usado quando não há coluna de potência).",
    )
    parser.add_argument(
        "--time-format",
        default=None,
        help=(
            "Formato strftime dos timestamps (ex.: '%d/%m/%Y %H:%M:%S'). "
            "Se omitido, é esperado ISO 8601."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    power_column = args.power_column.strip() or None
    voltage_column = args.voltage_column.strip() or None
    current_column = args.current_column.strip() or None

    measurements = read_measurements(
        csv_path=args.csv_path,
        delimiter=args.delimiter,
        time_column=args.time_column,
        power_column=power_column,
        voltage_column=voltage_column,
        current_column=current_column,
        time_format=args.time_format,
    )

    if len(measurements) < 2:
        print("É necessário pelo menos duas medições para calcular o consumo.")
        return 1

    total_wh = integrate_energy(measurements)
    total_kwh = total_wh / 1000

    start = measurements[0].timestamp
    end = measurements[-1].timestamp
    duration_hours = (end - start).total_seconds() / 3600

    print("Resumo das medições:")
    print(f"  Início: {start}")
    print(f"  Fim: {end}")
    print(f"  Duração: {duration_hours:.2f} h")
    print(f"  Amostras: {len(measurements)}")
    print()
    print("Consumo estimado:")
    print(f"  {total_wh:.2f} Wh")
    print(f"  {total_kwh:.4f} kWh")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())