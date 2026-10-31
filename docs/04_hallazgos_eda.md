# Hallazgos del análisis exploratorio

Berka sirve para el proyecto, pero el análisis cambió dos decisiones: el saldo de cierre se calcula acumulando montos, y el margen usa una tasa supuesta. El detalle y los gráficos están en [notebooks/01_eda.ipynb](../notebooks/01_eda.ipynb).

## Decisiones que salieron del análisis

| Hallazgo | Evidencia | Decisión |
| --- | --- | --- |
| `trans_id` no sigue el orden dentro de un día | Acierta el cierre solo en el 21,1 % de los días con varios movimientos | Calcular el saldo acumulando abonos y cargos. Error medio de 0,18 CZK y máximo de 2,80 CZK |
| No hay intereses de préstamos | En los 682 préstamos, cuota por plazo es igual al monto | Usar la tasa supuesta de `ref.supuesto_tasa`, hoy 12 % anual, y rotular "estimado" |
| Los pagos `UVER` sí miden la mora | Marca en mora el 71 % de los préstamos problemáticos, con 3 falsas alertas en 606 sanos | Calcular el atraso comparando cuotas esperadas y pagadas, con tolerancia de una cuota |
| Las diferencias en `UVER` son de redondeo | La relación entre pago y cuota va de 1,000 a 1,002 | Contar pagos en vez de comparar montos exactos |
| `VYBER` en `type` se comporta como un cargo | El saldo baja en el 79,7 % de los casos comprobables, frente a 73,6 % en `VYDAJ` | Tratarlo como cargo |
| Hay 14 movimientos en cero | Todos son intereses o sanciones; ninguno es negativo | Cargarlos sin regla de rechazo |
| Hay 2.999 movimientos con saldo negativo | Están en 288 cuentas, y 255 de las 264 cuentas con sanción tuvieron saldo negativo | Tratarlos como sobregiros válidos |
| Falta `A12` y `A15` en el distrito Jesenik | Una fila con `?` | Cargar nulos |

El 71 % de detección tiene una limitación: la tolerancia de una cuota no ve a quien debe poco. Además, el estado B o D es el estado final de 1998, no el del mes analizado.

## Comportamiento del negocio

- Los movimientos crecen de 28.205 en 1993 a 322.277 en 1998.
- El 31,3 % de los movimientos ocurre los días 30 y 31, cuando se pagan intereses y comisiones. El proceso de cierre de mes será el más pesado.
- El 50,7 % de los movimientos no tiene categoría. Se clasifican con `type` y `operation`.
- El monto mediano es de 2.100 CZK, el percentil 99 de 45.455 CZK y el máximo de 87.400 CZK.
- Las comisiones y sanciones cubren solo el 9,9 % de los intereses pagados a clientes. Sin intereses de préstamos, el margen observable sería negativo.
- Los préstamos se reparten de forma pareja entre plazos de 12, 24, 36, 48 y 60 meses.
- Los préstamos problemáticos son más grandes: el estado D promedia 249.285 CZK y el estado A, 91.641 CZK.
- Moravia del Norte y Moravia del Sur concentran más cuentas, con 793 y 778.
- Cada cuenta tiene como máximo un préstamo.

## Qué mostró la primera carga

Con la tasa supuesta de 12 %, el margen estimado es negativo: en junio de 2026 fue de -163.574 CZK. El banco paga intereses sobre 156,9 millones de CZK en depósitos, pero solo presta 48,7 millones, el 31 %. Los datos no muestran qué hizo con el resto, así que el reporte no debe leerse como una pérdida real.
