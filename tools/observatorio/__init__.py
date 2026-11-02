"""Observatorio de sueldos del mercado tech argentino.

Este paquete no es el motor de liquidación (ese vive en ``src/``): acá solo se
recolectan, normalizan y publican datos de mercado.
"""

__all__ = ["fuentes", "normalizar", "construir", "graficar"]
