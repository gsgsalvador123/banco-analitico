# Crea excel/plantilla_informe.xlsx con Excel: cinco hojas visibles, tablas dinámicas, gráficos y segmentaciones.
# Uso: crear_plantilla.ps1 -Semilla <carpeta con los CSV de "python -m banco.informe semilla">
# Solo hace falta repetirlo si cambia el diseño. Cada mes GitHub Actions rellena esta plantilla sin abrir Excel.

param([Parameter(Mandatory)][string]$Semilla)

$ErrorActionPreference = 'Stop'
$salida = Join-Path $PSScriptRoot 'plantilla_informe.xlsx'
$falta = [Type]::Missing

function Color([string]$hex) {
  [Convert]::ToInt32($hex.Substring(4, 2) + $hex.Substring(2, 2) + $hex.Substring(0, 2), 16)
}
$marino = Color '12284B'; $azul = Color '2F6FD0'; $gris = Color '5B6776'; $rojo = Color 'D6453D'
$verde = Color '00806F'; $borde = Color 'E2E6EC'; $fondo = Color 'F3F5F8'; $blanco = Color 'FFFFFF'

function Convertir([string]$texto) {
  if ($texto -eq '') { return $null }
  if ($texto -match '^\d{4}-\d{2}-\d{2}') { return ([datetime]::Parse($texto.Substring(0, 10))).ToOADate() }
  $numero = 0.0
  if ($texto -match '^-?\d+(\.\d+)?$' -and
      [double]::TryParse($texto, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$numero)) {
    return $numero
  }
  return $texto
}

function PonerTabla($hoja, [int]$fila, [string]$nombre) {
  $lineas = Import-Csv (Join-Path $Semilla "$nombre.csv") -Encoding UTF8
  $columnas = @($lineas[0].PSObject.Properties.Name)
  $matriz = New-Object 'object[,]' ($lineas.Count + 1), $columnas.Count
  for ($c = 0; $c -lt $columnas.Count; $c++) { $matriz[0, $c] = $columnas[$c] }
  for ($f = 0; $f -lt $lineas.Count; $f++) {
    for ($c = 0; $c -lt $columnas.Count; $c++) {
      # anio_mes es texto aunque parezca fecha.
      $valor = $lineas[$f].($columnas[$c])
      $matriz[($f + 1), $c] = if ($columnas[$c] -eq 'anio_mes') { $valor } else { Convertir $valor }
    }
  }
  $inicio = $hoja.Cells.Item($fila, 1)
  $rango = $inicio.Resize($lineas.Count + 1, $columnas.Count)
  if ($columnas -contains 'anio_mes') { $rango.Columns.Item([array]::IndexOf($columnas, 'anio_mes') + 1).NumberFormat = '@' }
  $rango.Value2 = $matriz
  $tabla = $hoja.ListObjects.Add(1, $rango, $falta, 1)
  $tabla.Name = $nombre
  $tabla.TableStyle = 'TableStyleLight1'
  return $tabla
}

function FormatoColumna($tabla, [string]$columna, [string]$formato) {
  $tabla.ListColumns.Item($columna).DataBodyRange.NumberFormat = $formato
}

function Banda($hoja, [string]$titulo, [string]$subtitulo, [string]$ultima) {
  $hoja.Cells.Font.Name = 'Segoe UI'
  $hoja.Cells.Font.Size = 10
  $hoja.Cells.Font.Color = $marino
  $rango = $hoja.Range("A1:${ultima}2")
  $rango.Interior.Color = $marino
  $rango.Font.Color = $blanco
  $hoja.Range('B1').Value2 = $titulo
  $hoja.Range('B1').Font.Size = 16
  $hoja.Range('B1').Font.Bold = $true
  $hoja.Range('B2').Value2 = $subtitulo
  $hoja.Range('B2').Font.Color = (Color 'D5DDEA')
  $hoja.Rows.Item(1).RowHeight = 28
  $hoja.Rows.Item(2).RowHeight = 20
  $hoja.Columns.Item(1).ColumnWidth = 2
  $hoja.Activate()
  $hoja.Parent.Application.ActiveWindow.DisplayGridlines = $false
}

function Dinamica($cache, $hoja, [string]$celda, [string]$nombre, [string]$filas, [string]$columnas = ' ') {
  $tabla = $cache.CreatePivotTable($hoja.Range($celda), $nombre)
  $tabla.CompactLayoutRowHeader = $filas
  $tabla.CompactLayoutColumnHeader = $columnas
  $tabla.TableStyle2 = 'PivotStyleLight1'
  $tabla.HasAutoFormat = $false
  $tabla.NullString = '-'
  return $tabla
}

function CampoFila($tabla, [string]$campo, [string]$rotulo) {
  $f = $tabla.PivotFields($campo)
  $f.Orientation = 1
  $f.Caption = $rotulo
}

function CampoColumna($tabla, [string]$campo, [string]$rotulo) {
  $f = $tabla.PivotFields($campo)
  $f.Orientation = 2
  $f.Caption = $rotulo
}

function CampoValor($tabla, [string]$campo, [string]$rotulo, [string]$formato) {
  $f = $tabla.AddDataField($tabla.PivotFields($campo), $rotulo, -4157)
  $f.NumberFormat = $formato
}

function Segmentacion($libro, $tabla, $hoja, [string]$campo, [string]$rotulo, [double]$izq, [double]$arriba, [double]$ancho, [double]$alto) {
  $cache = $libro.SlicerCaches.Add2($tabla, $campo)
  $s = $cache.Slicers.Add($hoja, $falta, "s$campo$($tabla.Name)", $rotulo, $arriba, $izq, $ancho, $alto)
  $s.Style = 'SlicerStyleLight1'
  return $s
}

function Grafico($hoja, $tabla, [int]$tipo, [string]$titulo, [double]$izq, [double]$arriba, [double]$ancho, [double]$alto, [string[]]$colores) {
  # Rótulo aparte: Excel no siempre deja poner título a un gráfico dinámico.
  $caja = $hoja.Shapes.AddTextbox(1, $izq, $arriba, $ancho, 22)
  $caja.TextFrame2.TextRange.Text = $titulo
  $caja.TextFrame2.TextRange.Font.Size = 12
  $caja.TextFrame2.TextRange.Font.Bold = -1
  $caja.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $marino
  $caja.Line.Visible = 0
  # -1 = estilo por defecto del tipo de gráfico.
  $forma = $hoja.Shapes.AddChart2(-1, $tipo, $izq, $arriba + 22, $ancho, $alto - 22)
  $g = $forma.Chart
  $g.SetSourceData($tabla.TableRange1)
  $g.HasTitle = $false
  $g.ShowAllFieldButtons = $false
  $g.HasLegend = $true
  $g.Legend.Position = -4160
  $n = $g.SeriesCollection().Count
  for ($i = 1; $i -le $n -and $i -le $colores.Count; $i++) {
    $g.SeriesCollection($i).Format.Fill.ForeColor.RGB = (Color $colores[$i - 1])
  }
  return $g
}

$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
$libro = $null
try {
  $libro = $xl.Workbooks.Add()
  while ($libro.Worksheets.Count -lt 8) { [void]$libro.Worksheets.Add($falta, $libro.Worksheets.Item($libro.Worksheets.Count)) }
  $nombres = 'Portada', 'Rentabilidad', 'Cartera', 'Morosos', 'Supuestos', 'dKpi', 'dMargen', 'dCartera'
  for ($i = 0; $i -lt 8; $i++) { $libro.Worksheets.Item($i + 1).Name = $nombres[$i] }
  $portada = $libro.Worksheets.Item('Portada'); $renta = $libro.Worksheets.Item('Rentabilidad')
  $cartera = $libro.Worksheets.Item('Cartera'); $morosos = $libro.Worksheets.Item('Morosos')
  $supuestos = $libro.Worksheets.Item('Supuestos')

  # ---- Datos: el generador mensual reemplaza las filas de estas cuatro tablas.
  $tKpi = PonerTabla $libro.Worksheets.Item('dKpi') 1 'tKpi'
  $tMargen = PonerTabla $libro.Worksheets.Item('dMargen') 1 'tMargen'
  $tCartera = PonerTabla $libro.Worksheets.Item('dCartera') 1 'tCartera'
  foreach ($c in 'depositos', 'cartera', 'cartera_en_mora', 'margen_estimado') { FormatoColumna $tKpi $c '#,##0' }
  FormatoColumna $tMargen 'monto' '#,##0'
  FormatoColumna $tCartera 'capital_pendiente' '#,##0'

  # ---- Morosos: selector con validación y BUSCARX sobre la tabla.
  Banda $morosos 'Morosos' 'Préstamos en mora para gestionar, de mayor a menor capital pendiente.' 'L'
  $tMorosos = PonerTabla $morosos 9 'tMorosos'
  foreach ($c in 'Monto', 'Cuota', 'Capital pendiente') { FormatoColumna $tMorosos $c '#,##0' }
  foreach ($c in 'Última gestión', 'Compromiso') { FormatoColumna $tMorosos $c 'dd/mm/yyyy' }
  $tMorosos.ShowTableStyleRowStripes = $false
  $tMorosos.HeaderRowRange.Font.Bold = $true
  $tMorosos.HeaderRowRange.Interior.Color = (Color 'EEF1F6')
  $morosos.Range('B4').Value2 = 'Elige un préstamo'
  $morosos.Range('B4').Font.Bold = $true
  $morosos.Range('C4').Value2 = $tMorosos.ListColumns.Item('Préstamo').DataBodyRange.Cells.Item(1, 1).Value2
  $morosos.Range('C4').Interior.Color = (Color 'FFF7DB')
  $morosos.Range('C4').HorizontalAlignment = -4108
  # Un nombre y no una función: las validaciones se escriben en el idioma de Excel.
  [void]$libro.Names.Add('ListaPrestamos', '=tMorosos[Préstamo]')
  [void]$morosos.Range('C4').Validation.Add(3, 1, 1, '=ListaPrestamos')
  $morosos.Range('C4').Validation.ErrorTitle = 'Préstamo no encontrado'
  $morosos.Range('C4').Validation.ErrorMessage = 'Elige un préstamo de la lista.'
  $campos = @(
    @('D', 'Distrito', 'Distrito', '@'), @('E', 'Región', 'Región', '@'),
    @('F', 'Capital pendiente', 'Capital pendiente', '#,##0'), @('G', 'Cuotas atrasadas', 'Cuotas atrasadas', '0'),
    @('H', 'Tiempo de atraso', 'Tiempo de atraso', '@'), @('I', 'Último resultado', 'Último resultado', '@')
  )
  foreach ($c in $campos) {
    $morosos.Range("$($c[0])4").Value2 = $c[1]
    $morosos.Range("$($c[0])4").Font.Color = $gris
    $celda = $morosos.Range("$($c[0])5")
    $celda.NumberFormat = if ($c[3] -eq '@') { 'General' } else { $c[3] }
    $celda.Formula2 = "=XLOOKUP(`$C`$4,tMorosos[Préstamo],tMorosos[$($c[2])],""Sin datos"",0)&"""""
    if ($c[3] -ne '@') { $celda.Formula2 = "=XLOOKUP(`$C`$4,tMorosos[Préstamo],tMorosos[$($c[2])],""Sin datos"",0)" }
    $celda.Font.Bold = $true
    $celda.HorizontalAlignment = -4131
  }
  $morosos.Range('B7').Value2 = 'Lista completa'
  $morosos.Range('B7').Font.Bold = $true
  # Resalta los atrasos más largos. El rango excede la tabla porque cada mes cambia de tamaño.
  $regla = $morosos.Range('H10:H2000').FormatConditions.Add(2, 0, '=$H10="Más de 90"')
  $regla.Font.Color = $rojo
  $tMorosos.Range.Columns.AutoFit() | Out-Null
  $morosos.Columns.Item(1).ColumnWidth = 12
  foreach ($c in 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I') { if ($morosos.Columns.Item($c).ColumnWidth -lt 15) { $morosos.Columns.Item($c).ColumnWidth = 15 } }

  # ---- Rentabilidad: tabla y gráfico dinámicos, con segmentación por región.
  Banda $renta 'Rentabilidad' 'Margen estimado por producto y mes, en CZK. El interés de préstamos usa una tasa supuesta.' 'R'
  $cacheMargen = $libro.PivotCaches().Create(1, 'tMargen')
  $cacheMargen.RefreshOnFileOpen = $true
  $dRenta = Dinamica $cacheMargen $renta 'B5' 'dRentabilidad' 'Mes' 'Producto'
  CampoFila $dRenta 'anio_mes' 'Mes'
  CampoColumna $dRenta 'producto' 'Producto'
  CampoValor $dRenta 'monto' 'Margen estimado' '#,##0;-#,##0'
  $dRenta.ColumnGrand = $true
  $renta.Columns.Item(2).ColumnWidth = 32
  $renta.Columns.Item('C:E').ColumnWidth = 13
  $gRenta = Grafico $renta $dRenta 51 'Margen estimado por producto' 450 72 560 320 @('2F6FD0', '00A5A0')
  $gRenta.Axes(1).TickLabelPosition = -4134
  $dRentaCopia = Dinamica $cacheMargen $renta 'B24' 'dComponentes' 'Componente'
  CampoFila $dRentaCopia 'componente' 'Componente'
  CampoValor $dRentaCopia 'monto' 'Total 13 meses' '#,##0;-#,##0'
  [void](Segmentacion $libro $dRenta $renta 'region' 'Región' 450 400 560 78)
    $libro.SlicerCaches.Item(1).PivotTables.AddPivotTable($dRentaCopia)
  $libro.SlicerCaches.Item(1).Slicers.Item(1).NumberOfColumns = 4

  # ---- Cartera: mora por distrito y plazo, con segmentaciones.
  Banda $cartera 'Cartera' 'Capital pendiente en el último mes cerrado, en CZK. Usa las segmentaciones para filtrar.' 'R'
  $cacheCartera = $libro.PivotCaches().Create(1, 'tCartera')
  $cacheCartera.RefreshOnFileOpen = $true
  $dPlazo = Dinamica $cacheCartera $cartera 'B5' 'dPlazo' 'Plazo' 'Situación'
  CampoFila $dPlazo 'plazo' 'Plazo'
  CampoColumna $dPlazo 'situacion' 'Situación'
  CampoValor $dPlazo 'capital_pendiente' 'Capital pendiente' '#,##0'
  # Deja dos filas libres arriba para el filtro "En mora".
  $dDistrito = Dinamica $cacheCartera $cartera 'B18' 'dDistrito' 'Distrito'
  CampoFila $dDistrito 'distrito' 'Distrito'
  CampoValor $dDistrito 'capital_pendiente' 'Capital en mora' '#,##0'
  $mora = $dDistrito.PivotFields('situacion')
  $mora.Orientation = 3
  $mora.Caption = 'Situación'
  $mora.CurrentPage = 'En mora'
  $dDistrito.PivotFields('distrito').AutoSort(2, 'Capital en mora')
  $cartera.Columns.Item(2).ColumnWidth = 26
  $cartera.Columns.Item('C:E').ColumnWidth = 13
  [void](Grafico $cartera $dPlazo 52 'Capital por plazo: al día y en mora' 420 192 560 300 @('2F6FD0', 'D6453D'))
  $sRegion = Segmentacion $libro $dPlazo $cartera 'region' 'Región' 420 72 350 112
  $sRegion.NumberOfColumns = 3
  $sTramo = Segmentacion $libro $dPlazo $cartera 'tramo_atraso' 'Tiempo de atraso' 780 72 200 112
  foreach ($i in 2, 3) { $libro.SlicerCaches.Item($i).PivotTables.AddPivotTable($dDistrito) }

  # ---- Supuestos: tasa y definiciones.
  Banda $supuestos 'Supuestos' 'Lo que hay que saber para leer bien estas cifras.' 'D'
  $filas = @(
    @('Tasa anual de préstamos', 0.12, 'Supuesto del proyecto: Berka no trae intereses de préstamos. Por eso el margen es estimado.'),
    @('Margen estimado', '', 'Intereses estimados de préstamos + comisiones + sanciones - intereses pagados a clientes.'),
    @('Ratio de mora', '', 'Capital pendiente en mora / capital pendiente total del mes.'),
    @('En mora', '', 'Préstamo con más de una cuota de atraso, contando cuotas pagadas contra esperadas.'),
    @('Mes cerrado', '', 'Mes cuyo último día ya se cargó. El informe no incluye el mes en curso.'),
    @('Últimos 13 meses', '', 'Permiten comparar con el mismo mes del año anterior.'),
    @('Origen', '', 'Vistas de mart en Azure SQL, las mismas que usa Power BI. Datos simulados a partir de Berka.'),
    @('Al abrir el archivo', '', 'Pulsa "Habilitar edición" para que fórmulas y tablas dinámicas se actualicen con los datos del mes.')
  )
  $supuestos.Range('B4').Value2 = 'Concepto'; $supuestos.Range('C4').Value2 = 'Valor'; $supuestos.Range('D4').Value2 = 'Definición'
  $supuestos.Range('B4:D4').Font.Bold = $true
  $supuestos.Range('B4:D4').Interior.Color = (Color 'EEF1F6')
  for ($i = 0; $i -lt $filas.Count; $i++) {
    $f = 5 + $i
    $supuestos.Range("B$f").Value2 = $filas[$i][0]
    if ($filas[$i][1] -ne '') { $supuestos.Range("C$f").Value2 = $filas[$i][1]; $supuestos.Range("C$f").NumberFormat = '0%' }
    $supuestos.Range("D$f").Value2 = $filas[$i][2]
    $supuestos.Range("B${f}:D$f").Borders.Item(9).Color = $borde
  }
  $supuestos.Columns.Item(2).ColumnWidth = 26; $supuestos.Columns.Item(3).ColumnWidth = 9; $supuestos.Columns.Item(4).ColumnWidth = 92
  [void]$libro.Names.Add('TasaSupuesta', '=Supuestos!$C$5')

  # ---- Portada: KPI del mes con fórmulas, formato condicional y navegación.
  Banda $portada 'Banco Analítico: informe mensual' 'Mismas cifras que Power BI. Pulsa "Habilitar edición" para actualizar.' 'H'
  $portada.Range('B4').Value2 = 'Mes de corte'
  $portada.Range('B4').Font.Color = $gris
  $portada.Range('C4').Formula2 = '=INDEX(tKpi[anio_mes],ROWS(tKpi[anio_mes]))'
  $portada.Range('C4').Font.Bold = $true
  $portada.Range('C4').Font.Size = 12
  $portada.Range('B6:E6').Value2 = [object[]]('Indicador', 'Este mes', 'Mes anterior', 'Cambio')
  $portada.Range('B6:E6').Font.Bold = $true
  $portada.Range('B6:E6').Interior.Color = (Color 'EEF1F6')
  $portada.Range('C6:E6').HorizontalAlignment = -4152
  $ultimo = 'ROWS(tKpi[anio_mes])'
  $kpi = @(
    @('Depósitos (CZK)', 'tKpi[depositos]', '#,##0', 1),
    @('Cartera (CZK)', 'tKpi[cartera]', '#,##0', 1),
    @('Margen estimado (CZK)', 'tKpi[margen_estimado]', '#,##0;-#,##0', 1),
    @('Préstamos en mora', 'tKpi[prestamos_en_mora]', '#,##0', -1)
  )
  $f = 7
  foreach ($k in $kpi) {
    $portada.Range("B$f").Value2 = $k[0]
    $portada.Range("C$f").Formula2 = "=INDEX($($k[1]),$ultimo)"
    $portada.Range("D$f").Formula2 = "=INDEX($($k[1]),$ultimo-1)"
    $portada.Range("C${f}:D$f").NumberFormat = $k[2]
    $portada.Range("E$f").Formula2 = "=IFERROR((C$f-D$f)/ABS(D$f),0)"
    $portada.Range("E$f").NumberFormat = '▲ 0.0%;▼ 0.0%;= 0.0%'
    $bien = if ($k[3] -gt 0) { "=E$f>0" } else { "=E$f<0" }
    $mal = if ($k[3] -gt 0) { "=E$f<0" } else { "=E$f>0" }
    ($portada.Range("E$f").FormatConditions.Add(2, 0, $bien)).Font.Color = $verde
    ($portada.Range("E$f").FormatConditions.Add(2, 0, $mal)).Font.Color = $rojo
    $f++
  }
  $portada.Range("B$f").Value2 = 'Ratio de mora'
  $portada.Range("C$f").Formula2 = "=INDEX(tKpi[cartera_en_mora],$ultimo)/INDEX(tKpi[cartera],$ultimo)"
  $portada.Range("D$f").Formula2 = "=INDEX(tKpi[cartera_en_mora],$ultimo-1)/INDEX(tKpi[cartera],$ultimo-1)"
  $portada.Range("C${f}:D$f").NumberFormat = '0.0%'
  $portada.Range("E$f").Formula2 = "=(C$f-D$f)*100"
  $portada.Range("E$f").NumberFormat = '▲ 0.0" pp";▼ 0.0" pp";= 0.0" pp"'
  ($portada.Range("E$f").FormatConditions.Add(2, 0, "=E$f<0")).Font.Color = $verde
  ($portada.Range("E$f").FormatConditions.Add(2, 0, "=E$f>0")).Font.Color = $rojo
  # El margen negativo se ve en rojo aunque mejore.
  ($portada.Range('C9:D9').FormatConditions.Add(1, 6, '=0')).Font.Color = $rojo
  $portada.Range("B7:E$f").Borders.Item(12).Color = $borde
  $portada.Range("B${f}:E$f").Borders.Item(9).Color = $borde
  $portada.Range("E7:E$f").HorizontalAlignment = -4152
  $portada.Range('B14').Value2 = 'Ir a'
  $portada.Range('B14').Font.Bold = $true
  $destinos = @(
    @('Rentabilidad', 'Margen por producto y mes'), @('Cartera', 'Mora por distrito y plazo'),
    @('Morosos', 'Préstamos para gestionar'), @('Supuestos', 'Tasa y definiciones')
  )
  $f = 15
  foreach ($d in $destinos) {
    [void]$portada.Hyperlinks.Add($portada.Range("B$f"), '', "'$($d[0])'!A1", $d[1], $d[0])
    $portada.Range("C$f").Value2 = $d[1]
    $portada.Range("C$f").Font.Color = $gris
    $f++
  }
  $portada.Columns.Item(2).ColumnWidth = 26
  $portada.Columns.Item('C:E').ColumnWidth = 16

  # ---- Cierre: oculta los datos, deja la portada al frente y guarda.
  foreach ($h in 'dKpi', 'dMargen', 'dCartera') { $libro.Worksheets.Item($h).Visible = 0 }
  foreach ($h in $portada, $renta, $cartera, $morosos, $supuestos) {
    $h.Activate()
    [void]$h.Range('A1').Select()
    $h.PageSetup.Orientation = 2
    $h.PageSetup.Zoom = $false
    $h.PageSetup.FitToPagesWide = 1
    $h.PageSetup.FitToPagesTall = 1
  }
  $portada.Activate()
  if (Test-Path $salida) { Remove-Item $salida -Confirm:$false }
  $libro.SaveAs($salida, 51)
  Write-Output "Plantilla escrita en $salida"
}
catch {
  Write-Output "Falló en la línea $($_.InvocationInfo.ScriptLineNumber): $($_.InvocationInfo.Line.Trim())"
  throw
}
finally {
  if ($libro) { $libro.Close($false) }
  $xl.Quit()
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
}
