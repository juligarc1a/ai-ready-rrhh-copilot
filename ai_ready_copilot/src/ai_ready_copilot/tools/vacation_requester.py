from datetime import date, timedelta, datetime
import dateparser

def _parse_date_spec(spec: str) -> date:
    """
    Convierte expresiones como 'lunes', '2/3/2026', 'el próximo viernes'
    en una fecha concreta.
    """
    parsed = dateparser.parse(
        spec,
        languages=["es"],
        settings={
            "RELATIVE_BASE": datetime.today(),   # relativo a hoy
            "PREFER_DATES_FROM": "future",       # coge fechas futuras por defecto
            "DATE_ORDER": "DMY",                 # interpreta 2/3/2026 como 2 marzo
        },
    )
    if not parsed:
        raise ValueError(f"No se puede interpretar la fecha: {spec!r}")
    return parsed.date()

def request_vacation(
    start_spec: str,
    end_spec: str | None = None,
    days: int | None = None,
    reason: str | None = None,
) -> dict:
    """
    Solicita vacaciones a partir de expresiones flexibles de fecha.

    - Caso 1: rango explícito -> start_spec y end_spec
      Ej: start_spec='2/3/2026', end_spec='5/3/2026'

    - Caso 2: desde una referencia + número de días
      Ej: start_spec='lunes', days=5
    """
    start_date = _parse_date_spec(start_spec)

    if end_spec is not None:
        # Caso: rango explícito
        end_date = _parse_date_spec(end_spec)
    elif days is not None:
        # Caso: 'a partir de X' + número de días
        end_date = start_date + timedelta(days=days - 1)
    else:
        raise ValueError(
            "Debes proporcionar end_spec (fecha fin) o days (número de días)."
        )

    msg = (
        f"Vacaciones solicitadas desde {start_date.isoformat()} "
        f"hasta {end_date.isoformat()}"
    )
    if reason:
        msg += f" por motivo: {reason}"

    return {
        "status": "success",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "message": msg,
    }