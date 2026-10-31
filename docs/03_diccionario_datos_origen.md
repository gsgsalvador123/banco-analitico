# Diccionario de datos de origen: Berka

Este diccionario describe los archivos originales, antes de limpiarlos. Los significados vienen de la [guía oficial del dataset](https://web.archive.org/web/2022/https://sorry.vse.cz/~berka/challenge/pkdd1999/berka.htm). Los conteos salen de la lectura directa de los archivos el 30 de octubre de 2026.

- **Ubicación:** `data/raw/berka/`
- **Formato:** texto separado por punto y coma, con encabezado
- **Periodo:** 1 de enero de 1993 al 31 de diciembre de 1998
- **Moneda:** coronas checas (CZK)
- **Control:** SHA-256 de `data_berka.zip`: `affa4477572e9d8f2de6beff8a525d37c056d5d8e4a9670dd8c7636208c002ce`

## Cómo se relacionan

```text
district ──< client ──< disp >── account ──< trans
                         │          ├──────< order
                         │          └──────< loan
                         └──< card

district ──< account
```

Un cliente se vincula con una cuenta mediante `disp`. Solo el titular (`OWNER`) puede crear órdenes permanentes y pedir préstamos.

## Archivos

| Archivo | Filas | Una fila representa |
| --- | --- | --- |
| `account.asc` | 4.500 | Una cuenta |
| `client.asc` | 5.369 | Un cliente |
| `disp.asc` | 5.369 | El derecho de un cliente sobre una cuenta |
| `order.asc` | 6.471 | Una orden de pago permanente |
| `trans.asc` | 1.056.320 | Un movimiento de una cuenta |
| `loan.asc` | 682 | Un préstamo |
| `card.asc` | 892 | Una tarjeta |
| `district.asc` | 77 | Un distrito |

## account

| Columna | Significado |
| --- | --- |
| `account_id` | Identificador de la cuenta |
| `district_id` | Distrito de la sucursal |
| `frequency` | Frecuencia de emisión de extractos |
| `date` | Fecha de creación, `AAMMDD` |

| Valor de `frequency` | Significado | Filas |
| --- | --- | --- |
| `POPLATEK MESICNE` | Mensual | 4.167 |
| `POPLATEK TYDNE` | Semanal | 240 |
| `POPLATEK PO OBRATU` | Después de cada transacción | 93 |

## client

| Columna | Significado |
| --- | --- |
| `client_id` | Identificador del cliente |
| `birth_number` | Fecha de nacimiento y sexo codificados |
| `district_id` | Distrito del cliente |

`birth_number` tiene la forma `AAMMDD` en hombres y `AA(MM+50)DD` en mujeres. El archivo contiene 2.724 filas del primer tipo y 2.645 del segundo.

## disp

| Columna | Significado |
| --- | --- |
| `disp_id` | Identificador de la relación |
| `client_id` | Cliente |
| `account_id` | Cuenta |
| `type` | `OWNER` para titular (4.500) o `DISPONENT` para usuario autorizado (869) |

## order

| Columna | Significado |
| --- | --- |
| `order_id` | Identificador de la orden |
| `account_id` | Cuenta de origen |
| `bank_to` | Banco de destino |
| `account_to` | Cuenta de destino |
| `amount` | Monto |
| `k_symbol` | Motivo: `POJISTNE`, `SIPO`, `LEASING` o `UVER` |

## trans

| Columna | Significado |
| --- | --- |
| `trans_id` | Identificador del movimiento |
| `account_id` | Cuenta |
| `date` | Fecha, `AAMMDD` |
| `type` | Abono o cargo |
| `operation` | Forma de la operación |
| `amount` | Monto |
| `balance` | Saldo después del movimiento |
| `k_symbol` | Categoría del movimiento |
| `bank` | Banco de la contraparte |
| `account` | Cuenta de la contraparte |

| Valor de `type` | Significado | Filas |
| --- | --- | --- |
| `PRIJEM` | Abono | 405.083 |
| `VYDAJ` | Cargo | 634.571 |
| `VYBER` | No aparece en la guía; se trata como cargo | 16.666 |

| Valor de `operation` | Significado |
| --- | --- |
| `VYBER KARTOU` | Retiro con tarjeta |
| `VKLAD` | Depósito en efectivo |
| `PREVOD Z UCTU` | Cobro desde otro banco |
| `VYBER` | Retiro en efectivo |
| `PREVOD NA UCET` | Envío a otro banco |

| Valor de `k_symbol` | Significado | Filas | Monto (CZK) |
| --- | --- | --- | --- |
| vacío | Sin categoría | 535.314 | sin calcular |
| `UROK` | Interés abonado al cliente | 183.114 | 27.470.689 |
| `SLUZBY` | Pago por extracto | 155.832 | 2.686.418 |
| `SIPO` | Pagos del hogar | 118.065 | 498.506.416 |
| `DUCHOD` | Pensión de jubilación | 30.338 | 167.472.118 |
| `POJISTNE` | Pago de seguro | 18.500 | 24.175.193 |
| `UVER` | Pago de préstamo | 13.580 | 55.252.303 |
| `SANKC. UROK` | Interés de sanción por saldo negativo | 1.577 | 37.663 |

## loan

| Columna | Significado |
| --- | --- |
| `loan_id` | Identificador del préstamo |
| `account_id` | Cuenta |
| `date` | Fecha de concesión, `AAMMDD` |
| `amount` | Monto |
| `duration` | Plazo en meses |
| `payments` | Cuota mensual |
| `status` | Estado del préstamo |

| Valor de `status` | Significado | Filas |
| --- | --- | --- |
| `A` | Terminado, sin problemas | 203 |
| `B` | Terminado, no pagado | 31 |
| `C` | Vigente, al día | 403 |
| `D` | Vigente, con deuda | 45 |

`status` solo muestra el estado final. Además, cuota por plazo es igual al monto en los 682 préstamos, así que no hay intereses de préstamos en los datos.

## card

| Columna | Significado |
| --- | --- |
| `card_id` | Identificador de la tarjeta |
| `disp_id` | Relación cliente-cuenta |
| `type` | `classic` (659), `junior` (145) o `gold` (88) |
| `issued` | Fecha de emisión |

## district

| Columna | Significado |
| --- | --- |
| `A1` | Código del distrito |
| `A2` | Nombre |
| `A3` | Región |
| `A4` | Habitantes |
| `A5` a `A8` | Municipios por tamaño de población |
| `A9` | Ciudades |
| `A10` | Porcentaje de población urbana |
| `A11` | Salario promedio |
| `A12` y `A13` | Tasa de desempleo de 1995 y 1996 |
| `A14` | Emprendedores por cada 1.000 habitantes |
| `A15` y `A16` | Delitos registrados en 1995 y 1996 |

## Problemas conocidos para el EDA

| Problema | Alcance | Tratamiento previsto |
| --- | --- | --- |
| Monto cero | 14 movimientos | Se cargan: son intereses o sanciones en cero |
| Saldo negativo | 2.999 movimientos | Se cargan como sobregiros válidos |
| Sin categoría | 535.314 movimientos | Clasificar con `type` y `operation` |
| Tipo `VYBER` | 16.666 movimientos | Se trata como cargo |
| Fechas `AAMMDD` | Varias tablas | Convertir a fecha |
| Sexo dentro de `birth_number` | Clientes | Separar sexo y fecha de nacimiento |
| Valor `?` | 1 fila de `district` | Tratar como nulo |
| Códigos en checo | Varias tablas | Traducir en tablas de referencia |
