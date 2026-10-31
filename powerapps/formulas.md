# App de cobranzas: pantallas y fórmulas

Sigue este orden en Power Apps Studio. Usa los mismos nombres de controles, porque las fórmulas dependen de ellos. Si Power Apps muestra un error, manda una captura en vez de cambiar la fórmula.

## Conexión

En **Data** > **Add data** > **SQL Server**:

| Campo | Valor |
| --- | --- |
| Autenticación | SQL Server Authentication |
| Servidor | `ba-sql-gdhi0s.database.windows.net` |
| Base de datos | `BancoAnalitico` |
| Usuario | `app_cobranzas` |
| Contraseña | El valor de `BA_CLAVE_APP` en el archivo `.env.azure` |

Agrega solo estas dos tablas:

- `mart.vw_bandeja_cobranza`
- `ops.gestion_cobranza`

Si Power Apps les da otro nombre, por ejemplo `[mart].[vw_bandeja_cobranza]`, usa ese en las fórmulas.

## Pantalla 1: Bandeja

Nombre de la pantalla: `scrBandeja`

| Control | Nombre | Propiedad | Valor |
| --- | --- | --- | --- |
| Entrada de texto | `txtBuscar` | HintText | `"Buscar distrito"` |
| Galería vertical | `galBandeja` | Items | Fórmula A |
| Etiqueta dentro de la galería | `lblPrestamo` | Text | Fórmula B |
| Etiqueta dentro de la galería | `lblDetalle` | Text | Fórmula C |

Fórmula A:

```powerfx
SortByColumns(
    Filter('mart.vw_bandeja_cobranza', StartsWith(distrito, txtBuscar.Text)),
    "cuotas_atrasadas",
    SortOrder.Descending
)
```

Fórmula B:

```powerfx
"Préstamo " & ThisItem.prestamo_id & " · " & ThisItem.distrito
```

Fórmula C:

```powerfx
ThisItem.tramo_atraso & " · Debe " & Text(ThisItem.capital_pendiente, "#,##0") & " CZK"
```

En la propiedad **OnSelect** de `galBandeja`:

```powerfx
Set(varPrestamo, ThisItem); Navigate(scrFicha, ScreenTransition.Fade)
```

## Pantalla 2: Ficha

Nombre de la pantalla: `scrFicha`

| Control | Nombre | Propiedad | Valor |
| --- | --- | --- | --- |
| Etiqueta | `lblFicha` | Text | Fórmula D |
| Galería vertical | `galHistorial` | Items | Fórmula E |
| Etiqueta dentro de la galería | `lblHistorial` | Text | Fórmula F |
| Botón | `btnRegistrar` | Text | `"Registrar gestión"` |
| Botón | `btnVolver` | Text | `"Volver"` |

Fórmula D:

```powerfx
"Préstamo " & varPrestamo.prestamo_id & Char(10) &
"Cliente " & varPrestamo.cliente_id & " · " & varPrestamo.distrito & Char(10) &
"Cuotas atrasadas: " & varPrestamo.cuotas_atrasadas & Char(10) &
"Capital pendiente: " & Text(varPrestamo.capital_pendiente, "#,##0") & " CZK"
```

Fórmula E:

```powerfx
SortByColumns(
    Filter('ops.gestion_cobranza', prestamo_id = varPrestamo.prestamo_id),
    "fecha_gestion",
    SortOrder.Descending
)
```

Fórmula F:

```powerfx
Text(ThisItem.fecha_gestion, "dd/mm/yyyy") & " · " & ThisItem.resultado & " · " & ThisItem.analista
```

OnSelect de `btnRegistrar`:

```powerfx
Navigate(scrRegistrar, ScreenTransition.Fade)
```

OnSelect de `btnVolver`:

```powerfx
Back()
```

## Pantalla 3: Registrar gestión

Nombre de la pantalla: `scrRegistrar`

| Control | Nombre | Propiedad | Valor |
| --- | --- | --- | --- |
| Lista desplegable | `ddResultado` | Items | Fórmula G |
| Entrada de texto | `txtMonto` | Format | `TextFormat.Number` |
| Selector de fecha | `dpCompromiso` | IsEditable | `true` |
| Entrada de texto | `txtComentario` | Mode | `TextMode.MultiLine` |
| Botón | `btnGuardar` | Text | `"Guardar"` |

Fórmula G:

```powerfx
["Promesa de pago", "Pago realizado", "No contesta", "Rechaza pagar", "Número equivocado"]
```

OnSelect de `btnGuardar`:

```powerfx
Patch(
    'ops.gestion_cobranza',
    Defaults('ops.gestion_cobranza'),
    {
        prestamo_id: varPrestamo.prestamo_id,
        analista: User().FullName,
        resultado: ddResultado.Selected.Value,
        monto_prometido: If(IsBlank(txtMonto.Text), Blank(), Value(txtMonto.Text)),
        fecha_compromiso: dpCompromiso.SelectedDate,
        comentario: txtComentario.Text
    }
);
If(
    IsEmpty(Errors('ops.gestion_cobranza')),
    Notify("Gestión guardada", NotificationType.Success); Back(),
    Notify("No se pudo guardar", NotificationType.Error)
)
```

## Pantalla 4: Compromisos

Nombre de la pantalla: `scrCompromisos`

| Control | Nombre | Propiedad | Valor |
| --- | --- | --- | --- |
| Galería vertical | `galCompromisos` | Items | Fórmula H |
| Etiqueta dentro de la galería | `lblCompromiso` | Text | Fórmula I |
| Etiqueta dentro de la galería | `lblCompromiso` | Color | Fórmula J |

Fórmula H:

```powerfx
SortByColumns(
    Filter('ops.gestion_cobranza', resultado = "Promesa de pago"),
    "fecha_compromiso",
    SortOrder.Ascending
)
```

Fórmula I:

```powerfx
Text(ThisItem.fecha_compromiso, "dd/mm/yyyy") & " · Préstamo " & ThisItem.prestamo_id &
" · " & Text(ThisItem.monto_prometido, "#,##0") & " CZK"
```

Fórmula J:

```powerfx
If(ThisItem.fecha_compromiso < Today(), Color.Red, Color.Black)
```

Para llegar aquí, agrega en `scrBandeja` un botón `btnCompromisos` con este OnSelect:

```powerfx
Navigate(scrCompromisos, ScreenTransition.Fade)
```

## Prueba final

1. Selecciona un préstamo en la bandeja.
2. Registra una promesa de pago con monto y fecha.
3. Comprueba que aparece en la ficha y en Compromisos.
4. Guarda, publica y cierra la app, porque dejarla abierta mantiene despierta la base.
5. Exporta la solución como **Unmanaged** y guarda el ZIP en `powerplatform/`.
