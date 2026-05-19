# -*- coding: utf-8 -*-
"""
PlotBarh do DataFrame consolidado de incendios florestais.

Periodo: maio a outubro de 2025.
Municipios: Leiria, Pombal, Marinha Grande, Alcobaca, Nazare,
Porto de Mos, Batalha, Ourem e Ansiao.
"""

import struct
import unicodedata

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


# =========================
# 1. CAMINHOS DOS FICHEIROS
# =========================

pasta = r"C:\Users\silva\Desktop\EDA_prof_Albano_projeto"

ficheiro_temperatura = pasta + r"\temp_max_2025-leiria.csv"
ficheiro_pdsi = pasta + r"\mpdsi-per_seca1009-leiria.csv"
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
    """Le ficheiros DBF sem depender de geopandas."""
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
    """Remove acentos e espacos extra para comparar municipios."""
    if pd.isna(valor):
        return ""

    texto = str(valor).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def criar_dataframe_consolidado():
    """Cria o dataframe mensal consolidado usado nos graficos."""
    temperatura = pd.read_csv(ficheiro_temperatura)
    temperatura["date"] = pd.to_datetime(temperatura["date"], errors="coerce")
    temperatura["mean"] = pd.to_numeric(temperatura["mean"], errors="coerce")

    temperatura = temperatura[
        (temperatura["date"].dt.year == ano_analise) &
        (temperatura["date"].dt.month >= mes_inicio) &
        (temperatura["date"].dt.month <= mes_fim)
    ].copy()

    temperatura["mes"] = temperatura["date"].dt.month

    temperatura_mensal = (
        temperatura
        .groupby("mes", as_index=False)
        .agg(temperatura_media=("mean", "mean"))
    )

    pdsi = pd.read_csv(ficheiro_pdsi)
    pdsi["date"] = pd.to_datetime(pdsi["date"], errors="coerce")
    pdsi["mean"] = pd.to_numeric(pdsi["mean"], errors="coerce")

    pdsi = pdsi[
        (pdsi["date"].dt.year == ano_analise) &
        (pdsi["date"].dt.month >= mes_inicio) &
        (pdsi["date"].dt.month <= mes_fim)
    ].copy()

    pdsi["mes"] = pdsi["date"].dt.month

    pdsi_mensal = (
        pdsi
        .groupby("mes", as_index=False)
        .agg(pdsi=("mean", "mean"))
    )

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

    dataframe_consolidado = pd.DataFrame({
        "mes": list(range(mes_inicio, mes_fim + 1))
    })

    dataframe_consolidado = dataframe_consolidado.merge(
        temperatura_mensal,
        on="mes",
        how="left"
    )

    dataframe_consolidado = dataframe_consolidado.merge(
        pdsi_mensal,
        on="mes",
        how="left"
    )

    dataframe_consolidado = dataframe_consolidado.merge(
        area_incendios_mensal,
        on="mes",
        how="left"
    )

    dataframe_consolidado["area_ardida_mensal"] = (
        dataframe_consolidado["area_ardida_mensal"].fillna(0)
    )

    dataframe_consolidado["numero_incendios_mensal"] = (
        dataframe_consolidado["numero_incendios_mensal"]
        .fillna(0)
        .astype(int)
    )

    dataframe_consolidado["temperatura_media"] = (
        dataframe_consolidado["temperatura_media"]
        .fillna(dataframe_consolidado["temperatura_media"].mean())
    )

    dataframe_consolidado["pdsi"] = (
        dataframe_consolidado["pdsi"]
        .fillna(dataframe_consolidado["pdsi"].mean())
    )

    dataframe_consolidado = dataframe_consolidado.fillna(0)
    dataframe_consolidado["nome_mes"] = dataframe_consolidado["mes"].map(nomes_meses)

    return dataframe_consolidado


# =========================
# 4. CRIAR DATAFRAME
# =========================

df = criar_dataframe_consolidado()

print("===== DataFrame usado no PlotBarh =====")
print(df)


# =========================
# 5. PLOTBARH - AREA ARDIDA
# =========================

sns.set_theme(style="whitegrid")

df_area = df.sort_values("area_ardida_mensal", ascending=True)

plt.figure(figsize=(10, 6))

grafico = sns.barplot(
    data=df_area,
    y="nome_mes",
    x="area_ardida_mensal",
    color="#C94C4C"
)

plt.title(
    "Area ardida mensal - Maio a Outubro de 2025",
    fontsize=14,
    fontweight="bold"
)
plt.xlabel("Area ardida mensal (ha)")
plt.ylabel("Mes")
plt.grid(axis="x", alpha=0.3)

for barra in grafico.patches:
    largura = barra.get_width()
    grafico.text(
        largura,
        barra.get_y() + barra.get_height() / 2,
        f" {largura:.1f}",
        va="center",
        fontsize=10
    )

plt.tight_layout()
plt.show()


# =========================
# 6. PLOTBARH - NUMERO DE INCENDIOS
# =========================

df_incendios = df.sort_values("numero_incendios_mensal", ascending=True)

plt.figure(figsize=(10, 6))

grafico = sns.barplot(
    data=df_incendios,
    y="nome_mes",
    x="numero_incendios_mensal",
    color="#4C78A8"
)

plt.title(
    "Numero de incendios mensal - Maio a Outubro de 2025",
    fontsize=14,
    fontweight="bold"
)
plt.xlabel("Numero de incendios")
plt.ylabel("Mes")
plt.grid(axis="x", alpha=0.3)

for barra in grafico.patches:
    largura = barra.get_width()
    grafico.text(
        largura,
        barra.get_y() + barra.get_height() / 2,
        f" {int(largura)}",
        va="center",
        fontsize=10
    )

plt.tight_layout()
plt.show()
