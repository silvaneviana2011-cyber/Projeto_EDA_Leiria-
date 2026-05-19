# -*- coding: utf-8 -*-
"""
KPIs de temperatura e incendios florestais.

Periodo: maio a outubro de 2025.
Area de estudo: Leiria e municipios adjacentes.

KPIs calculados:
- temperatura media;
- temperatura mais alta;
- area ardida total;
- area ardida no mes critico;
- numero total de incendios.

Tambem cria um dataframe mensal para visualizacao dos resultados.
"""

import struct
import unicodedata

import pandas as pd


# =========================
# 1. CAMINHOS DOS FICHEIROS
# =========================

pasta = r"C:\Users\silva\Desktop\EDA_prof_Albano_projeto"

ficheiro_temperatura = pasta + r"\temp_max_2025-leiria.csv"
ficheiro_area_ardida = pasta + r"\ardida_2025.dbf"


# =========================
# 2. PARAMETROS DA ANALISE
# =========================

ano_analise = 2025
mes_inicio = 5
mes_fim = 10

municipios_analise = [
    "Leiria",
    "Pombal",
    "Marinha Grande",
    "Alcobaca",
    "Nazare",
    "Porto de Mos",
    "Batalha",
    "Ourem",
    "Ansiao"
]

nomes_meses = {
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro"
}


# =========================
# 3. FUNCOES AUXILIARES
# =========================

def ler_dbf(caminho):
    """
    Le um ficheiro DBF e devolve um DataFrame.
    Assim nao e necessario instalar geopandas ou dbfread.
    """
    with open(caminho, "rb") as f:
        cabecalho = f.read(32)
        numero_registos = struct.unpack("<I", cabecalho[4:8])[0]
        tamanho_cabecalho = struct.unpack("<H", cabecalho[8:10])[0]
        tamanho_registo = struct.unpack("<H", cabecalho[10:12])[0]

        campos = []

        while True:
            descritor = f.read(32)

            if descritor[0] == 0x0D:
                break

            nome = descritor[:11].split(b"\x00", 1)[0].decode("latin1")
            tamanho = descritor[16]
            campos.append((nome, tamanho))

        f.seek(tamanho_cabecalho)

        linhas = []

        for _ in range(numero_registos):
            registo = f.read(tamanho_registo)

            if not registo or registo[0:1] == b"*":
                continue

            posicao = 1
            linha = {}

            for nome, tamanho in campos:
                valor = registo[posicao:posicao + tamanho]
                posicao += tamanho
                valor = valor.decode("latin1", errors="ignore").strip()
                linha[nome] = valor

            linhas.append(linha)

    return pd.DataFrame(linhas)


def normalizar_texto(valor):
    """
    Remove acentos para comparar corretamente nomes de municipios.
    """
    if pd.isna(valor):
        return ""

    texto = str(valor).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


# =========================
# 4. TEMPERATURA
# =========================

temperatura = pd.read_csv(ficheiro_temperatura)

temperatura["date"] = pd.to_datetime(
    temperatura["date"],
    errors="coerce"
)

temperatura["mean"] = pd.to_numeric(
    temperatura["mean"],
    errors="coerce"
)

temperatura["maximum"] = pd.to_numeric(
    temperatura["maximum"],
    errors="coerce"
)

temperatura = temperatura[
    (temperatura["date"].dt.year == ano_analise) &
    (temperatura["date"].dt.month >= mes_inicio) &
    (temperatura["date"].dt.month <= mes_fim)
].copy()

temperatura["mes"] = temperatura["date"].dt.month

temperatura_mensal = (
    temperatura
    .groupby("mes", as_index=False)
    .agg(
        temperatura_media=("mean", "mean"),
        temperatura_mais_alta=("maximum", "max")
    )
)


# =========================
# 5. AREA ARDIDA E INCENDIOS
# =========================

area_ardida = ler_dbf(ficheiro_area_ardida)

area_ardida["DH_Inicio"] = pd.to_datetime(
    area_ardida["DH_Inicio"],
    format="%Y%m%d",
    errors="coerce"
)

area_ardida["AreaHaSIG"] = pd.to_numeric(
    area_ardida["AreaHaSIG"],
    errors="coerce"
)

area_ardida["municipio_norm"] = area_ardida["PI_Conc"].apply(normalizar_texto)
area_ardida["ano"] = area_ardida["DH_Inicio"].dt.year
area_ardida["mes"] = area_ardida["DH_Inicio"].dt.month

municipios_norm = [normalizar_texto(municipio) for municipio in municipios_analise]

area_ardida_filtrada = area_ardida[
    (area_ardida["ano"] == ano_analise) &
    (area_ardida["mes"] >= mes_inicio) &
    (area_ardida["mes"] <= mes_fim) &
    (area_ardida["municipio_norm"].isin(municipios_norm))
].copy()

area_incendios_mensal = (
    area_ardida_filtrada
    .groupby("mes", as_index=False)
    .agg(
        area_ardida_mensal=("AreaHaSIG", "sum"),
        numero_incendios_mensal=("Cod_SGIF", "count")
    )
)


# =========================
# 6. DATAFRAME MENSAL
# =========================

df_resultados = pd.DataFrame({
    "mes": list(range(mes_inicio, mes_fim + 1))
})

df_resultados = df_resultados.merge(
    temperatura_mensal,
    on="mes",
    how="left"
)

df_resultados = df_resultados.merge(
    area_incendios_mensal,
    on="mes",
    how="left"
)

df_resultados["nome_mes"] = df_resultados["mes"].map(nomes_meses)

# Se nao houve incendio num mes, a area e o numero de incendios ficam a zero.
df_resultados["area_ardida_mensal"] = (
    df_resultados["area_ardida_mensal"]
    .fillna(0)
)

df_resultados["numero_incendios_mensal"] = (
    df_resultados["numero_incendios_mensal"]
    .fillna(0)
    .astype(int)
)

# Se nao existir temperatura em algum mes, fica como 0 para evitar erros na visualizacao.
df_resultados["temperatura_media"] = (
    df_resultados["temperatura_media"]
    .fillna(0)
)

df_resultados["temperatura_mais_alta"] = (
    df_resultados["temperatura_mais_alta"]
    .fillna(0)
)

df_resultados = df_resultados[
    [
        "mes",
        "nome_mes",
        "temperatura_media",
        "temperatura_mais_alta",
        "area_ardida_mensal",
        "numero_incendios_mensal"
    ]
]


# =========================
# 7. KPIS GERAIS
# =========================

temperatura_media_periodo = df_resultados.loc[
    df_resultados["temperatura_media"] > 0,
    "temperatura_media"
].mean()

temperatura_mais_alta_periodo = df_resultados["temperatura_mais_alta"].max()

area_ardida_total = df_resultados["area_ardida_mensal"].sum()

numero_total_incendios = df_resultados["numero_incendios_mensal"].sum()

linha_mes_critico = df_resultados.loc[
    df_resultados["area_ardida_mensal"].idxmax()
]

mes_critico = linha_mes_critico["nome_mes"]
area_ardida_mes_critico = linha_mes_critico["area_ardida_mensal"]


df_kpis = pd.DataFrame({
    "kpi": [
        "Temperatura media",
        "Temperatura mais alta",
        "Area ardida total",
        "Area ardida no mes critico",
        "Numero total de incendios",
        "Mes critico"
    ],
    "valor": [
        round(temperatura_media_periodo, 2),
        round(temperatura_mais_alta_periodo, 2),
        round(area_ardida_total, 2),
        round(area_ardida_mes_critico, 2),
        int(numero_total_incendios),
        mes_critico
    ],
    "unidade": [
        "C",
        "C",
        "ha",
        "ha",
        "incendios",
        ""
    ]
})


# =========================
# 8. RESULTADOS
# =========================

print("===== KPIs - Maio a Outubro de 2025 =====")
print(df_kpis)

print("\n===== DataFrame mensal para visualizacao =====")
print(df_resultados) 
