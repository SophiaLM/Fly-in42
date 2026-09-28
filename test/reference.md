==============================================================================
  FLY-IN — SUITE DE ERRORES DE PARSING
==============================================================================
[+] TARGET   : python3 -m src.main <mapa>
[+] MAPS     : test/maps_fake/
[+] COVERAGE : encoding / nb_drones / zone

------------------------------------------------------------------------------
 1. ENCODING — MAPA CON BYTES NO UTF-8
------------------------------------------------------------------------------

  [ OK ]  TEST 01:
          ARGUMENT:    python3 -m src.main test/maps_fake/encoding_invalido.txt
          DESCRIPTION: Encoding inválido: bytes 0xFF 0xFE 0x80 ilegibles
          |-- EXPECTED : exit != 0 y mensaje de error a stderr
          |-- GOT      : exit=1 (falla), última excepción: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 13: invalid start byte
          [WARN] Excepción sin capturar (traceback) en vez de un error limpio 'error: ...'

  [SECTION SUMMARY] : 1/1 Passed — encoding
  [TOTALS]          : PASS=1 | FAIL=0

------------------------------------------------------------------------------
 2. NB_DRONES — CANTIDAD DE DRONES INVÁLIDA
------------------------------------------------------------------------------

  [ OK ]  TEST 02:
          ARGUMENT:    python3 -m src.main test/maps_fake/nb_drones_cero.txt
          DESCRIPTION: nb_drones = 0 (no positivo)
          |-- EXPECTED : exit != 0 y mensaje de error a stderr
          |-- GOT      : exit=1, error: Line 1: 'nb_drones' must be a positive integer

  [ OK ]  TEST 03:
          ARGUMENT:    python3 -m src.main test/maps_fake/nb_drones_negativo.txt
          DESCRIPTION: nb_drones = -3 (negativo)
          |-- EXPECTED : exit != 0 y mensaje de error a stderr
          |-- GOT      : exit=1, error: Line 1: 'nb_drones' must be a positive integer

  [ OK ]  TEST 04:
          ARGUMENT:    python3 -m src.main test/maps_fake/nb_drones_no_entero.txt
          DESCRIPTION: nb_drones = abc (no entero)
          |-- EXPECTED : exit != 0 y mensaje de error a stderr
          |-- GOT      : exit=1, error: Line 1: 'nb_drones' must be a positive integer

  [SECTION SUMMARY] : 3/3 Passed — nb_drones
  [TOTALS]          : PASS=3 | FAIL=0

------------------------------------------------------------------------------
 3. ZONES — TIPO DE ZONA INVÁLIDO
------------------------------------------------------------------------------

  [ OK ]  TEST 05:
          ARGUMENT:    python3 -m src.main test/maps_fake/zone_invalida.txt
          DESCRIPTION: zone=volcano (no está en normal/blocked/restricted/priority)
          |-- EXPECTED : exit != 0 y mensaje de error a stderr
          |-- GOT      : exit=1, error: Line 3: zone='volcano' is not valid. Allowed values: normal, blocked, restricted, priority.

  [SECTION SUMMARY] : 1/1 Passed — zone
  [TOTALS]          : PASS=1 | FAIL=0

==============================================================================
 FINAL TEST RESULTS
==============================================================================

  TOTAL TESTS RAN : [ 5 ]
  PASSED          : [ 5 ]
  FAILED          : [ 0 ]
  SUCCESS RATE    : [ 100.0% ]

  STATUS          : Ninguno falló — Todos los mapas inválidos fueron rechazados correctamente.

  NOTA: Las advertencias [WARN] indican un fallo capturado vía traceback 
        en lugar de un mensaje de error formateado (stderr).

