"""Excepción propia del parser para errores de formato o validación."""


class MapParseError(Exception):
    """Se lanza cuando el fichero de mapa viola el formato esperado."""
