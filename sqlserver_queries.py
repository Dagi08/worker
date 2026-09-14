"""Queries parametrizadas contra SQL Server (equivalentes a usp_ObtenerDatosVehiculoSolicitud
y a las queries adicionales de ingresos/deuda financiera). Todas usan `?` como placeholder
posicional para pyodbc; ver sqlserver_client.obtener_datos_vehiculo para el orden de llamada."""

SQL_NUMERO_DOCUMENTO = """
    SELECT MAX(CASE WHEN WFAttSId = 'CLNRODOC' THEN TRIM(WFAttSVal) END) AS NumeroDocumento
    FROM WFAttSValues
    WHERE WFInsPrcId = ?
"""
SQL_VEHICULO = """
    WITH DatosVehiculo AS (
        SELECT
            WFInsPrcId,
            CAST(MAX(CASE WHEN WFAttSId = 'VEHMONTO' THEN TRIM(WFAttSVal) END) AS DECIMAL(18,2)) AS [Monto en soles],
            MAX(CASE WHEN WFAttSId = 'CLTIPDOC' THEN TRIM(WFAttSVal) END) AS CodTipoDoc,
            MAX(CASE WHEN WFAttSId = 'CLNRODOC' THEN TRIM(WFAttSVal) END) AS [Numero de Documento]
        FROM WFAttSValues
        --WHERE WFInsPrcId = ?
        GROUP BY WFInsPrcId
    )
    SELECT
        WI.WFInsPrcId AS INSTANCIA,
        CAST(DV.[Monto en soles] / NULLIF(FA2.JMFAA2TCS, 0) AS DECIMAL(18,2)) AS [Monto en dólares],
        DV.[Monto en soles],
        FA1.JMFAA1SEX AS Score,
        FA2.JMFAA2CCU AS Cuotas,
        T.Tdnom AS [Tipo Documento],
        DV.[Numero de Documento]
    FROM (
        SELECT d.WFInsPrcId
        FROM WFWrkItems d
        INNER JOIN WFInstPrc c ON c.WFInsPrcId = d.WFInsPrcId AND c.WFInsPrcOSta = 1
        --WHERE d.WFInsPrcId = ?
          AND NOT EXISTS (
              SELECT 1 FROM WFWrkItems d2
              WHERE d2.WFInsPrcId = d.WFInsPrcId AND d2.WFItemId > d.WFItemId
          )
    ) WI
    INNER JOIN WFInstPrc IP ON IP.WFInsPrcId = WI.WFInsPrcId
    LEFT JOIN DatosVehiculo DV ON DV.WFInsPrcId = WI.WFInsPrcId
    LEFT JOIN JMFAA1 FA1 ON FA1.JMFAA1INS = WI.WFInsPrcId
    LEFT JOIN JMFAA2 FA2 ON FA2.JMFAA2INS = WI.WFInsPrcId
    LEFT JOIN Fst014 T ON T.Tdocum = DV.CodTipoDoc
    WHERE IP.WFInsPrcOSta = 1
      AND WI.WFInsPrcId = ?
    ORDER BY WI.WFInsPrcId DESC
"""
SQL_PERSONA = """
    SELECT
        WI.WFInsPrcId AS INSTANCIA,
        ISNULL(CLI.SNGC60Ocup, '') AS [Tipo de ocupación],
        ISNULL(CAT.sngc07dsc, 'No Especificado') AS [Nombre de ocupación],
        TRIM(CLI.SNGC60Rute) AS [RUC Empleador],
        CASE WHEN CLI.SNGC60Ocup = 1 THEN CAST(ING.JMFN02TEM AS INT) ELSE 0 END AS [Cod. Tipo de empresa],
        CASE
            WHEN CLI.SNGC60Ocup = 1 THEN
                CASE CAST(ING.JMFN02TEM AS INT)
                    WHEN 1 THEN 'Publica'
                    WHEN 2 THEN 'Privada'
                    WHEN 3 THEN 'Remype'
                    ELSE '-'
                END
            ELSE '-'
        END AS [Tipo de empresa],
        CASE WHEN CLI.SNGC60Ocup = 1 THEN CAST(ING.JMFN02TIN AS INT) ELSE 0 END AS [Cod. Tipo de ingreso],
        CASE
            WHEN CLI.SNGC60Ocup = 1 THEN
                CASE CAST(ING.JMFN02TIN AS INT)
                    WHEN 1 THEN 'Fijos'
                    WHEN 2 THEN 'Variables'
                    ELSE '-'
                END
            ELSE '-'
        END AS [Tipo de ingreso],
        CLI.SNGC60Fine AS [Fecha Ingreso Empresa],
        TRIM(CONCAT(TRIM(CLI2.Pfnom1), ' ', TRIM(CLI2.Pfnom2))) AS [Nombre],
        TRIM(CLI2.Pfape1) AS [Apellido Paterno],
        TRIM(CLI2.Pfape2) AS [Apellido Materno],
        CAST(CLI2.Pffnac AS DATE) AS [Fecha de Nacimiento]
    FROM (
        SELECT d.WFInsPrcId
        FROM WFWrkItems d
        INNER JOIN WFInstPrc c ON c.WFInsPrcId = d.WFInsPrcId AND c.WFInsPrcOSta = 1
        --WHERE d.WFInsPrcId = ? AND
        WHERE  NOT EXISTS (
              SELECT 1 FROM WFWrkItems d2
              WHERE d2.WFInsPrcId = d.WFInsPrcId AND d2.WFItemId > d.WFItemId
          )
    ) WI
    INNER JOIN WFInstPrc IP ON IP.WFInsPrcId = WI.WFInsPrcId
    LEFT JOIN JMFAA1 FA1 ON FA1.JMFAA1INS = WI.WFInsPrcId
    LEFT JOIN SNGC60 CLI ON CLI.SNGC60Pais = FA1.JMFAA1PAI
                        AND CLI.SNGC60Tdoc = FA1.JMFAA1TDO
                        AND CLI.SNGC60Ndoc = FA1.JMFAA1NDO
                        AND CLI.SNGC60Corr = 0
    LEFT JOIN JMFN02 ING ON ING.JMFN02PAI = CLI.SNGC60Pais
                        AND ING.JMFN02TDO = CLI.SNGC60Tdoc
                        AND ING.JMFN02NDO = CLI.SNGC60Ndoc
                        AND ING.JMFN02COR = CLI.SNGC60Corr
    LEFT JOIN FSD002 CLI2 ON CLI2.Pfpais = FA1.JMFAA1PAI
                         AND CLI2.Pftdoc = FA1.JMFAA1TDO
                         AND TRIM(CLI2.Pfndoc) = TRIM(FA1.JMFAA1NDO)
    LEFT JOIN SNGC07 CAT ON CLI.SNGC60Ocup = CAT.SNGC07Cod
    WHERE IP.WFInsPrcOSta = 1
      AND WI.WFInsPrcId = ?
    ORDER BY WI.WFInsPrcId DESC
"""
SQL_DOMICILIOS = """
    SELECT
        a.Docod AS [Código],
        ISNULL(RTRIM(LTRIM(b.Donom)), 'Otro') AS [Tipo Dom.],
        ISNULL(NULLIF(RTRIM(LTRIM(a.sngc13Dir)), ''), ISNULL(NULLIF(RTRIM(LTRIM(a.sngc13Ref1)), ''), 'Sin Dirección Registrada')) AS [Dirección],
        a.sngc13Est AS [Cod. Habilitado],
        CASE a.sngc13Est
            WHEN 'H' THEN 'SI'
            ELSE 'NO'
        END AS [Habilitado]
    FROM sngc13 a
    LEFT JOIN FST015 b ON a.Docod = b.Docod
    WHERE a.sngc13Pais = 604
      AND a.sngc13Tdoc = 1
      AND TRIM(a.sngc13Ndoc) = ?
      AND a.sngc13Est = 'H'
"""
SQL_CANTIDAD_SOLICITUDES = """
    SELECT
        TRIM(JMFAA1NDO) AS [DNI],
        COUNT(*) AS [Cantidad de Solicitudes]
    FROM JMFAA1
    WHERE TRIM(JMFAA1NDO) = ?
      AND JMFAA1TDO = 1
    GROUP BY JMFAA1NDO
"""
SQL_MOROSIDAD_DNI = """
    SELECT DISTINCT
        f.Aooper AS Operacion,
        p.Pendoc AS DNI,
        f.Aocta AS Cuenta,
        ISNULL(m.Mosign, 'S/. ') AS Moneda,
        f.Aoimp AS [Monto de capital],
        ISNULL(e.Cenom, 'Normal') AS Estado
    FROM Fsd010 f
    INNER JOIN Fsd008 c ON f.Pgcod = c.Pgcod AND f.Aocta = c.CTNRO
    INNER JOIN Fsd005 p ON c.Ctnroi = p.Doccorp
    INNER JOIN Fst111 d ON f.Aomod = d.Modulo
    LEFT JOIN  Fst005 m ON f.Aomda = m.Moneda
    LEFT JOIN  Fst026 e ON f.Aostat = e.Cecod
    WHERE f.Pgcod = 1
      AND TRIM(p.Pendoc) = ?
      AND d.Dscod = 50
      AND f.Aostat <> 99
    ORDER BY f.Aooper ASC
"""
SQL_MOROSIDAD_CUENTA = """
    SELECT DISTINCT
        f.Aooper AS Operacion,
        f.Aocta AS Cuenta,
        ISNULL(m.Mosign, 'S/. ') AS Moneda,
        f.Aoimp AS [Monto de capital],
        ISNULL(e.Cenom, 'Normal') AS Estado
    FROM Fsd010 f
    INNER JOIN Fst111 d ON f.Aomod = d.Modulo
    LEFT JOIN  Fst005 m ON f.Aomda = m.Moneda
    LEFT JOIN  Fst026 e ON f.Aostat = e.Cecod
    WHERE f.Pgcod = 1
      AND f.Aocta IN (
          SELECT DISTINCT f2.Aocta
          FROM Fsd010 f2
          INNER JOIN Fsd008 c2 ON f2.Pgcod = c2.Pgcod AND f2.Aocta = c2.CTNRO
          INNER JOIN Fsd005 p2 ON c2.Ctnroi = p2.Doccorp
          INNER JOIN Fst111 d2 ON f2.Aomod = d2.Modulo
          WHERE f2.Pgcod = 1
            AND TRIM(p2.Pendoc) = ?
            AND d2.Dscod = 50
            AND f2.Aostat <> 99
      )
      AND d.Dscod = 50
      AND f.Aostat <> 99
    ORDER BY f.Aooper ASC
"""
SQL_NUMERO_INGRESO = """
SELECT
    JMFW50INS AS [Instancia / Crédito],
    JMFW50NDO AS [DNI],
    JMFW50NSA AS [Valor BD],
    CASE JMFW50TEM
        WHEN 2 THEN 14
        ELSE 12
    END AS [Nro. Ingresos Mensuales]
FROM JMFW50
WHERE JMFW50INS = ?
  AND JMFW50COR = 0;
"""
SQL_REGIMEN_SUNAT = """
SELECT
    w50.JMFW50INS AS Instancia,
    w50.JMFW50NDO AS Documento_Identidad,
    w50.JMFW50RSU AS Codigo_Regimen,
    ISNULL(f98.Tpdesc, 'No configurado') AS Regimen_Sunat
FROM JMFW50 w50
LEFT JOIN FST098 f98 ON f98.Tpcorr = w50.JMFW50RSU AND f98.Tpcod = 3928
WHERE w50.JMFW50INS = ? --IN (913599, 918942) -- Instancia
  AND w50.JMFW50COR = 0;
"""
SQL_PERIODOS_INGRESO = """
SELECT
    w50.JMFW50INS AS [Instancia],
    sol.JMFAA1FSO AS [Fecha Solicitud],
    CONVERT(VARCHAR(6), DATEADD(MONTH, -3, sol.JMFAA1FSO), 112) AS [Periodo 3],
    CONVERT(VARCHAR(6), DATEADD(MONTH, -2, sol.JMFAA1FSO), 112) AS [Periodo 2],
    CONVERT(VARCHAR(6), DATEADD(MONTH, -1, sol.JMFAA1FSO), 112) AS [Periodo 1]
FROM JMFW50 w50
LEFT JOIN JMFAA1 sol ON sol.JMFAA1INS = w50.JMFW50INS
WHERE w50.JMFW50INS = ? --IN (918942, 913599, 795215, 769025)
  AND w50.JMFW50COR = 0;
"""
SQL_INGRESOS = """
WITH DatosBase AS (
    SELECT DISTINCT
        w50.JMFW50INS AS Instancia,
        sol.JMFAA1FSO AS FechaBaseSolicitud,
        -- Mapeo de la Categoría Laboral
        ISNULL(
            (SELECT MAX(c60.SNGC60Ocup)
             FROM SNGC60 c60
             WHERE c60.SNGC60Tdoc = w50.JMFW50TDO
               AND c60.SNGC60Ndoc = w50.JMFW50NDO
               AND c60.SNGC60Pais IN (w50.JMFW50PAI, 999)),
            w50.JMFW50PCL
        ) AS CodCat,
        -- Montos de ingresos
        ISNULL(w50.JMFW50PRO, 0)  AS ImpIngFijo,
        ISNULL(w50.JMFW50ING1, 0) AS ImpIngVar1,
        ISNULL(w50.JMFW50ING2, 0) AS ImpIngVar2,
        ISNULL(w50.JMFW50ING3, 0) AS ImpIngVar3,
        CONVERT(VARCHAR(6), DATEADD(MONTH, -3, sol.JMFAA1FSO), 112) AS Periodo1,
        CONVERT(VARCHAR(6), DATEADD(MONTH, -2, sol.JMFAA1FSO), 112) AS Periodo2,
        CONVERT(VARCHAR(6), DATEADD(MONTH, -1, sol.JMFAA1FSO), 112) AS Periodo3
    FROM JMFW50 w50
    LEFT JOIN JMFAA1 sol ON sol.JMFAA1INS = w50.JMFW50INS
    WHERE w50.JMFW50COR = 0
),
ReporteAgrupado AS (
    -- INGRESO FIJO
    SELECT
        Instancia, 'Fijo Titular' AS [Variable Periodo], 0 AS Orden,
        CASE WHEN CodCat IN (4, 5, 6) THEN ImpIngFijo ELSE 0 END AS [3° Cat],
        CASE WHEN CodCat = 9 THEN ImpIngFijo ELSE 0 END AS [1° Cat],
        CASE WHEN CodCat = 1 THEN ImpIngFijo ELSE 0 END AS [5° Cat],
        CASE WHEN CodCat = 3 THEN ImpIngFijo ELSE 0 END AS [4° Cat]
    FROM DatosBase
    UNION ALL
    -- INGRESO VARIABLE 1
    SELECT
        Instancia, 'periodo ' + Periodo1 AS [Variable Periodo], 1 AS Orden,
        CASE WHEN CodCat IN (4, 5, 6) THEN ImpIngVar1 ELSE 0 END AS [3° Cat],
        CASE WHEN CodCat = 9 THEN ImpIngVar1 ELSE 0 END AS [1° Cat],
        CASE WHEN CodCat = 1 THEN ImpIngVar1 ELSE 0 END AS [5° Cat],
        CASE WHEN CodCat = 3 THEN ImpIngVar1 ELSE 0 END AS [4° Cat]
    FROM DatosBase
    UNION ALL
    -- INGRESO VARIABLE 2
    SELECT
        Instancia, 'periodo ' + Periodo2 AS [Variable Periodo], 2 AS Orden,
        CASE WHEN CodCat IN (4, 5, 6) THEN ImpIngVar2 ELSE 0 END AS [3° Cat],
        CASE WHEN CodCat = 9 THEN ImpIngVar2 ELSE 0 END AS [1° Cat],
        CASE WHEN CodCat = 1 THEN ImpIngVar2 ELSE 0 END AS [5° Cat],
        CASE WHEN CodCat = 3 THEN ImpIngVar2 ELSE 0 END AS [4° Cat]
    FROM DatosBase
    UNION ALL
    -- INGRESO VARIABLE 3
    SELECT
        Instancia, 'periodo ' + Periodo3 AS [Variable Periodo], 3 AS Orden,
        CASE WHEN CodCat IN (4, 5, 6) THEN ImpIngVar3 ELSE 0 END AS [3° Cat],
        CASE WHEN CodCat = 9 THEN ImpIngVar3 ELSE 0 END AS [1° Cat],
        CASE WHEN CodCat = 1 THEN ImpIngVar3 ELSE 0 END AS [5° Cat],
        CASE WHEN CodCat = 3 THEN ImpIngVar3 ELSE 0 END AS [4° Cat]
    FROM DatosBase
)
SELECT
    Instancia,
    [Variable Periodo],
    'S/. ' + ISNULL(CONVERT(VARCHAR, CAST([5° Cat] AS MONEY), 1), '0.00') AS [5° Categoría],
    'S/. ' + ISNULL(CONVERT(VARCHAR, CAST([4° Cat] AS MONEY), 1), '0.00') AS [4° Categoría],
    'S/. ' + ISNULL(CONVERT(VARCHAR, CAST([3° Cat] AS MONEY), 1), '0.00') AS [3° Categoría],
    'S/. ' + ISNULL(CONVERT(VARCHAR, CAST([1° Cat] AS MONEY), 1), '0.00') AS [1° Categoría]
FROM ReporteAgrupado
WHERE Instancia = ? --IN (913599, 918942, 795215, 769025) -- Instancia
  AND NOT ([5° Cat] = 0 AND [4° Cat] = 0 AND [3° Cat] = 0 AND [1° Cat] = 0 AND [Variable Periodo] LIKE 'periodo%')
ORDER BY Instancia DESC, Orden ASC;
"""
SQL_DEUDA_FIANCIERA = """
SELECT
    b.MAFA16INST AS [Instancia / Crédito],
    b.MAFA16FILA AS [Nro. Registro],

    -- Información Principal de la Entidad
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'DscEnt'   THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [Entidad],
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'TipoCred' THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [Tipo de Crédito],
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'Tipmoda'  THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [Modalidad],
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'DscMda'   THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [Moneda],

    -- Fechas de Auditoría de la Deuda
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'FecDeu'   THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [F. Creación],
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'FecMod'   THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [F. Modif],

    -- Cuotas del Crédito (Titular y Cónyuge)
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'CCuotaTi' THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [Cuota Titular],
    ISNULL(MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'CCuotaCo' THEN RTRIM(LTRIM(b.MAFA16VALR)) END), '-') AS [Cuota Cónyuge]

FROM MAFA16 b
WHERE b.MAFA16INST = ?  -- Instancia
  AND b.MAFA16SECU = 12 -- Grilla de Deudas Financieras
GROUP BY b.MAFA16INST, b.MAFA16FILA
ORDER BY b.MAFA16FILA;
"""
SQL_INGRESO_USD = """
SELECT
    MAFA16INST AS [Instancia],
    'Ingresos' AS [Concepto],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'IngresDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Valor Mensual],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'TotIngresDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Total Acumulado]
FROM MAFA16
WHERE MAFA16INST = ?  -- Instancia
  AND MAFA16SECU = 17
  AND MAFA16FILA = 1
GROUP BY MAFA16INST;
"""
SQL_GASTO_OPERATIVO_USD = """
SELECT
    MAFA16INST AS [Instancia],
    'Gastos Operativos' AS [Concepto],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'CosOpeDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Valor Mensual],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'TotCosOpeDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Total Acumulado]
FROM MAFA16
WHERE MAFA16INST = ?  -- Instancia
  AND MAFA16SECU = 17
  AND MAFA16FILA = 2
GROUP BY MAFA16INST;
"""
SQL_UTILIDAD_OPERATIVA_USD = """
SELECT
    MAFA16INST AS [Instancia],
    'Utilidad Operativa' AS [Concepto],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'MarOpeDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Valor Mensual],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'TotMarOpeDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Total Acumulado]
FROM MAFA16
WHERE MAFA16INST = ?  -- Instancia
  AND MAFA16SECU = 17
  AND MAFA16FILA = 3
GROUP BY MAFA16INST;
"""
SQL_NET_USD = """
SELECT
    MAFA16INST AS [Instancia],
    'NET' AS [Concepto],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'CuoNETDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Valor Mensual],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'TotCuoNETDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Total Acumulado]
FROM MAFA16
WHERE MAFA16INST = ?  -- Instancia
  AND MAFA16SECU = 17
  AND MAFA16FILA = 4
GROUP BY MAFA16INST
"""
SQL_CUOTA_MAF_USD = """
SELECT
    MAFA16INST AS [Instancia],
    'Cuota MAF' AS [Concepto],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'CuoMAFDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Valor Mensual],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'TotCuoMAFDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Total Acumulado]
FROM MAFA16
WHERE MAFA16INST = ?  -- Instancia
  AND MAFA16SECU = 17
  AND MAFA16FILA = 5
GROUP BY MAFA16INST;
"""
SQL_SALDO_USD = """
SELECT
    MAFA16INST AS [Instancia],
    'Saldo' AS [Concepto],
    MAX(CASE WHEN TRIM(MAFA16ATRB) = 'SaldoDol' THEN RTRIM(LTRIM(MAFA16VALR)) END) AS [Valor Mensual]
FROM MAFA16
WHERE MAFA16INST = ?  -- Instancia
  AND MAFA16SECU = 17
  AND MAFA16FILA = 6
GROUP BY MAFA16INST;
"""
SQL_RCI_USD = """
SELECT
    b.MAFA16INST AS [Instancia / Crédito],
    'RCI' AS [Parámetro],
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'CRCI'     THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [Valor Obtenido],
    MAX(CASE WHEN TRIM(b.MAFA16ATRB) = 'ResulRCI' THEN RTRIM(LTRIM(b.MAFA16VALR)) END) AS [Resultados]
FROM MAFA16 b
WHERE b.MAFA16INST = ? -- Instancia
  AND b.MAFA16SECU = 19 -- Grilla de Resultados de Políticas
  AND b.MAFA16FILA = 2  -- Fila exclusiva del RCI
GROUP BY b.MAFA16INST;
"""
